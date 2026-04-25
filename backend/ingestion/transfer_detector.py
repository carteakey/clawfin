"""
Transfer pair detector — runs post-dedup, pre-insert.

Identifies internal transfers by pairing transactions with:
  - Matching absolute amounts (within 1 cent tolerance)
  - Opposite signs
  - Date delta ≤ 2 days
  - Different account_ids (or one has no account)

Matched transactions get category="Transfer" so they are excluded
from income/expense reporting without being deleted.

This is intentionally conservative: only mark Transfer when there
is a clear counterpart. Unmatched transactions are left as-is.
"""
from datetime import timedelta


def detect_internal_transfers(
    new_txs: list[dict],
    existing_txs: list[dict] | None = None,
) -> int:
    """
    Mark transfer pairs within new_txs (and optionally against existing_txs)
    as category="Transfer".

    new_txs: list of transaction dicts (mutable, category set in place).
    existing_txs: already-committed transactions to match against (read-only).
                  Pass the last 5 days of committed txns for SimpleFIN incremental syncs.

    Returns the number of newly marked transfers.
    """
    from datetime import date as date_type
    import datetime

    def _as_date(d) -> date_type:
        if isinstance(d, date_type):
            return d
        if isinstance(d, str):
            return date_type.fromisoformat(d)
        return d

    AMT_TOL = 0.01  # 1-cent tolerance for FX rounding

    marked = 0

    # Index existing transactions by (rounded_amount, date) for fast lookup
    # existing_txs are read-only, we only mark new ones
    existing_by_amt: dict[float, list[dict]] = {}
    for tx in (existing_txs or []):
        if tx.get("category") == "Transfer":
            continue
        key = round(abs(tx["amount"]), 2)
        existing_by_amt.setdefault(key, []).append(tx)

    # Track which new_txs indices have been paired
    paired: set[int] = set()

    # First pass: pair within new_txs
    for i, tx_a in enumerate(new_txs):
        if i in paired:
            continue
        if tx_a.get("category") == "Transfer":
            continue
        amt_a = tx_a["amount"]
        date_a = _as_date(tx_a["date"])

        for j, tx_b in enumerate(new_txs):
            if j <= i or j in paired:
                continue
            if tx_b.get("category") == "Transfer":
                continue
            amt_b = tx_b["amount"]
            date_b = _as_date(tx_b["date"])

            # Must be opposite signs, matching absolute amounts
            if amt_a * amt_b >= 0:
                continue  # same sign
            if abs(abs(amt_a) - abs(amt_b)) > AMT_TOL:
                continue
            if abs((date_b - date_a).days) > 2:
                continue

            # Don't pair transactions on the same account (same-account debit+credit is a correction)
            acct_a = tx_a.get("account_id")
            acct_b = tx_b.get("account_id")
            if acct_a and acct_b and acct_a == acct_b:
                continue

            # It's a transfer pair
            new_txs[i]["category"] = "Transfer"
            new_txs[j]["category"] = "Transfer"
            paired.add(i)
            paired.add(j)
            marked += 2
            break

    # Second pass: match unpaired new_txs against existing committed txns
    for i, tx_a in enumerate(new_txs):
        if i in paired:
            continue
        if tx_a.get("category") == "Transfer":
            continue
        amt_a = tx_a["amount"]
        date_a = _as_date(tx_a["date"])
        key = round(abs(amt_a), 2)

        candidates = existing_by_amt.get(key, [])
        for tx_b in candidates:
            amt_b = tx_b["amount"]
            date_b = _as_date(tx_b["date"])

            if amt_a * amt_b >= 0:
                continue
            if abs((date_b - date_a).days) > 2:
                continue

            acct_a = tx_a.get("account_id")
            acct_b = tx_b.get("account_id")
            if acct_a and acct_b and acct_a == acct_b:
                continue

            new_txs[i]["category"] = "Transfer"
            marked += 1
            break

    return marked
