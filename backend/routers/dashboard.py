"""Dashboard API router — pre-computed KPIs and breakdowns."""
from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.db.database import get_db
from backend.db.models import Transaction, Account, Holding

router = APIRouter()


@router.get("")
def get_dashboard(
    days: int = Query(30, ge=1, le=3650),
    db: Session = Depends(get_db),
):
    cutoff = date.today() - timedelta(days=days)
    prev_cutoff = cutoff - timedelta(days=days)

    # Current period transactions
    txs = db.query(Transaction).filter(Transaction.date >= cutoff).all()
    prev_txs = db.query(Transaction).filter(
        Transaction.date >= prev_cutoff, Transaction.date < cutoff
    ).all()

    # KPIs
    income = sum(tx.amount for tx in txs if tx.amount > 0)
    expenses = abs(sum(tx.amount for tx in txs if tx.amount < 0))
    prev_income = sum(tx.amount for tx in prev_txs if tx.amount > 0)
    prev_expenses = abs(sum(tx.amount for tx in prev_txs if tx.amount < 0))

    savings_rate = ((income - expenses) / income * 100) if income > 0 else 0

    # Net worth
    accounts = db.query(Account).all()
    holdings = db.query(Holding).all()
    total_cash = sum(a.balance for a in accounts)
    total_investments = sum(h.market_value for h in holdings)
    net_worth = total_cash + total_investments

    # Spending by category
    category_spending = {}
    for tx in txs:
        if tx.amount < 0:
            cat = tx.category or "Other"
            category_spending.setdefault(cat, {"total": 0, "count": 0})
            category_spending[cat]["total"] += abs(tx.amount)
            category_spending[cat]["count"] += 1

    # Previous period for deltas
    prev_category_spending = {}
    for tx in prev_txs:
        if tx.amount < 0:
            cat = tx.category or "Other"
            prev_category_spending.setdefault(cat, 0)
            prev_category_spending[cat] += abs(tx.amount)

    spending_breakdown = []
    for cat, data in sorted(category_spending.items(), key=lambda x: -x[1]["total"]):
        prev_amount = prev_category_spending.get(cat, 0)
        delta_pct = ((data["total"] - prev_amount) / prev_amount * 100) if prev_amount > 0 else 0
        spending_breakdown.append({
            "category": cat,
            "amount": round(data["total"], 2),
            "count": data["count"],
            "pct_of_total": round(data["total"] / expenses * 100, 1) if expenses > 0 else 0,
            "delta_pct": round(delta_pct, 1),
        })

    # Top merchants
    merchant_totals = {}
    for tx in txs:
        if tx.amount < 0:
            m = tx.normalized_merchant or tx.merchant
            merchant_totals.setdefault(m, {"total": 0, "count": 0})
            merchant_totals[m]["total"] += abs(tx.amount)
            merchant_totals[m]["count"] += 1

    top_merchants = [
        {"merchant": m, "amount": round(d["total"], 2), "count": d["count"]}
        for m, d in sorted(merchant_totals.items(), key=lambda x: -x[1]["total"])[:10]
    ]

    # Daily spending (for bar chart)
    daily_spending = {}
    for tx in txs:
        if tx.amount < 0:
            day = tx.date.isoformat()
            daily_spending.setdefault(day, 0)
            daily_spending[day] += abs(tx.amount)

    return {
        "period_days": days,
        "kpis": {
            "income": round(income, 2),
            "expenses": round(expenses, 2),
            "savings_rate": round(savings_rate, 1),
            "net_worth": round(net_worth, 2),
            "income_delta_pct": round(((income - prev_income) / prev_income * 100) if prev_income > 0 else 0, 1),
            "expenses_delta_pct": round(((expenses - prev_expenses) / prev_expenses * 100) if prev_expenses > 0 else 0, 1),
        },
        "spending_breakdown": spending_breakdown,
        "top_merchants": top_merchants,
        "daily_spending": dict(sorted(daily_spending.items())),
        "account_count": len(accounts),
        "transaction_count": len(txs),
    }
