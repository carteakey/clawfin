"""RBC CSV normalizer.

RBC CSVs typically have columns:
Account Type, Account Number, Transaction Date, Cheque Number, Description 1, Description 2, CAD$, USD$
Date format: YYYY/MM/DD or MM/DD/YYYY
Amounts: negative for debits, positive for credits in CAD$ column.
"""
from datetime import datetime


def normalize(header_row: list[str], rows: list[list[str]]) -> list[dict]:
    headers = [h.strip().lower() for h in header_row]
    transactions = []

    date_idx = _find_col(headers, ["transaction date"])
    desc1_idx = _find_col(headers, ["description 1"])
    desc2_idx = _find_col(headers, ["description 2"])
    cad_idx = _find_col(headers, ["cad$", "cad"])
    usd_idx = _find_col(headers, ["usd$", "usd"])

    for row in rows:
        if len(row) <= max(filter(None, [date_idx, desc1_idx, cad_idx]), default=0):
            continue

        raw_date = row[date_idx].strip() if date_idx is not None else ""
        tx_date = _parse_date(raw_date)
        if not tx_date:
            continue

        # Use CAD amount; fall back to USD
        amount = 0.0
        currency = "CAD"
        if cad_idx is not None and row[cad_idx].strip():
            amount = _parse_amount(row[cad_idx])
        elif usd_idx is not None and row[usd_idx].strip():
            amount = _parse_amount(row[usd_idx])
            currency = "USD"
        else:
            continue

        desc1 = row[desc1_idx].strip() if desc1_idx is not None else ""
        desc2 = row[desc2_idx].strip() if desc2_idx is not None else ""
        merchant = f"{desc1} {desc2}".strip()
        if not merchant:
            continue

        transactions.append({
            "date": tx_date.date().isoformat(),
            "amount": amount,
            "merchant": merchant,
            "currency": currency,
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
    for fmt in ("%Y/%m/%d", "%m/%d/%Y", "%Y-%m-%d", "%d/%m/%Y"):
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
