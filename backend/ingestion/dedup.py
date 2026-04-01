"""
Dedup engine — SHA256 hash with per-day sequence counter.

Handles identical transactions on the same day (e.g., two $4.50 Tim Hortons)
by incrementing a sequence counter until a unique hash is found.
"""
from datetime import date
from sqlalchemy.orm import Session
from backend.db.models import Transaction


def dedup_transactions(
    transactions: list[dict],
    db: Session,
    account_id: int | None = None,
) -> tuple[list[dict], int]:
    """
    Deduplicate transactions against the database.

    Returns:
        (new_transactions, skipped_count)
    """
    from collections import defaultdict

    # 1. Group incoming transactions by their base fingerprint
    incoming_groups = defaultdict(list)
    for tx in transactions:
        tx_date = date.fromisoformat(tx["date"])
        merchant = tx.get("merchant", "")
        amount = tx.get("amount", 0.0)
        acct_id = tx.get("account_id", account_id)
        
        # Base signature ignores sequence
        sig = (tx_date, amount, merchant.strip().lower(), acct_id)
        incoming_groups[sig].append(tx)

    new = []
    skipped = 0

    # 2. For each group, determine how many exist in the DB
    for sig, txs in incoming_groups.items():
        tx_date, amount, merchant_lower, acct_id = sig
        n_incoming = len(txs)

        # We check hashes 0 to n_incoming - 1
        existing_count = 0
        for seq in range(n_incoming):
            h = Transaction.compute_hash(tx_date, amount, merchant_lower, acct_id, seq)
            exists = db.query(Transaction.id).filter(Transaction.hash == h).first()
            if exists:
                existing_count += 1
            else:
                # Assuming dense sequences, if seq N is missing, N+1 is missing too.
                break
        
        # If we have more incoming than existing, insert the difference
        if n_incoming > existing_count:
            # We skip 'existing_count' transactions, and insert the rest
            transactions_to_insert = txs[existing_count:]
            skipped += existing_count
            
            # Start assigning sequences from 'existing_count'
            current_seq = existing_count
            for tx in transactions_to_insert:
                tx["hash"] = Transaction.compute_hash(tx_date, amount, merchant_lower, acct_id, current_seq)
                tx["sequence"] = current_seq
                tx["account_id"] = acct_id
                new.append(tx)
                current_seq += 1
        else:
            # All incoming transactions already exist
            skipped += n_incoming

    return new, skipped
