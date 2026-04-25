"""Daily and weekly financial briefing generation."""
from collections import defaultdict
from datetime import date, timedelta
import json

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from backend.ai import provider
from backend.config import settings
from backend.db.models import Account, AccountType, Transaction

INVESTMENT_ACCOUNT_TYPES = {
    AccountType.TFSA,
    AccountType.RRSP,
    AccountType.FHSA,
    AccountType.MARGIN,
    AccountType.CRYPTO,
}


def _budget_transaction_query(db: Session):
    from sqlalchemy import and_
    return (
        db.query(Transaction)
        .outerjoin(Account, Transaction.account_id == Account.id)
        .filter(or_(
            Transaction.account_id.is_(None),
            and_(
                Account.account_type.notin_(INVESTMENT_ACCOUNT_TYPES),
                Account.on_budget.is_(True)
            )
        ))
    )


BRIEFING_SYSTEM_PROMPT = """You write concise personal finance status briefings for ClawFin.

Rules:
- Use only the supplied JSON context. Do not invent numbers.
- Be factual and direct. This is a status report, not financial advice.
- Mention the period, total spend, income, net cash flow, and the most important nudge.
- Call out stale accounts or reconnect needs if present.
- Keep the message notification-friendly: 6-10 short lines, no markdown table.
- Format money as CAD unless a value explicitly says otherwise.
"""


def resolve_period(period: str, end_date: date | None = None) -> tuple[date, date]:
    """Return inclusive start/end dates for a supported briefing period."""
    end = end_date or date.today()
    if period == "daily":
        return end, end
    if period == "weekly":
        return end - timedelta(days=6), end
    raise ValueError("period must be 'daily' or 'weekly'")


def build_transaction_briefing_context(
    db: Session,
    period: str,
    end_date: date | None = None,
    include_transactions: bool = False,
    max_transactions: int = 25,
) -> dict:
    """Build deterministic transaction context for an LLM or external automator."""
    start, end = resolve_period(period, end_date)
    days = (end - start).days + 1
    prev_start = start - timedelta(days=days)
    prev_end = start - timedelta(days=1)

    txs = (
        _budget_transaction_query(db)
        .filter(Transaction.date >= start, Transaction.date <= end)
        .order_by(Transaction.date.desc(), Transaction.id.desc())
        .all()
    )
    prev_txs = (
        _budget_transaction_query(db)
        .filter(Transaction.date >= prev_start, Transaction.date <= prev_end)
        .all()
    )

    income = sum(tx.amount for tx in txs if tx.amount > 0)
    expenses = abs(sum(tx.amount for tx in txs if tx.amount < 0))
    prev_expenses = abs(sum(tx.amount for tx in prev_txs if tx.amount < 0))
    net_cash_flow = income - expenses

    category_totals: dict[str, dict] = defaultdict(lambda: {"amount": 0.0, "count": 0})
    merchant_totals: dict[str, dict] = defaultdict(lambda: {"amount": 0.0, "count": 0})
    daily_spending: dict[str, float] = defaultdict(float)

    for tx in txs:
        if tx.amount >= 0:
            continue
        category = tx.category or "Other"
        merchant = _merchant_name(tx)
        amount = abs(tx.amount)
        category_totals[category]["amount"] += amount
        category_totals[category]["count"] += 1
        merchant_totals[merchant]["amount"] += amount
        merchant_totals[merchant]["count"] += 1
        daily_spending[tx.date.isoformat()] += amount

    top_categories = _ranked_rows(category_totals, expenses, limit=8)
    top_merchants = _ranked_rows(merchant_totals, expenses, limit=8)
    largest_transactions = _largest_transactions(txs, limit=8)
    unusual_spending = _unusual_spending(category_totals, prev_txs, expenses)
    recurring = _recurring_activity(db, start, end)
    account_freshness = _account_freshness(db, end)

    context = {
        "period": period,
        "range": {"start": start.isoformat(), "end": end.isoformat(), "days": days},
        "totals": {
            "income": round(income, 2),
            "expenses": round(expenses, 2),
            "net_cash_flow": round(net_cash_flow, 2),
            "previous_period_expenses": round(prev_expenses, 2),
            "expenses_delta_pct": _pct_delta(expenses, prev_expenses),
        },
        "counts": {
            "transactions": len(txs),
            "pending": sum(1 for tx in txs if tx.pending),
            "uncategorized": sum(1 for tx in txs if not tx.category or tx.category == "Other"),
        },
        "top_categories": top_categories,
        "top_merchants": top_merchants,
        "largest_transactions": largest_transactions,
        "daily_spending": {k: round(v, 2) for k, v in sorted(daily_spending.items())},
        "unusual_spending": unusual_spending,
        "recurring_activity": recurring,
        "account_freshness": account_freshness,
        "privacy": {
            "transactions_included": include_transactions,
        },
    }

    if include_transactions:
        context["transactions"] = [
            _transaction_row(tx)
            for tx in txs[:max(0, min(max_transactions, 100))]
        ]

    return context


