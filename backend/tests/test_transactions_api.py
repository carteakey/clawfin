"""Tests for ledger transaction mutation APIs."""
from datetime import date

from backend.db.models import Account, AccountType, DataSource, Transaction


def _manual_account(db):
    account = Account(
        institution="Manual",
        name="Cash",
        account_type=AccountType.CHEQUING,
        currency="CAD",
        source=DataSource.MANUAL,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def test_create_edit_delete_manual_transaction(client, db, monkeypatch):
    from backend.config import settings

    monkeypatch.setattr(settings, "PASSWORD", "")
    account = _manual_account(db)

    created = client.post("/api/transactions", json={
        "date": "2026-04-28",
        "amount": -12.34,
        "merchant": "Corner Store",
        "account_id": account.id,
        "category": "Groceries",
    })
    assert created.status_code == 200
    tx = created.json()["transaction"]
    assert tx["source"] == "manual"

    updated = client.patch(f"/api/transactions/{tx['id']}", json={"amount": -10.0, "merchant": "Corner Market"})
    assert updated.status_code == 200

    listed = client.get("/api/transactions?days=3650")
    assert listed.json()["transactions"][0]["merchant"] == "Corner Market"

    deleted = client.delete(f"/api/transactions/{tx['id']}")
    assert deleted.status_code == 200
    assert db.query(Transaction).count() == 0


def test_filtered_export_and_bulk_category(client, db, monkeypatch):
    from backend.config import settings

    monkeypatch.setattr(settings, "PASSWORD", "")
    account = _manual_account(db)
    for i, amount in enumerate([-5, -25]):
        tx_hash = Transaction.compute_hash(date(2026, 4, 28), amount, f"Shop {i}", account.id)
        db.add(Transaction(
            date=date(2026, 4, 28),
            amount=amount,
            merchant=f"Shop {i}",
            category="Other",
            account_id=account.id,
            source=DataSource.MANUAL,
            currency="CAD",
            hash=tx_hash,
        ))
    db.commit()

    listed = client.get("/api/transactions?days=3650&amount_max=-10")
    assert listed.status_code == 200
    ids = [row["id"] for row in listed.json()["transactions"]]
    assert len(ids) == 1

    bulk = client.post("/api/transactions/bulk", json={"ids": ids, "category": "Dining"})
    assert bulk.status_code == 200
    assert bulk.json()["count"] == 1

    exported = client.get("/api/transactions/export.csv?days=3650&category=Dining")
    assert exported.status_code == 200
    assert "Shop 1" in exported.text
