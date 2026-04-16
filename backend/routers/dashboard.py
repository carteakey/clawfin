"""Dashboard API router — pre-computed KPIs and breakdowns."""
from collections import defaultdict
from datetime import date, timedelta
from statistics import mean, median
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.db.database import get_db
from backend.db.models import Transaction, Account, Holding, Snapshot

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


# ─── Net worth over time ─────────────────────────────────────────────

_PERIOD_DAYS = {"1M": 31, "3M": 92, "6M": 183, "1Y": 366, "ALL": 3650}


@router.get("/net-worth")
def get_net_worth(
    period: str = Query("1Y"),
    db: Session = Depends(get_db),
):
    """
    Returns a date series of net worth.

    Prefers Snapshot table when populated. Otherwise synthesizes a series
    from current Account balances + sum of Holdings by walking backward
    through Transaction history (running balance of cash-affecting txns).
    """
    days = _PERIOD_DAYS.get(period.upper(), 366)
    cutoff = date.today() - timedelta(days=days)

    # Prefer real snapshots if present
    snaps = (
        db.query(Snapshot)
        .filter(Snapshot.date >= cutoff)
        .order_by(Snapshot.date.asc())
        .all()
    )
    if snaps:
        return {
            "source": "snapshot",
            "period": period,
            "series": [{"date": s.date.isoformat(), "amount": round(s.net_worth, 2)} for s in snaps],
        }

    # Synthesize from current balances + transaction history
    accounts = db.query(Account).all()
    holdings = db.query(Holding).all()
    cash_now = sum(a.balance for a in accounts)
    investments_now = sum(h.market_value for h in holdings)
    current = cash_now + investments_now

    txs = (
        db.query(Transaction)
        .filter(Transaction.date >= cutoff)
        .order_by(Transaction.date.asc())
        .all()
    )

    # Running balance by walking backward: value(yesterday) = value(today) - today's txns
    # Pre-aggregate daily net-change
    daily_change: dict[date, float] = defaultdict(float)
    for tx in txs:
        daily_change[tx.date] += tx.amount

    today = date.today()
    series = []
    running = current
    day = today
    # Emit series from cutoff → today. Walk forward from cutoff using computed historical values.
    # First compute the value at cutoff by walking backward through daily_change from today.
    history_values: dict[date, float] = {today: current}
    d = today
    while d > cutoff:
        prev = d - timedelta(days=1)
        # value at prev = value at d - (txns that happened on d)
        history_values[prev] = history_values[d] - daily_change.get(d, 0.0)
        d = prev

    # Now emit sparsely — weekly for long periods, daily for short
    step = 1 if days <= 92 else 7
    d = cutoff
    while d <= today:
        series.append({"date": d.isoformat(), "amount": round(history_values.get(d, current), 2)})
        d += timedelta(days=step)

    # Ensure today is always the last point
    if series and series[-1]["date"] != today.isoformat():
        series.append({"date": today.isoformat(), "amount": round(current, 2)})

    return {"source": "synthetic", "period": period, "series": series}


# ─── Cash flow forecast ──────────────────────────────────────────────


def _detect_recurring(txs: list[Transaction], min_occurrences: int = 3, tolerance: float = 0.15) -> list[dict]:
    """
    Group transactions by normalized merchant; for each group check for a stable
    cadence (avg interval in days) and amount (within tolerance).
    Returns list of detected recurring series.
    """
    by_merchant: dict[str, list[Transaction]] = defaultdict(list)
    for tx in txs:
        key = (tx.normalized_merchant or tx.merchant).strip().lower()
        if key:
            by_merchant[key].append(tx)

    detected = []
    for merchant, items in by_merchant.items():
        if len(items) < min_occurrences:
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
        variance_ok = all(abs(a - avg_amt) / abs(avg_amt) <= tolerance for a in amounts) if avg_amt else False
        if not variance_ok:
            continue

        detected.append({
            "merchant": merchant,
            "avg_amount": round(avg_amt, 2),
            "cadence_days": int(round(cadence)),
            "count": len(items),
            "last_seen": items[-1].date.isoformat(),
        })

    detected.sort(key=lambda r: abs(r["avg_amount"]), reverse=True)
    return detected


@router.get("/cashflow-forecast")
def get_cashflow_forecast(
    months: int = Query(3, ge=1, le=12),
    db: Session = Depends(get_db),
):
    lookback = date.today() - timedelta(days=180)
    txs = db.query(Transaction).filter(Transaction.date >= lookback).all()
    recurring = _detect_recurring(txs)

    today = date.today()
    # Project forward for N months
    projected = []
    for m in range(1, months + 1):
        # Period end = today + m*30 days
        period_start = today + timedelta(days=(m - 1) * 30)
        period_end = today + timedelta(days=m * 30)
        label = period_end.strftime("%b %Y")

        proj_in = 0.0
        proj_out = 0.0
        for r in recurring:
            # How many times will this recurring fire in the window?
            cadence = r["cadence_days"]
            # Approximate: 30 / cadence occurrences per month
            occurrences = max(1, round(30 / cadence)) if cadence <= 30 else 0
            if cadence > 30:
                # Bi-monthly or quarterly — fire on alternating months
                occurrences = 1 if m % max(1, round(cadence / 30)) == 0 else 0
            amt = r["avg_amount"] * occurrences
            if amt >= 0:
                proj_in += amt
            else:
                proj_out += abs(amt)

        projected.append({
            "month": period_end.strftime("%Y-%m"),
            "label": label,
            "projected_in": round(proj_in, 2),
            "projected_out": round(proj_out, 2),
            "net": round(proj_in - proj_out, 2),
        })

    return {
        "months": projected,
        "detected_count": len(recurring),
        "recurring": recurring[:30],
    }