async def generate_transaction_briefing(context: dict) -> str:
    """Generate a notification-ready briefing from deterministic context."""
    if not provider.is_configured():
        raise RuntimeError("AI provider not configured")

    response = await provider.chat_completion(
        messages=[
            {"role": "system", "content": BRIEFING_SYSTEM_PROMPT},
            {"role": "user", "content": f"Write the briefing from this JSON context:\n{json.dumps(context)}"},
        ],
        temperature=0.2,
    )
    return (response.get("content") or "").strip()


def _merchant_name(tx: Transaction) -> str:
    return tx.normalized_merchant or tx.merchant or "Unknown"


def _transaction_row(tx: Transaction) -> dict:
    return {
        "date": tx.date.isoformat(),
        "amount": round(tx.amount, 2),
        "merchant": _merchant_name(tx),
        "category": tx.category or "Other",
        "currency": tx.currency,
        "pending": bool(tx.pending),
    }


def _ranked_rows(groups: dict[str, dict], total: float, limit: int) -> list[dict]:
    rows = []
    for name, data in groups.items():
        amount = data["amount"]
        rows.append({
            "name": name,
            "amount": round(amount, 2),
            "count": data["count"],
            "pct_of_spend": round(amount / total * 100, 1) if total else 0,
        })
    return sorted(rows, key=lambda row: row["amount"], reverse=True)[:limit]


def _largest_transactions(txs: list[Transaction], limit: int) -> list[dict]:
    outflows = [tx for tx in txs if tx.amount < 0]
    outflows.sort(key=lambda tx: abs(tx.amount), reverse=True)
    return [_transaction_row(tx) for tx in outflows[:limit]]


def _unusual_spending(current_categories: dict[str, dict], prev_txs: list[Transaction], total: float) -> list[dict]:
    prev_categories: dict[str, float] = defaultdict(float)
    for tx in prev_txs:
        if tx.amount < 0:
            prev_categories[tx.category or "Other"] += abs(tx.amount)

    rows = []
    for category, data in current_categories.items():
        current = data["amount"]
        previous = prev_categories.get(category, 0.0)
        delta_pct = _pct_delta(current, previous)
        if current >= 25 and (previous == 0 or delta_pct >= 50):
            rows.append({
                "category": category,
                "amount": round(current, 2),
                "previous_amount": round(previous, 2),
                "delta_pct": delta_pct,
                "pct_of_spend": round(current / total * 100, 1) if total else 0,
            })
    return sorted(rows, key=lambda row: row["amount"], reverse=True)[:5]


