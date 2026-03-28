"""TD Bank CSV normalizer.

TD CSVs typically have columns:
Date, Transaction Description, Debit, Credit, Balance
Date format: MM/DD/YYYY
Debits are positive numbers, credits are positive numbers in a separate column.
"""
from datetime import datetime


def normalize(header_row: list[str], rows: list[list[str]]) -> list[dict]:
    headers = [h.strip().lower() for h in header_row]
    transactions = []

    # Find column indices
    date_idx = _find_col(headers, ["date"])
    desc_idx = _find_col(headers, ["transaction description", "description"])
    debit_idx = _find_col(headers, ["debit", "withdrawals"])
    credit_idx = _find_col(headers, ["credit", "deposits"])

    for row in rows:
        if len(row) <= max(date_idx, desc_idx):
            continue

        # Parse date (TD uses MM/DD/YYYY)
        raw_date = row[date_idx].strip()
        tx_date = _parse_date(raw_date)
        if not tx_date:
            continue

        # Parse amount (debits are negative, credits positive)
        amount = 0.0
        if debit_idx is not None and row[debit_idx].strip():
            amount = -abs(_parse_amount(row[debit_idx]))
        elif credit_idx is not None and row[credit_idx].strip():
            amount = abs(_parse_amount(row[credit_idx]))
        else:
            continue

        merchant = row[desc_idx].strip() if desc_idx is not None else ""
        if not merchant:
            continue

        transactions.append({
            "date": tx_date.date().isoformat(),
            "amount": amount,
            "merchant": merchant,
            "currency": "CAD",
            "description": merchant,
        })

    return transactions


def _find_col(headers: list[str], candidates: list[str]) -> int | None:
    for c in candidates:
        for i, h in enumerate(headers):
            if c in h:
                return i
    return None


def _parse_date(s: str) -> datetime | None:
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%d/%m/%Y", "%m-%d-%Y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _parse_amount(s: str) -> float:
    cleaned = s.replace("$", "").replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return 0.0
