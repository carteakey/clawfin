"""Tests for the internal transfer detector."""
import pytest
from backend.ingestion.transfer_detector import detect_internal_transfers


def _tx(amount, date_str, account_id=None, category="Other"):
    return {"amount": amount, "date": date_str, "account_id": account_id, "category": category}


def test_basic_pair_same_batch():
    txs = [
        _tx(-500.00, "2025-01-15", account_id=1),
        _tx(500.00, "2025-01-15", account_id=2),
        _tx(-80.00, "2025-01-16", account_id=1),  # real expense, no match
    ]
    marked = detect_internal_transfers(txs)
    assert marked == 2
    assert txs[0]["category"] == "Transfer"
    assert txs[1]["category"] == "Transfer"
    assert txs[2]["category"] == "Other"  # untouched


def test_date_tolerance_2_days():
    txs = [
        _tx(-200.00, "2025-02-01", account_id=1),
        _tx(200.00, "2025-02-03", account_id=2),  # 2-day lag (SimpleFIN posting delay)
    ]
    marked = detect_internal_transfers(txs)
    assert marked == 2


def test_date_out_of_tolerance():
    txs = [
        _tx(-200.00, "2025-02-01", account_id=1),
        _tx(200.00, "2025-02-04", account_id=2),  # 3 days — too far
    ]
    marked = detect_internal_transfers(txs)
    assert marked == 0


def test_same_account_not_paired():
    """Debit + credit on the same account is a correction, not a transfer."""
    txs = [
        _tx(-300.00, "2025-03-10", account_id=5),
        _tx(300.00, "2025-03-10", account_id=5),
    ]
    marked = detect_internal_transfers(txs)
    assert marked == 0


def test_no_false_positive_different_amounts():
    txs = [
        _tx(-100.00, "2025-04-01", account_id=1),
        _tx(99.50, "2025-04-01", account_id=2),  # different amount
    ]
    marked = detect_internal_transfers(txs)
    assert marked == 0


def test_match_against_existing():
    """New debit matched against an already-committed credit."""
    new_txs = [_tx(-750.00, "2025-05-02", account_id=1)]
    existing = [_tx(750.00, "2025-05-01", account_id=2, category="Other")]
    marked = detect_internal_transfers(new_txs, existing_txs=existing)
    assert marked == 1
    assert new_txs[0]["category"] == "Transfer"


def test_already_transfer_skipped():
    """Don't double-mark."""
    txs = [
        _tx(-100.00, "2025-06-01", account_id=1, category="Transfer"),
        _tx(100.00, "2025-06-01", account_id=2),
    ]
    marked = detect_internal_transfers(txs)
    assert marked == 0  # first is already Transfer, second has no valid counterpart