def _recurring_activity(db: Session, start: date, end: date) -> dict:
    lookback = end - timedelta(days=180)
    txs = (
        _budget_transaction_query(db)
        .filter(Transaction.date >= lookback, Transaction.date <= end, Transaction.amount < 0)
        .all()
    )

    by_merchant: dict[str, list[Transaction]] = defaultdict(list)
    for tx in txs:
        key = (tx.normalized_merchant or tx.merchant or "").strip().lower()
        if key:
            by_merchant[key].append(tx)

    seen = []
    due_soon = []
    for items in by_merchant.values():
        if len(items) < 3:
            continue
        items.sort(key=lambda tx: tx.date)
        intervals = [(items[i].date - items[i - 1].date).days for i in range(1, len(items))]
        cadence = _median(intervals)
        if cadence < 6 or cadence > 45:
            continue
        amounts = [tx.amount for tx in items]
        avg_amount = sum(amounts) / len(amounts)
        last = items[-1]
        row = {
            "merchant": _merchant_name(last),
            "avg_amount": round(abs(avg_amount), 2),
            "cadence_days": int(round(cadence)),
            "last_seen": last.date.isoformat(),
            "next_estimated": (last.date + timedelta(days=int(round(cadence)))).isoformat(),
            "category": last.category or "Other",
        }
        if start <= last.date <= end:
            seen.append(row)
        next_estimated = last.date + timedelta(days=int(round(cadence)))
        if end < next_estimated <= end + timedelta(days=7):
            due_soon.append(row)

    return {
        "seen_this_period": sorted(seen, key=lambda row: row["avg_amount"], reverse=True)[:10],
        "due_next_7_days": sorted(due_soon, key=lambda row: row["avg_amount"], reverse=True)[:10],
    }


def _account_freshness(db: Session, end: date) -> dict:
    accounts = db.query(Account).all()
    latest_by_account = {
        account_id: latest
        for account_id, latest in (
            db.query(Transaction.account_id, func.max(Transaction.date))
            .filter(Transaction.account_id.isnot(None))
            .group_by(Transaction.account_id)
            .all()
        )
    }

    stale = []
    for account in accounts:
        dates = []
        if account.last_successful_balance_date:
            dates.append(account.last_successful_balance_date.date())
        if account.balance_date:
            dates.append(account.balance_date.date())
        if account.last_successful_transaction_date:
            dates.append(account.last_successful_transaction_date)
        latest_tx_date = latest_by_account.get(account.id)
        if isinstance(latest_tx_date, str):
            latest_tx_date = date.fromisoformat(latest_tx_date)
        if latest_tx_date:
            dates.append(latest_tx_date)
        latest = max(dates) if dates else None
        activity_days_stale = (end - latest).days if latest else None
        sync_days_stale = (end - account.last_sync_at.date()).days if account.last_sync_at else None
        stale_reason = _account_stale_reason(account, sync_days_stale)
        if stale_reason:
            stale.append({
                "account_id": account.id,
                "name": account.name,
                "institution": account.institution,
                "latest_activity_date": latest.isoformat() if latest else None,
                "days_stale": sync_days_stale,
                "activity_days_stale": activity_days_stale,
                "last_sync_at": account.last_sync_at.isoformat() if account.last_sync_at else None,
                "last_sync_error": account.last_sync_error,
                "simplefin_account_present": bool(account.simplefin_account_present),
                "stale_reason": stale_reason,
            })

    return {
        "account_count": len(accounts),
        "stale_accounts": stale,
        "reconnect_nudge": bool(stale),
    }


def _account_stale_reason(account: Account, sync_days_stale: int | None) -> str | None:
    if account.stale_reason:
        return account.stale_reason
    if account.last_sync_error:
        return "simplefin_sync_error"
    if account.simplefin_account_present is False:
        return "missing_from_simplefin_response"
    if sync_days_stale is None:
        return "never_synced"
    if sync_days_stale >= settings.SIMPLEFIN_STALE_DAYS:
        return "simplefin_sync_stale"
    return None


def _pct_delta(current: float, previous: float) -> float:
    if previous == 0:
        return 0 if current == 0 else 100
    return round((current - previous) / previous * 100, 1)


def _median(values: list[int]) -> float:
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[mid])
    return (ordered[mid - 1] + ordered[mid]) / 2
