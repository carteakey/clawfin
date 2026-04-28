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


def test_transactions_sort_by_amount(client, db, monkeypatch):
    from backend.config import settings

    monkeypatch.setattr(settings, "PASSWORD", "")
    account = _manual_account(db)
    for i, amount in enumerate([-5, -25, 10]):
        tx_hash = Transaction.compute_hash(date(2026, 4, 28), amount, f"Sort {i}", account.id)
        db.add(Transaction(
            date=date(2026, 4, 28),
            amount=amount,
            merchant=f"Sort {i}",
            category="Other",
            account_id=account.id,
            source=DataSource.MANUAL,
            currency="CAD",
            hash=tx_hash,
        ))
    db.commit()

    asc = client.get("/api/transactions?days=3650&sort_by=amount&sort_dir=asc")
    assert asc.status_code == 200
    assert [row["amount"] for row in asc.json()["transactions"]] == [-25, -5, 10]


def test_background_recategorize_reports_progress(client, db, monkeypatch):
    from backend.config import settings
    from backend.routers import transactions as transactions_router

    class TestSessionContext:
        def __enter__(self):
            return db

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(settings, "PASSWORD", "")
    monkeypatch.setattr(transactions_router, "SessionLocal", lambda: TestSessionContext())
    transactions_router.RECATEGORIZE_JOBS.clear()
    account = _manual_account(db)
    tx_hash = Transaction.compute_hash(date(2026, 4, 28), -5, "STARBUCKS", account.id)
    db.add(Transaction(
        date=date(2026, 4, 28),
        amount=-5,
        merchant="STARBUCKS",
        category="Other",
        account_id=account.id,
        source=DataSource.MANUAL,
        currency="CAD",
        hash=tx_hash,
    ))
    db.commit()

    started = client.post("/api/transactions/recategorize?background=true")
    assert started.status_code == 200
    job_id = started.json()["id"]

    progress = client.get(f"/api/transactions/recategorize/{job_id}")
    assert progress.status_code == 200
    body = progress.json()
    assert body["status"] == "complete"
    assert body["processed"] == 1
    assert body["total"] == 1
