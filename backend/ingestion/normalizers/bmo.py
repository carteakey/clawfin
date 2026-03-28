"""BMO CSV normalizer.

BMO CSVs typically have columns:
First Bank Card, Transaction Type, Date Posted, Transaction Amount, Description
Date format: YYYYMMDD
Amounts: positive for debits, negative for credits (reversed from convention).
"""
from datetime import datetime


def normalize(header_row: list[str], rows: list[list[str]]) -> list[dict]:
    headers = [h.strip().lower() for h in header_row]
    transactions = []

    date_idx = _find_col(headers, ["date posted", "date"])
    amount_idx = _find_col(headers, ["transaction amount", "amount"])
    desc_idx = _find_col(headers, ["description"])

    for row in rows:
        if not row or len(row) < 3:
            continue

        raw_date = row[date_idx].strip() if date_idx is not None else ""
        tx_date = _parse_date(raw_date)
        if not tx_date:
            continue

        raw_amount = row[amount_idx].strip() if amount_idx is not None else ""
        amount = _parse_amount(raw_amount)
        if amount == 0.0:
            continue

        # BMO reverses sign convention: positive = debit, negative = credit
        amount = -amount

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
    for fmt in ("%Y%m%d", "%m/%d/%Y", "%Y-%m-%d", "%Y/%m/%d"):
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
