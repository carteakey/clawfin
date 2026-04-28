"""Transactions API router."""
import csv
import io
import uuid
from collections import defaultdict
from datetime import date as dt_date, timedelta
from statistics import mean, median
from fastapi import APIRouter, BackgroundTasks, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from backend.db.database import SessionLocal, get_db
from backend.db.models import Transaction, CategoryRule, AppConfig, Account, AccountType, DataSource
from backend.ingestion.categorizer import categorize_transactions, ai_categorize_batch
from backend.ingestion.transfer_detector import redetect_transfers_in_db

router = APIRouter()
RECATEGORIZE_JOBS: dict[str, dict] = {}
SORT_COLUMNS = {
    "date": Transaction.date,
    "merchant": Transaction.merchant,
    "category": Transaction.category,
    "amount": Transaction.amount,
    "account": Account.name,
    "account_name": Account.name,
    "source": Transaction.source,
}


class TransactionUpdate(BaseModel):
    date: dt_date | None = None
    amount: float | None = None
    merchant: str | None = None
    category: str | None = None
    account_id: int | None = None
    currency: str | None = None
    memo: str | None = None
    pending: bool | None = None
    normalized_merchant: str | None = None
    save_rule: bool = False


class TransactionCreate(BaseModel):
    date: dt_date
    amount: float
    merchant: str
    account_id: int
    category: str = "Other"
    currency: str = "CAD"
    memo: str | None = None
    pending: bool = False


class BulkTransactionUpdate(BaseModel):
    ids: list[int]
    category: str | None = None
    delete: bool = False


@router.get("")
def list_transactions(
    days: int = Query(30, ge=1, le=3650),
    start_date: dt_date = Query(None),
    end_date: dt_date = Query(None),
    amount_min: float = Query(None),
    amount_max: float = Query(None),
    category: str = Query(None),
    account_id: int = Query(None),
    search: str = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("date"),
    sort_dir: str = Query("desc"),
    include_off_budget: bool = Query(False),
    db: Session = Depends(get_db),
):
    q = _filtered_transaction_query(
        db,
        days=days,
        start_date=start_date,
        end_date=end_date,
        amount_min=amount_min,
        amount_max=amount_max,
        category=category,
        account_id=account_id,
        search=search,
        include_off_budget=include_off_budget,
    )

    total = q.count()
    txs = _apply_transaction_sort(q, sort_by, sort_dir).offset(offset).limit(limit).all()
    return {"total": total, "transactions": _serialize_transactions(txs, db)}


@router.get("/export.csv")
def export_transactions_csv(
    days: int = Query(30, ge=1, le=3650),
    start_date: dt_date = Query(None),
    end_date: dt_date = Query(None),
    amount_min: float = Query(None),
    amount_max: float = Query(None),
    category: str = Query(None),
    account_id: int = Query(None),
    search: str = Query(None),
    sort_by: str = Query("date"),
    sort_dir: str = Query("desc"),
    include_off_budget: bool = Query(False),
    db: Session = Depends(get_db),
):
    q = (
        _filtered_transaction_query(
            db,
            days=days,
            start_date=start_date,
            end_date=end_date,
            amount_min=amount_min,
            amount_max=amount_max,
            category=category,
            account_id=account_id,
            search=search,
            include_off_budget=include_off_budget,
        )
    )
    txs = _apply_transaction_sort(q, sort_by, sort_dir).all()
    rows = _serialize_transactions(txs, db)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        "id", "date", "amount", "merchant", "normalized_merchant", "category",
        "account_id", "account_name", "account_institution", "currency", "memo",
        "pending", "source",
    ])
    writer.writeheader()
    writer.writerows(rows)
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=clawfin-ledger.csv"},
    )


def _filtered_transaction_query(
    db: Session,
    days: int,
    start_date: dt_date | None = None,
    end_date: dt_date | None = None,
    amount_min: float | None = None,
    amount_max: float | None = None,
    category: str | None = None,
    account_id: int | None = None,
    search: str | None = None,
    include_off_budget: bool = False,
):
    cutoff = start_date or (dt_date.today() - timedelta(days=days))
    q = db.query(Transaction).outerjoin(Account, Transaction.account_id == Account.id).filter(Transaction.date >= cutoff)
    if end_date:
        q = q.filter(Transaction.date <= end_date)
    if amount_min is not None:
        q = q.filter(Transaction.amount >= amount_min)
    if amount_max is not None:
        q = q.filter(Transaction.amount <= amount_max)
    if not include_off_budget:
        from sqlalchemy import or_
        q = q.filter(
            or_(Transaction.account_id.is_(None), Account.on_budget.is_(True))
        )
    if category:
        q = q.filter(Transaction.category == category)
    if account_id:
        q = q.filter(Transaction.account_id == account_id)
    if search:
        needle = f"%{search}%"
        q = q.filter(Transaction.merchant.ilike(needle))
    return q


