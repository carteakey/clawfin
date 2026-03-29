"""Test the deduplication hashing logic."""
from datetime import date
from backend.db.models import Transaction

def test_transaction_hash_stability():
    """Ensure the hash function generates stable outputs for the same inputs."""
    tx_date = date(2025, 5, 26)
    amount = -12.50
    merchant = "Uber Eats"
    
    hash1 = Transaction.compute_hash(tx_date, amount, merchant)
    hash2 = Transaction.compute_hash(tx_date, amount, merchant)
    
    assert hash1 == hash2
    assert type(hash1) is str
    assert len(hash1) == 64  # SHA256 length

def test_identical_same_day_transactions_differ_by_sequence():
    """Ensure sequence counter differentiates identical same-day purchases."""
    tx_date = date(2025, 5, 26)
    amount = -4.50
    merchant = "Tim Hortons"
    account_id = 1
    
    # Coffee 1 at 8 AM
    hash_seq_0 = Transaction.compute_hash(tx_date, amount, merchant, account_id, sequence=0)
    
    # Coffee 2 at 2 PM (identical amount, merchant, date, and account)
    hash_seq_1 = Transaction.compute_hash(tx_date, amount, merchant, account_id, sequence=1)
    
    assert hash_seq_0 != hash_seq_1

def test_hash_is_case_insensitive_for_merchants():
    """Ensure casing in the CSV doesn't cause false duplicate failures."""
    tx_date = date(2025, 5, 26)
    amount = -100.00
    
    hash_upper = Transaction.compute_hash(tx_date, amount, "WALMART SUPERCENTER")
    hash_lower = Transaction.compute_hash(tx_date, amount, "walmart supercenter")
    hash_mixed = Transaction.compute_hash(tx_date, amount, "Walmart SuperCenter ")
    
    assert hash_upper == hash_lower
    assert hash_lower == hash_mixed
