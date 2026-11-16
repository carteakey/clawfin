"""
Transfer pair detector — runs post-dedup, pre-insert (import pipeline)
and on-demand over committed DB rows (retrigger endpoint).

Internal transfer definition: money moves between your own accounts
(net worth unchanged). This explicitly covers:
  - Chequing → Savings
  - Chequing → TFSA / RRSP / FHSA (on-budget to off/investment)
  - Credit card payment (chequing debit + credit card credit)

NOT a transfer: sending money to another person (e-transfer to someone
else typically has no matching counterpart in your own accounts).

Pairing criteria (conservative):
  - Matching absolute amounts (within 1 cent tolerance for FX rounding)
  - Opposite signs
  - Date delta ≤ 2 days (SimpleFIN posting lag between accounts)
  - Different account_ids — same-account debit+credit is a correction, not a transfer
    NOTE: if both transactions have account_id=None (CSV without account),
    we still pair them since we can't tell they're the same account.
"""
from datetime import date as date_type, timedelta


# ─── Shared pairing primitives ────────────────────────────────────────────

AMT_TOL = 0.01  # 1-cent tolerance


def _as_date(d) -> date_type:
    if isinstance(d, date_type):
        return d
    if isinstance(d, str):
        return date_type.fromisoformat(d)
    return d


def _is_pair(amt_a, date_a, acct_a, amt_b, date_b, acct_b) -> bool:
    """Return True if two transactions look like an internal transfer pair."""
    # Must be opposite signs
    if amt_a * amt_b >= 0:
        return False
    # Matching absolute amounts (within tolerance)
    if abs(abs(amt_a) - abs(amt_b)) > AMT_TOL:
        return False
    # Within 2 days
    if abs((_as_date(date_b) - _as_date(date_a)).days) > 2:
        return False
    # Different accounts (if both known)
    if acct_a and acct_b and acct_a == acct_b:
        return False
    return True


# ─── Import-time detector (operates on dicts, pre-insert) ─────────────────

def detect_internal_transfers(
    new_txs: list[dict],
    existing_txs: list[dict] | None = None,
) -> int:
    """
    Mark transfer pairs within new_txs (and optionally against existing_txs)
    as category="Transfer".

    new_txs: list of transaction dicts (mutable, category set in place).
    existing_txs: already-committed transactions to match against (read-only).
                  Pass the last 5 days of committed txns for SimpleFIN syncs.

    Returns the number of newly marked transfers.
    """
    marked = 0

    # Index existing transactions by rounded absolute amount for fast lookup
    existing_by_amt: dict[float, list[dict]] = {}
    for tx in (existing_txs or []):
        if tx.get("category") == "Transfer":
            continue
        key = round(abs(tx["amount"]), 2)
        existing_by_amt.setdefault(key, []).append(tx)

    paired: set[int] = set()

    # First pass: pair within new_txs
    for i, tx_a in enumerate(new_txs):
        if i in paired or tx_a.get("category") == "Transfer":
            continue
        for j, tx_b in enumerate(new_txs):
            if j <= i or j in paired or tx_b.get("category") == "Transfer":
                continue
            if _is_pair(
                tx_a["amount"], tx_a["date"], tx_a.get("account_id"),
                tx_b["amount"], tx_b["date"], tx_b.get("account_id"),
            ):
                new_txs[i]["category"] = "Transfer"
                new_txs[j]["category"] = "Transfer"
                paired.update({i, j})
                marked += 2
                break

    # Second pass: match unpaired new_txs against committed existing txns
    for i, tx_a in enumerate(new_txs):
        if i in paired or tx_a.get("category") == "Transfer":
            continue
        key = round(abs(tx_a["amount"]), 2)
        for tx_b in existing_by_amt.get(key, []):
            if _is_pair(
                tx_a["amount"], tx_a["date"], tx_a.get("account_id"),
                tx_b["amount"], tx_b["date"], tx_b.get("account_id"),
            ):
                new_txs[i]["category"] = "Transfer"
                marked += 1
                break

    return marked


# ─── DB re-trigger (operates on committed Transaction ORM rows) ────────────

def redetect_transfers_in_db(db, days: int | None = None) -> dict:
    """
    Scan committed transactions in the DB, pair them, and update
    category="Transfer" for matched pairs.

    Runs over ALL transactions by default (days=None), or the last N days.
    Already-Transfer rows are re-evaluated: if a row was previously marked
    Transfer but no longer has a counterpart, it is left as-is (conservative —
    don't un-mark; the user may have set it intentionally).

    Returns {"scanned": int, "newly_marked": int, "already_marked": int}
    """
    from backend.db.models import Transaction
    from datetime import date as dt_date
    import datetime

    q = db.query(Transaction)
    if days is not None:
        cutoff = dt_date.today() - timedelta(days=days)
        q = q.filter(Transaction.date >= cutoff)

    txs = q.order_by(Transaction.date.asc(), Transaction.id.asc()).all()

    # Convert ORM rows to lightweight dicts, keep id for update mapping
    rows = [
        {
            "id": t.id,
            "amount": t.amount,
            "date": t.date,
            "account_id": t.account_id,
            "category": t.category,
            "_orig_category": t.category,
        }
        for t in txs
    ]

    already_marked = sum(1 for r in rows if r["category"] == "Transfer")

    # Build amount index (skip already-Transfer)
    by_amt: dict[float, list[int]] = {}  # abs_amount -> list of row indices
    for idx, r in enumerate(rows):
        if r["category"] == "Transfer":
            continue
        key = round(abs(r["amount"]), 2)
        by_amt.setdefault(key, []).append(idx)

    paired_ids: set[int] = set()  # row ids (DB primary key) already paired

    # O(n) per amount bucket — iterate in date order so pairs are close together
    newly_marked = 0
    for i, r_a in enumerate(rows):
        if r_a["category"] == "Transfer" or r_a["id"] in paired_ids:
            continue

        key = round(abs(r_a["amount"]), 2)
        candidates = by_amt.get(key, [])

        for j in candidates:
            if j == i:
                continue
            r_b = rows[j]
            if r_b["category"] == "Transfer" or r_b["id"] in paired_ids:
                continue
            if _is_pair(
                r_a["amount"], r_a["date"], r_a["account_id"],
                r_b["amount"], r_b["date"], r_b["account_id"],
            ):
                rows[i]["category"] = "Transfer"
                rows[j]["category"] = "Transfer"
                paired_ids.update({r_a["id"], r_b["id"]})
                newly_marked += 2
                break

    # Write back only changed rows
    tx_map = {t.id: t for t in txs}
    for r in rows:
        if r["category"] != r["_orig_category"]:
            orm_tx = tx_map.get(r["id"])
            if orm_tx:
                orm_tx.category = "Transfer"

    db.commit()

    return {
        "scanned": len(rows),
        "newly_marked": newly_marked,
        "already_marked": already_marked,
    }