def _apply_transaction_sort(q, sort_by: str, sort_dir: str):
    col = SORT_COLUMNS.get((sort_by or "").lower(), Transaction.date)
    ordered = col.asc() if (sort_dir or "").lower() == "asc" else col.desc()
    return q.order_by(ordered, Transaction.id.desc())


def _serialize_transactions(txs: list[Transaction], db: Session) -> list[dict]:
    # Enrich with account name in one shot
    acct_ids = {tx.account_id for tx in txs if tx.account_id}
    accounts = (
        {a.id: a for a in db.query(Account).filter(Account.id.in_(acct_ids)).all()}
        if acct_ids else {}
    )
    return [
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
    ]


def _manual_account(db: Session, account_id: int) -> Account:
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if account.source != DataSource.MANUAL:
        raise HTTPException(status_code=400, detail="Manual transactions must use a manual account")
    return account


def _next_hash(
    db: Session,
    tx_date: dt_date,
    amount: float,
    merchant: str,
    account_id: int | None,
    exclude_id: int | None = None,
) -> tuple[str, int]:
    sequence = 0
    while True:
        tx_hash = Transaction.compute_hash(tx_date, amount, merchant, account_id, sequence)
        q = db.query(Transaction.id).filter(Transaction.hash == tx_hash)
        if exclude_id is not None:
            q = q.filter(Transaction.id != exclude_id)
        exists = q.first()
        if not exists:
            return tx_hash, sequence
        sequence += 1


