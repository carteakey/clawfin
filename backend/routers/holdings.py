"""Holdings API router."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.db.database import get_db
from backend.db.models import Holding

router = APIRouter()


@router.get("")
def list_holdings(db: Session = Depends(get_db)):
    holdings = db.query(Holding).all()

    total_book = sum(h.book_value for h in holdings)
    total_market = sum(h.market_value for h in holdings)

    return {
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
            }
            for h in holdings
        ],
    }
