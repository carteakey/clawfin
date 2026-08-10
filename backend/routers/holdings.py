"""Holdings API router."""
from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.db.database import get_db
from backend.db.models import Holding, Account

router = APIRouter()


@router.get("/dates")
def list_snapshot_dates(db: Session = Depends(get_db)):
    """Distinct as_of_date values in the Holdings table, newest first."""
    rows = (
        db.query(Holding.as_of_date, func.count(Holding.id))
        .group_by(Holding.as_of_date)
        .order_by(Holding.as_of_date.desc())
        .all()
    )
    dates = [
        {"date": d.isoformat() if d else None, "count": c}
        for d, c in rows if d is not None
    ]
    return {"dates": dates, "count": len(dates)}


@router.get("")
def list_holdings(
    as_of: str | None = Query(None, description="YYYY-MM-DD snapshot date; defaults to latest"),
    db: Session = Depends(get_db),
):
    # Pick effective snapshot date
    effective: date | None = None
    if as_of:
        try:
            effective = date.fromisoformat(as_of)
        except ValueError:
            effective = None

    if effective is None:
        latest = db.query(func.max(Holding.as_of_date)).scalar()
        effective = latest

    query = db.query(Holding)
    if effective is not None:
        query = query.filter(Holding.as_of_date == effective)
    holdings = query.all()

    # Resolve account type labels for grouping
    acct_ids = {h.account_id for h in holdings if h.account_id}
    acct_types = {
        a.id: (a.account_type.value if a.account_type else None)
        for a in db.query(Account).filter(Account.id.in_(acct_ids)).all()
    } if acct_ids else {}

    total_book = sum(h.book_value for h in holdings)
    total_market = sum(h.market_value for h in holdings)

    return {
        "as_of": effective.isoformat() if effective else None,
        "total_book_value": round(total_book, 2),
        "total_market_value": round(total_market, 2),
        "total_gain_loss": round(total_market - total_book, 2),
        "holdings": [
            {
                "id": h.id,
                "ticker": h.ticker,
                "asset_name": h.asset_name,
                "quantity": h.quantity,
                "book_value": h.book_value,
                "market_value": h.market_value,
                "gain_loss": round(h.market_value - h.book_value, 2),
                "gain_pct": round((h.market_value - h.book_value) / h.book_value * 100, 2) if h.book_value else 0,
                "currency": h.currency,
                "as_of_date": h.as_of_date.isoformat() if h.as_of_date else None,
                "account_id": h.account_id,
                "account_type": acct_types.get(h.account_id),
            }
            for h in holdings
        ],
    }
