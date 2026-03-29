"""
Wealthsimple CSV parser — holdings + activity.

Wealthsimple exports two types of CSVs:

1. Holdings (portfolio snapshot):
   Date, Account, Symbol, Name, Quantity, Price, Book Value, Market Value, Currency

2. Activity (transaction history):
   Date, Type, Description, Symbol, Quantity, Price, Amount, Currency, Account
"""
from datetime import datetime


def parse_holdings(header_row: list[str], rows: list[list[str]]) -> list[dict]:
    """Parse Wealthsimple holdings export.

    Real format columns:
    Account Name, Account Type, Account Classification, Account Number, Symbol, Exchange, MIC,
    Name, Security Type, Quantity, Position Direction, Market Price, Market Price Currency,
    Book Value (CAD), Book Value Currency (CAD), Book Value (Market), Book Value Currency (Market),
    Market Value, Market Value Currency, Market Unrealized Returns, Market Unrealized Returns Currency
    """
    headers = [h.strip().lower() for h in header_row]
    holdings = []

    # Map columns
    acct_name_idx = _find_col(headers, ["account name"])
    acct_type_idx = _find_col(headers, ["account type"])
    symbol_idx = _find_col(headers, ["symbol", "ticker"])
    name_idx = _find_col(headers, ["security name", "name"])
    security_type_idx = _find_col(headers, ["security type"])
    qty_idx = _find_col(headers, ["quantity"])
    price_idx = _find_col(headers, ["market price"])
    price_currency_idx = _find_col(headers, ["market price currency"])
    book_cad_idx = _find_col(headers, ["book value (cad)"])
    book_market_idx = _find_col(headers, ["book value (market)"])
    book_market_currency_idx = _find_col(headers, ["book value currency (market)"])
    market_val_idx = _find_col(headers, ["market value (cad)", "market value"])
    market_val_currency_idx = _find_col(headers, ["market value currency (cad)", "market value currency", "currency"])
    unrealized_idx = _find_col(headers, ["market unrealized returns"])
    exchange_idx = _find_col(headers, ["exchange"])

    # Check for as-of date in footer
    as_of_date = None
    for row in reversed(rows):
        if row and row[0].strip().startswith('"As of') or (row and row[0].strip().startswith('As of')):
            # Parse "As of 2025-05-26 10:50 GMT-04:00"
            text = row[0].strip().strip('"')
            parts = text.replace("As of ", "").split(" ")
            if parts:
                as_of_date = parts[0]
            break

    for row in rows:
        if not row or len(row) < 10:
            continue
        # Skip footer line
        first_cell = row[0].strip().strip('"')
        if first_cell.startswith("As of") or not first_cell:
            continue

        symbol = _safe_get(row, symbol_idx, "").strip().strip('"')
        name = _safe_get(row, name_idx, "").strip().strip('"')
        if not symbol and not name:
            continue

        # Use CAD book value (already converted by Wealthsimple)
        book_cad = _parse_float(_safe_get(row, book_cad_idx, "0"))
        market_val = _parse_float(_safe_get(row, market_val_idx, "0"))
        market_currency = _safe_get(row, market_val_currency_idx, "CAD").strip().strip('"').upper()

        holding = {
            "ticker": symbol or None,
            "asset_name": name or symbol,
            "quantity": _parse_float(_safe_get(row, qty_idx, "0")),
            "book_value": book_cad,
            "market_value": market_val,
            "currency": market_currency,
            "account_type_hint": _safe_get(row, acct_type_idx, "").strip().strip('"'),
            "account_name_hint": _safe_get(row, acct_name_idx, "").strip().strip('"'),
            "security_type": _safe_get(row, security_type_idx, "").strip().strip('"'),
            "exchange": _safe_get(row, exchange_idx, "").strip().strip('"'),
            "as_of_date": as_of_date,
            "source": "wealthsimple",
        }
        holdings.append(holding)

    return holdings


def parse_activity(header_row: list[str], rows: list[list[str]]) -> list[dict]:
    """Parse Wealthsimple activity/transaction export."""
    headers = [h.strip().lower() for h in header_row]
    transactions = []

    date_idx = _find_col(headers, ["date", "transaction date"])
    type_idx = _find_col(headers, ["type", "transaction type"])
    desc_idx = _find_col(headers, ["description"])
    symbol_idx = _find_col(headers, ["symbol", "ticker"])
    amount_idx = _find_col(headers, ["amount", "net amount"])
    currency_idx = _find_col(headers, ["currency"])
    account_idx = _find_col(headers, ["account", "account type"])

    for row in rows:
        if not row or len(row) < 4:
            continue

        raw_date = _safe_get(row, date_idx, "").strip()
        tx_date = _parse_date_str(raw_date)
        if not tx_date:
            continue

        tx_type = _safe_get(row, type_idx, "").strip()
        description = _safe_get(row, desc_idx, "").strip()
        symbol = _safe_get(row, symbol_idx, "").strip()

        merchant = " ".join(filter(None, [tx_type, symbol, description])).strip()
        if not merchant:
            continue

        amount = _parse_float(_safe_get(row, amount_idx, "0"))
        currency = _safe_get(row, currency_idx, "CAD").strip().upper()

        transactions.append({
            "date": tx_date,
            "amount": amount,
            "merchant": merchant,
            "currency": currency,
            "description": description,
            "account_type_hint": _safe_get(row, account_idx, "").strip(),
            "source": "wealthsimple",
        })

    return transactions


def detect_wealthsimple_type(header_row: list[str]) -> str | None:
    """Detect whether this is a holdings or activity export."""
    headers = [h.strip().lower() for h in header_row]
    header_str = " ".join(headers)

    if "book value" in header_str or "market value" in header_str:
        return "holdings"
    elif "type" in headers and ("amount" in headers or "net amount" in header_str):
        return "activity"
    return None


# ─── Helpers ─────────────────────────────────────────────────────────

def _find_col(headers: list[str], candidates: list[str]) -> int | None:
    for c in candidates:
        for i, h in enumerate(headers):
            if c in h:
                return i
    return None


def _safe_get(row: list[str], idx: int | None, default: str = "") -> str:
    if idx is None or idx >= len(row):
        return default
    return row[idx]


def _parse_float(s: str) -> float:
    cleaned = s.replace("$", "").replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _parse_date_str(s: str) -> str | None:
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(s.strip(), fmt).date().isoformat()
        except ValueError:
            continue
    return None
