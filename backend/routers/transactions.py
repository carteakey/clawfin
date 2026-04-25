"""Transactions API router."""
from collections import defaultdict
from datetime import date, timedelta
from statistics import mean, median
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from backend.db.database import get_db
from backend.db.models import Transaction, CategoryRule, AppConfig, Account
from backend.ingestion.categorizer import categorize_transactions, ai_categorize_batch
from backend.ingestion.transfer_detector import redetect_transfers_in_db

router = APIRouter()


class TransactionUpdate(BaseModel):
    category: str | None = None
    normalized_merchant: str | None = None
    save_rule: bool = False


@router.get("")
def list_transactions(
    days: int = Query(30, ge=1, le=3650),
    category: str = Query(None),
    account_id: int = Query(None),
    search: str = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    cutoff = date.today() - timedelta(days=days)
    q = db.query(Transaction).filter(Transaction.date >= cutoff)

    if category:
        q = q.filter(Transaction.category == category)
    if account_id:
        q = q.filter(Transaction.account_id == account_id)
    if search:
        q = q.filter(Transaction.merchant.ilike(f"%{search}%"))

    total = q.count()
    txs = q.order_by(Transaction.date.desc()).offset(offset).limit(limit).all()

    # Enrich with account name in one shot
    acct_ids = {tx.account_id for tx in txs if tx.account_id}
    accounts = (
        {a.id: a for a in db.query(Account).filter(Account.id.in_(acct_ids)).all()}
        if acct_ids else {}
    )

    return {
        "total": total,
        "transactions": [
            {
                "id": tx.id,
                "date": tx.date.isoformat(),
                "amount": tx.amount,
                "merchant": tx.merchant,
                "normalized_merchant": tx.normalized_merchant,
                "category": tx.category,
                "account_id": tx.account_id,
                "account_name": accounts[tx.account_id].name if tx.account_id in accounts else None,
                "account_institution": accounts[tx.account_id].institution if tx.account_id in accounts else None,
                "currency": tx.currency,
                "memo": tx.memo,
                "pending": bool(tx.pending),
                "source": tx.source.value if tx.source else None,
            }
            for tx in txs
        ],
    }


@router.patch("/{tx_id}")
def update_transaction(tx_id: int, update: TransactionUpdate, db: Session = Depends(get_db)):
    tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if not tx:
        return {"error": "Transaction not found"}, 404

    if update.category is not None:
        tx.category = update.category
    if update.normalized_merchant is not None:
        tx.normalized_merchant = update.normalized_merchant

    # If requested, learn a rule from this override so future imports stick.
    rule_id = None
    if update.save_rule and update.category:
        pattern = (tx.normalized_merchant or tx.merchant or "").strip().lower()
        if pattern:
            existing = db.query(CategoryRule).filter(CategoryRule.pattern == pattern).first()
            if existing:
                existing.category = update.category
                existing.priority = max(existing.priority, 1)
                rule_id = existing.id
            else:
                rule = CategoryRule(pattern=pattern, category=update.category, priority=1, is_regex=False)
                db.add(rule)
                db.flush()
                rule_id = rule.id

    db.commit()
    return {"status": "updated", "id": tx_id, "rule_id": rule_id}


@router.post("/accounts/reinfer-types")
def reinfer_account_types(db: Session = Depends(get_db)):
    """Re-run SimpleFin-style type inference on all accounts. One-shot cleanup
    for data that was imported before type-inference was wired up."""
    from backend.ingestion.simplefin import SimpleFinClient
    from backend.db.models import AccountType

    accts = db.query(Account).all()
    updated = 0
    for a in accts:
        inferred = SimpleFinClient._infer_type(a.name or "")
        try:
            new_type = AccountType(inferred)
        except ValueError:
            continue
        if a.account_type != new_type:
            a.account_type = new_type
            updated += 1
    db.commit()
    return {"status": "ok", "updated": updated, "total": len(accts)}


@router.post("/redetect-transfers")
def redetect_transfers(
    days: int = Query(None, ge=1, le=3650),
    db: Session = Depends(get_db),
):
    """
    Re-run internal transfer detection over committed transactions.

    Pairs same-amount / opposite-sign transactions within 2 days across
    different accounts and marks them category="Transfer". Covers:
      - Chequing → Savings
      - Chequing → TFSA / RRSP / FHSA (on-budget → investment)
      - Credit card payments

    Use ?days=N to limit to recent history; omit to scan all time.
    Already-Transfer rows are left as-is if they no longer have a counterpart.
    """
    result = redetect_transfers_in_db(db, days=days)
    return {"status": "ok", **result}


@router.get("/accounts")
def list_accounts_for_filter(db: Session = Depends(get_db)):
    accounts = db.query(Account).order_by(Account.institution, Account.name).all()
    return {
        "accounts": [
            {
                "id": a.id,
                "name": a.name,
                "institution": a.institution,
                "account_type": a.account_type.value if a.account_type else None,
                "currency": a.currency,
                "balance": round(a.balance or 0, 2),
                "available_balance": round(a.available_balance, 2) if a.available_balance is not None else None,
                "last_sync_at": a.last_sync_at.isoformat() if a.last_sync_at else None,
                "last_successful_balance_date": a.last_successful_balance_date.isoformat() if a.last_successful_balance_date else None,
                "last_successful_transaction_date": a.last_successful_transaction_date.isoformat() if a.last_successful_transaction_date else None,
                "last_sync_error": a.last_sync_error,
                "simplefin_account_present": bool(a.simplefin_account_present),
                "stale_reason": a.stale_reason,
                "on_budget": bool(a.on_budget),
                "source": a.source.value if a.source else None,
            }
            for a in accounts
        ]
    }


from fastapi import HTTPException

class AccountUpdate(BaseModel):
    on_budget: bool | None = None

@router.patch("/accounts/{account_id}")
def update_account(account_id: int, update: AccountUpdate, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    if update.on_budget is not None:
        account.on_budget = update.on_budget

    db.commit()
    return {"status": "updated", "id": account_id}

@router.delete("/accounts/{account_id}")
def delete_account(account_id: int, db: Session = Depends(get_db)):
    from backend.db.models import Holding
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    db.query(Transaction).filter(Transaction.account_id == account_id).delete()
    db.query(Holding).filter(Holding.account_id == account_id).delete()
    db.delete(account)
    db.commit()
    return {"status": "deleted"}


@router.get("/recurring")
def list_recurring(db: Session = Depends(get_db)):
    """
    Detect recurring outflows (subscriptions, EMIs, bills, insurance).
    Heuristic: same normalized merchant, ≥3 occurrences in last 180 days,
    stable amount (±15%), cadence 6-35 days. Classifies each.
    """
    lookback = date.today() - timedelta(days=180)
    txs = (
        db.query(Transaction)
        .filter(
            Transaction.date >= lookback,
            Transaction.amount < 0,
            Transaction.category != "Transfer",
        )
        .all()
    )

    by_merchant: dict[str, list[Transaction]] = defaultdict(list)
    for tx in txs:
        key = (tx.normalized_merchant or tx.merchant or "").strip().lower()
        if key:
            by_merchant[key].append(tx)

    rows = []
    for merchant, items in by_merchant.items():
        if len(items) < 3:
            continue
        items.sort(key=lambda t: t.date)
        intervals = [(items[i].date - items[i - 1].date).days for i in range(1, len(items))]
        if not intervals:
            continue
        cadence = median(intervals)
        if cadence < 6 or cadence > 35:
            continue

        amounts = [t.amount for t in items]
        avg_amt = mean(amounts)
        if avg_amt == 0:
            continue
        variance_ok = all(abs(a - avg_amt) / abs(avg_amt) <= 0.15 for a in amounts)
        if not variance_ok:
            continue

        cadence_days = int(round(cadence))
        annual = abs(avg_amt) * (365 / cadence)
        last = items[-1]
        next_est = last.date + timedelta(days=cadence_days)

        rows.append({
            "merchant": merchant,
            "display_name": last.merchant,
            "category": last.category or "Other",
            "avg_amount": round(abs(avg_amt), 2),
            "cadence_days": cadence_days,
            "count": len(items),
            "annual_cost": round(annual, 2),
            "last_charge": last.date.isoformat(),
            "next_estimated": next_est.isoformat(),
            "currency": last.currency,
        })

    rows.sort(key=lambda s: s["annual_cost"], reverse=True)
    total_annual = round(sum(s["annual_cost"] for s in rows), 2)
    total_monthly = round(total_annual / 12, 2)

    by_category: dict[str, float] = defaultdict(float)
    for r in rows:
        by_category[r["category"]] += r["annual_cost"]

    return {
        "recurring": rows,
        "count": len(rows),
        "total_annual": total_annual,
        "total_monthly": total_monthly,
        "by_category": {k: round(v, 2) for k, v in sorted(by_category.items(), key=lambda x: -x[1])},
    }


# Legacy alias
@router.get("/subscriptions")
def list_subscriptions_alias(db: Session = Depends(get_db)):
    return list_recurring(db)


@router.post("/recategorize")
def recategorize(db: Session = Depends(get_db)):
    """Run the categorizer over every transaction and persist any changes."""
    txs = db.query(Transaction).all()
    payload = [
        {
            "_id": tx.id,
            "merchant": (tx.normalized_merchant or tx.merchant or ""),
            "category": tx.category,
        }
        for tx in txs
    ]

    # Honor the experimental AI flag
    flag = db.query(AppConfig).filter(AppConfig.key == "ai_categorization_enabled").first()
    ai_enabled = bool(flag and flag.value.strip().lower() in ("1", "true", "yes", "on"))
    ai_fn = ai_categorize_batch if ai_enabled else None

    categorize_transactions(payload, db, ai_categorize_fn=ai_fn)

    updated = 0
    by_id = {tx.id: tx for tx in txs}
    for row in payload:
        tx = by_id.get(row["_id"])
        if tx and tx.category != row["category"]:
            tx.category = row["category"]
            updated += 1
    db.commit()
    return {"status": "ok", "updated": updated, "total": len(txs)}
