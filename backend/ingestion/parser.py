"""CSV ingestion orchestrator with bank auto-detection."""
import csv
import io
from backend.ingestion.normalizers import td, rbc, scotiabank, bmo, cibc


# Header signatures for auto-detection
BANK_SIGNATURES = {
    "td": {
        "headers": ["date", "transaction description", "debit", "credit", "balance"],
        "normalizer": td.normalize,
        "source": "csv_td",
    },
    "rbc": {
        "headers": ["account type", "account number", "transaction date", "cheque number", "description 1", "description 2", "cad$"],
        "normalizer": rbc.normalize,
        "source": "csv_rbc",
    },
    "scotiabank": {
        "headers": ["date", "amount", "description"],
        "normalizer": scotiabank.normalize,
        "source": "csv_scotiabank",
    },
    "bmo": {
        "headers": ["first bank card", "transaction type", "date posted", "transaction amount", "description"],
        "normalizer": bmo.normalize,
        "source": "csv_bmo",
    },
    "cibc": {
        "headers": ["transaction date", "posting date", "description", "debit", "credit"],
        "normalizer": cibc.normalize,
        "source": "csv_cibc",
    },
}


def detect_bank(header_row: list[str]) -> str | None:
    """Auto-detect bank from CSV header row."""
    normalized_headers = [h.strip().lower() for h in header_row]

    for bank_id, sig in BANK_SIGNATURES.items():
        sig_headers = sig["headers"]
        # Check if enough signature headers are present
        matches = sum(1 for h in sig_headers if h in normalized_headers)
        if matches >= len(sig_headers) * 0.7:  # 70% match threshold
            return bank_id

    return None


def parse_csv(csv_text: str, bank_hint: str | None = None) -> dict:
    """
    Parse a bank CSV and return normalized transactions.

    Returns:
        {
            "bank": str,
            "transactions": list[dict],  # normalized transaction dicts
            "row_count": int,
            "error": str | None,
        }
    """
    reader = csv.reader(io.StringIO(csv_text))

    # Read header row
    try:
        header_row = next(reader)
    except StopIteration:
        return {"bank": None, "transactions": [], "row_count": 0, "error": "Empty CSV file"}

    # Detect bank
    bank_id = bank_hint or detect_bank(header_row)
    if not bank_id:
        return {
            "bank": None,
            "transactions": [],
            "row_count": 0,
            "error": f"Could not auto-detect bank. Headers: {header_row}",
        }

    if bank_id not in BANK_SIGNATURES:
        return {"bank": bank_id, "transactions": [], "row_count": 0, "error": f"Unknown bank: {bank_id}"}

    sig = BANK_SIGNATURES[bank_id]

    # Parse all rows
    rows = list(reader)

    # Normalize using bank-specific normalizer
    transactions = sig["normalizer"](header_row, rows)

    # Tag source
    for tx in transactions:
        tx["source"] = sig["source"]

    return {
        "bank": bank_id,
        "transactions": transactions,
        "row_count": len(rows),
        "error": None,
    }
