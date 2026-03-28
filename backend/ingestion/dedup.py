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
    new = []
    skipped = 0

    for tx in transactions:
        tx_date = date.fromisoformat(tx["date"])
        merchant = tx.get("merchant", "")
        amount = tx.get("amount", 0.0)
        acct_id = tx.get("account_id", account_id)

        # Try sequence 0, 1, 2... until we find an unused hash
        sequence = 0
        while True:
            h = Transaction.compute_hash(tx_date, amount, merchant, acct_id, sequence)

            existing = db.query(Transaction.id).filter(Transaction.hash == h).first()
            if existing is None:
                # This hash is free — it's either a genuinely new tx,
                # or a duplicate we haven't seen at this sequence yet
                tx["hash"] = h
                tx["sequence"] = sequence
                tx["account_id"] = acct_id
                new.append(tx)
                break
            else:
                # Hash exists. Is this the same tx (duplicate import) or a different one?
                # Check if there's a matching tx at the next sequence
                sequence += 1
                if sequence > 50:
                    # Safety valve: more than 50 identical txs in one day is unlikely
                    skipped += 1
                    break

    return new, skipped
