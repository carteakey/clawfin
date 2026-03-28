"""CIBC CSV normalizer.

CIBC CSVs typically have columns:
Transaction Date, Posting Date, Description, Debit, Credit
Date format: YYYY-MM-DD
Debits and credits in separate columns.
"""
from datetime import datetime


def normalize(header_row: list[str], rows: list[list[str]]) -> list[dict]:
    headers = [h.strip().lower() for h in header_row]
    transactions = []

    date_idx = _find_col(headers, ["transaction date", "date"])
    desc_idx = _find_col(headers, ["description"])
    debit_idx = _find_col(headers, ["debit", "withdrawal"])
    credit_idx = _find_col(headers, ["credit", "deposit"])

    for row in rows:
        if not row or len(row) < 3:
            continue

        raw_date = row[date_idx].strip() if date_idx is not None else ""
        tx_date = _parse_date(raw_date)
        if not tx_date:
            continue

        amount = 0.0
        if debit_idx is not None and debit_idx < len(row) and row[debit_idx].strip():
            amount = -abs(_parse_amount(row[debit_idx]))
        elif credit_idx is not None and credit_idx < len(row) and row[credit_idx].strip():
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
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d", "%d/%m/%Y"):
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