@router.post("")
def create_transaction(req: TransactionCreate, db: Session = Depends(get_db)):
    account = _manual_account(db, req.account_id)
    merchant = req.merchant.strip()
    if not merchant:
        raise HTTPException(status_code=422, detail="Merchant is required")
    tx_hash, sequence = _next_hash(db, req.date, req.amount, merchant, account.id)
    tx = Transaction(
        date=req.date,
        amount=req.amount,
        merchant=merchant,
        normalized_merchant=merchant,
        category=req.category or "Other",
        account_id=account.id,
        source=DataSource.MANUAL,
        currency=(req.currency or account.currency or "CAD").upper(),
        hash=tx_hash,
        sequence=sequence,
        memo=req.memo,
        pending=req.pending,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return {"status": "created", "transaction": _serialize_transactions([tx], db)[0]}


@router.patch("/{tx_id}")
def update_transaction(tx_id: int, update: TransactionUpdate, db: Session = Depends(get_db)):
    tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if any(v is not None for v in [update.date, update.amount, update.merchant, update.account_id, update.currency, update.memo, update.pending]):
        if tx.source != DataSource.MANUAL:
            raise HTTPException(status_code=400, detail="Only manual transactions can be edited beyond category")

    if update.account_id is not None:
        _manual_account(db, update.account_id)
        tx.account_id = update.account_id
    if update.date is not None:
        tx.date = update.date
    if update.amount is not None:
        tx.amount = update.amount
    if update.merchant is not None:
        merchant = update.merchant.strip()
        if not merchant:
            raise HTTPException(status_code=422, detail="Merchant is required")
        tx.merchant = merchant
        tx.normalized_merchant = merchant
    if update.currency is not None:
        tx.currency = update.currency.upper()
    if update.memo is not None:
        tx.memo = update.memo
    if update.pending is not None:
        tx.pending = update.pending

    if update.category is not None:
        tx.category = update.category
        if update.save_rule and tx.merchant:
            # Upsert rule
            rule = db.query(CategoryRule).filter(CategoryRule.pattern == tx.merchant).first()
            if rule:
                rule.category = update.category
            else:
                db.add(CategoryRule(pattern=tx.merchant, category=update.category, priority=10))

    if update.normalized_merchant is not None:
        tx.normalized_merchant = update.normalized_merchant

    if tx.source == DataSource.MANUAL:
        tx.hash, tx.sequence = _next_hash(db, tx.date, tx.amount, tx.merchant, tx.account_id, exclude_id=tx.id)

    db.commit()
    return {"status": "ok", "id": tx_id}


@router.delete("/{tx_id}")
def delete_transaction(tx_id: int, db: Session = Depends(get_db)):
    tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if tx.source != DataSource.MANUAL:
        raise HTTPException(status_code=400, detail="Only manual transactions can be deleted")
    db.delete(tx)
    db.commit()
    return {"status": "deleted", "id": tx_id}


@router.post("/bulk")
def bulk_update_transactions(req: BulkTransactionUpdate, db: Session = Depends(get_db)):
    ids = sorted(set(req.ids))
    if not ids:
        raise HTTPException(status_code=422, detail="No transactions selected")
    txs = db.query(Transaction).filter(Transaction.id.in_(ids)).all()
    if len(txs) != len(ids):
        raise HTTPException(status_code=404, detail="One or more transactions were not found")
    if req.delete:
        non_manual = [tx.id for tx in txs if tx.source != DataSource.MANUAL]
        if non_manual:
            raise HTTPException(status_code=400, detail="Bulk delete is limited to manual transactions")
        for tx in txs:
            db.delete(tx)
        db.commit()
        return {"status": "deleted", "count": len(txs)}
    if req.category:
        for tx in txs:
            tx.category = req.category
        db.commit()
        return {"status": "updated", "count": len(txs)}
    raise HTTPException(status_code=422, detail="No bulk action requested")


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


class AccountUpdate(BaseModel):
    on_budget: bool | None = None
    account_type: AccountType | None = None


class AccountCreate(BaseModel):
    name: str
    institution: str
    account_type: AccountType
    currency: str = "CAD"
    on_budget: bool = True


@router.post("/accounts")
def create_account(req: AccountCreate, db: Session = Depends(get_db)):
    account = Account(
        name=req.name,
        institution=req.institution,
        account_type=req.account_type,
        currency=req.currency,
        on_budget=req.on_budget,
        source=DataSource.MANUAL,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return {"status": "created", "id": account.id}


@router.patch("/accounts/{account_id}")
def update_account(account_id: int, update: AccountUpdate, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    if update.on_budget is not None:
        account.on_budget = update.on_budget
    if update.account_type is not None:
        account.account_type = update.account_type

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
    stable amount (±15%), cadence 5-45 days. Classifies each.
    """
    lookback = dt_date.today() - timedelta(days=180)
    from backend.routers.dashboard import _budget_transaction_query
    txs = (
        _budget_transaction_query(db)
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
        if cadence < 5 or cadence > 45:
            # Focus on weekly-to-monthly recurring; skip daily noise and annual events
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
def recategorize(
    background_tasks: BackgroundTasks,
    background: bool = Query(False),
    db: Session = Depends(get_db),
):
    """Run the categorizer over every transaction and persist any changes."""
    if background:
        job_id = uuid.uuid4().hex
        RECATEGORIZE_JOBS[job_id] = {
            "id": job_id,
            "status": "queued",
            "processed": 0,
            "updated": 0,
            "total": 0,
            "error": None,
        }
        background_tasks.add_task(_run_recategorize_job, job_id)
        return RECATEGORIZE_JOBS[job_id]

    return _run_recategorize(db)


@router.get("/recategorize/{job_id}")
def get_recategorize_job(job_id: str):
    job = RECATEGORIZE_JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Recategorize job not found")
    return job


def _run_recategorize_job(job_id: str):
    with SessionLocal() as db:
        try:
            _run_recategorize(db, job_id=job_id)
        except Exception as e:
            RECATEGORIZE_JOBS[job_id].update({
                "status": "failed",
                "error": str(e)[:500],
            })


def _run_recategorize(db: Session, job_id: str | None = None):
    txs = db.query(Transaction).order_by(Transaction.id.asc()).all()
    total = len(txs)
    if job_id:
        RECATEGORIZE_JOBS[job_id].update({
            "status": "running",
            "total": total,
            "processed": 0,
            "updated": 0,
        })

    # Honor the experimental AI flag
    flag = db.query(AppConfig).filter(AppConfig.key == "ai_categorization_enabled").first()
    ai_enabled = bool(flag and flag.value.strip().lower() in ("1", "true", "yes", "on"))
    ai_fn = ai_categorize_batch if ai_enabled else None

    updated = 0
    chunk_size = 50 if ai_enabled else 250
    for start in range(0, total, chunk_size):
        chunk = txs[start:start + chunk_size]
        payload = [
            {
                "_id": tx.id,
                "merchant": (tx.normalized_merchant or tx.merchant or ""),
                "category": tx.category,
            }
            for tx in chunk
        ]
        categorize_transactions(payload, db, ai_categorize_fn=ai_fn)
        by_id = {tx.id: tx for tx in chunk}
        for row in payload:
            tx = by_id.get(row["_id"])
            if tx and tx.category != row["category"]:
                tx.category = row["category"]
                updated += 1
        db.commit()
        if job_id:
            RECATEGORIZE_JOBS[job_id].update({
                "processed": min(start + len(chunk), total),
                "updated": updated,
            })

    db.commit()
    if job_id:
        RECATEGORIZE_JOBS[job_id].update({
            "status": "complete",
            "processed": total,
            "updated": updated,
            "total": total,
        })
    return {"status": "ok", "updated": updated, "total": len(txs)}
