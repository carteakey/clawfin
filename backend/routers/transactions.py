"""Transactions API router."""
from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from backend.db.database import get_db
from backend.db.models import Transaction

router = APIRouter()


class TransactionUpdate(BaseModel):
    category: str | None = None
    normalized_merchant: str | None = None


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
                "currency": tx.currency,
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

    db.commit()
    return {"status": "updated", "id": tx_id}
