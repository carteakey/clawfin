"""AI agent tools — functions the LLM can call to interact with ClawFin data."""
import json
from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.db.models import Transaction, Holding, Account, Snapshot, Category


# ─── Tool definitions (OpenAI function-calling format) ───────────────

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "query_spending",
            "description": "Query spending totals by category, merchant, or time range. Returns aggregated transaction data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Filter by category name (e.g., 'Groceries', 'Dining')"},
                    "merchant": {"type": "string", "description": "Search by merchant name (partial match)"},
                    "days": {"type": "integer", "description": "Number of days to look back (default 30)"},
                    "group_by": {"type": "string", "enum": ["category", "merchant", "month"], "description": "How to group results"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_account_balances",
            "description": "Get current balances for all accounts, grouped by type.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_holdings",
            "description": "Get current investment holdings with book and market values.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_net_worth",
            "description": "Calculate current net worth from all accounts and holdings.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "simulate_savings",
            "description": "Project future savings or investment growth.",
            "parameters": {
                "type": "object",
                "properties": {
                    "monthly_amount": {"type": "number", "description": "Monthly contribution in CAD"},
                    "annual_return": {"type": "number", "description": "Expected annual return rate (e.g., 0.07 for 7%)"},
                    "years": {"type": "integer", "description": "Number of years to project"},
                    "initial_balance": {"type": "number", "description": "Starting balance (default 0)"},
                },
                "required": ["monthly_amount", "years"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_transactions",
            "description": "Search for specific transactions by merchant name, amount range, or date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "merchant": {"type": "string", "description": "Merchant name to search (partial match)"},
                    "min_amount": {"type": "number", "description": "Minimum transaction amount"},
                    "max_amount": {"type": "number", "description": "Maximum transaction amount"},
                    "days": {"type": "integer", "description": "Number of days to look back"},
                    "limit": {"type": "integer", "description": "Max results (default 20)"},
                },
                "required": [],
            },
        },
    },
]


# ─── Tool implementations ───────────────────────────────────────────

def execute_tool(name: str, arguments: dict, db: Session) -> str:
    """Execute a tool by name and return JSON string result."""
    handlers = {
        "query_spending": _query_spending,
        "get_account_balances": _get_account_balances,
        "get_holdings": _get_holdings,
        "get_net_worth": _get_net_worth,
        "simulate_savings": _simulate_savings,
        "search_transactions": _search_transactions,
    }

    handler = handlers.get(name)
    if not handler:
        return json.dumps({"error": f"Unknown tool: {name}"})

    try:
        result = handler(db=db, **arguments)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def _query_spending(db: Session, category: str = None, merchant: str = None,
                    days: int = 30, group_by: str = "category") -> dict:
    cutoff = date.today() - timedelta(days=days)
    q = db.query(Transaction).filter(Transaction.date >= cutoff, Transaction.amount < 0)

    if category:
        q = q.filter(Transaction.category == category)
    if merchant:
        q = q.filter(Transaction.merchant.ilike(f"%{merchant}%"))

    txs = q.all()

    if group_by == "category":
        groups = {}
        for tx in txs:
            cat = tx.category or "Other"
            groups.setdefault(cat, 0)
            groups[cat] += abs(tx.amount)
        return {"period_days": days, "total": sum(groups.values()), "breakdown": dict(sorted(groups.items(), key=lambda x: -x[1]))}

    elif group_by == "merchant":
        groups = {}
        for tx in txs:
            m = tx.normalized_merchant or tx.merchant
            groups.setdefault(m, {"total": 0, "count": 0})
            groups[m]["total"] += abs(tx.amount)
            groups[m]["count"] += 1
        sorted_groups = dict(sorted(groups.items(), key=lambda x: -x[1]["total"])[:20])
        return {"period_days": days, "top_merchants": sorted_groups}

    elif group_by == "month":
        groups = {}
        for tx in txs:
            month_key = tx.date.strftime("%Y-%m")
            groups.setdefault(month_key, 0)
            groups[month_key] += abs(tx.amount)
        return {"period_days": days, "monthly": dict(sorted(groups.items()))}

    return {"period_days": days, "count": len(txs)}


def _get_account_balances(db: Session) -> dict:
    accounts = db.query(Account).all()
    result = []
    for a in accounts:
        result.append({
            "institution": a.institution,
            "name": a.name,
            "type": a.account_type.value if a.account_type else "other",
            "balance": a.balance,
            "currency": a.currency,
        })
    return {"accounts": result, "total_cad": sum(a.balance for a in accounts if a.currency == "CAD")}


def _get_holdings(db: Session) -> dict:
    holdings = db.query(Holding).all()
    result = []
    for h in holdings:
        gain = h.market_value - h.book_value
        result.append({
            "ticker": h.ticker,
            "name": h.asset_name,
            "quantity": h.quantity,
            "book_value": h.book_value,
            "market_value": h.market_value,
            "gain_loss": round(gain, 2),
            "gain_pct": round(gain / h.book_value * 100, 2) if h.book_value else 0,
            "currency": h.currency,
        })
    total_book = sum(h.book_value for h in holdings)
    total_market = sum(h.market_value for h in holdings)
    return {"holdings": result, "total_book": total_book, "total_market": total_market}


def _get_net_worth(db: Session) -> dict:
    accounts = db.query(Account).all()
    holdings = db.query(Holding).all()

    cash_assets = sum(a.balance for a in accounts if a.balance > 0)
    liabilities = abs(sum(a.balance for a in accounts if a.balance < 0))
    investments = sum(h.market_value for h in holdings)

    return {
        "cash_and_deposits": round(cash_assets, 2),
        "investments": round(investments, 2),
        "total_assets": round(cash_assets + investments, 2),
        "liabilities": round(liabilities, 2),
        "net_worth": round(cash_assets + investments - liabilities, 2),
    }


def _simulate_savings(db: Session, monthly_amount: float, years: int,
                       annual_return: float = 0.07, initial_balance: float = 0) -> dict:
    monthly_return = annual_return / 12
    balance = initial_balance
    months = years * 12
    projections = []

    for month in range(1, months + 1):
        balance = balance * (1 + monthly_return) + monthly_amount
        if month % 12 == 0 or month == months:
            projections.append({"year": month // 12, "balance": round(balance, 2)})

    total_contributed = initial_balance + monthly_amount * months
    return {
        "final_balance": round(balance, 2),
        "total_contributed": round(total_contributed, 2),
        "total_growth": round(balance - total_contributed, 2),
        "projections": projections,
    }


def _search_transactions(db: Session, merchant: str = None, min_amount: float = None,
                          max_amount: float = None, days: int = 90, limit: int = 20) -> dict:
    cutoff = date.today() - timedelta(days=days)
    q = db.query(Transaction).filter(Transaction.date >= cutoff)

    if merchant:
        q = q.filter(Transaction.merchant.ilike(f"%{merchant}%"))
    if min_amount is not None:
        q = q.filter(func.abs(Transaction.amount) >= min_amount)
    if max_amount is not None:
        q = q.filter(func.abs(Transaction.amount) <= max_amount)

    txs = q.order_by(Transaction.date.desc()).limit(limit).all()
    return {
        "count": len(txs),
        "transactions": [
            {"date": tx.date.isoformat(), "merchant": tx.merchant, "amount": tx.amount,
             "category": tx.category, "currency": tx.currency}
            for tx in txs
        ],
    }
