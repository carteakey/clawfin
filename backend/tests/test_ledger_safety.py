"""Focused regression coverage for the promoted ledger safety backlog."""

from datetime import date

from backend.config import DEFAULT_SECRET_KEY, secret_key_is_default, settings, warn_if_default_secret
from backend.db.models import Account, AccountType, DataSource, Transaction
from backend.security import decrypt_value, encrypt_value


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


def _manual_tx(db, account, amount=-100.0, merchant="Grocery Run"):
    tx = Transaction(
        date=date(2026, 4, 28),
        amount=amount,
        merchant=merchant,
        normalized_merchant=merchant,
        category="Other",
        account_id=account.id,
        source=DataSource.MANUAL,
        currency="CAD",
        hash=Transaction.compute_hash(date(2026, 4, 28), amount, merchant, account.id),
        category_reason="manual",
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


def test_sensitive_values_round_trip_without_plaintext():
    value = "https://user:secret@example.simplefin.org"
    encrypted = encrypt_value(value)
    assert encrypted.startswith("enc:")
    assert value not in encrypted
    assert decrypt_value(encrypted) == value


def test_default_secret_detection_and_safe_warning(monkeypatch, caplog):
    assert secret_key_is_default(DEFAULT_SECRET_KEY)
    assert not secret_key_is_default("a-real-random-key")
    monkeypatch.setattr(settings, "SECRET_KEY", DEFAULT_SECRET_KEY)
    assert warn_if_default_secret() is True
    assert "development default" in caplog.text


def test_split_transaction_reconciles_and_hides_parent_from_ledger(client, db, monkeypatch):
    monkeypatch.setattr(settings, "PASSWORD", "")
    account = _manual_account(db)
    tx = _manual_tx(db, account)

    response = client.post(
        f"/api/transactions/{tx.id}/split",
        json={"allocations": [{"category": "Groceries", "amount": -60}, {"category": "Dining", "amount": -40}]},
    )
    assert response.status_code == 200
    assert len(response.json()["transactions"]) == 2
    assert db.query(Transaction).filter(Transaction.parent_transaction_id == tx.id).count() == 2
    assert client.get("/api/transactions?days=3650").json()["total"] == 2

    invalid = client.post(
        f"/api/transactions/{tx.id}/split",
        json={"allocations": [{"category": "Groceries", "amount": -1}, {"category": "Dining", "amount": -1}]},
    )
    assert invalid.status_code == 400

    children = db.query(Transaction).filter(Transaction.parent_transaction_id == tx.id).all()
    assert client.delete(f"/api/transactions/{children[0].id}").status_code == 400
    assert client.post(f"/api/transactions/{tx.id}/unsplit").json()["deleted_allocations"] == 2
    assert db.query(Transaction).filter(Transaction.id == tx.id).count() == 1

    split_again = client.post(
        f"/api/transactions/{tx.id}/split",
        json={"allocations": [{"category": "Groceries", "amount": -60}, {"category": "Dining", "amount": -40}]},
    )
    assert split_again.status_code == 200
    assert client.delete(f"/api/transactions/{tx.id}").json()["count"] == 3
    assert db.query(Transaction).filter(Transaction.id == tx.id).count() == 0


def test_bulk_transfer_and_other_actions(client, db, monkeypatch):
    monkeypatch.setattr(settings, "PASSWORD", "")
    account = _manual_account(db)
    first = _manual_tx(db, account, merchant="Move")
    second = _manual_tx(db, account, merchant="Misc")
    marked = client.post("/api/transactions/bulk", json={"ids": [first.id], "mark_transfer": True})
    assert marked.status_code == 200
    assert db.get(Transaction, first.id).category == "Transfer"
    marked_other = client.post("/api/transactions/bulk", json={"ids": [second.id], "mark_other": True})
    assert marked_other.status_code == 200
    assert db.get(Transaction, second.id).category == "Other"


def test_rule_preview_suggestions_and_merchant_merge(client, db, monkeypatch):
    monkeypatch.setattr(settings, "PASSWORD", "")
    account = _manual_account(db)
    tx = _manual_tx(db, account, merchant="Old Cafe")
    created = client.post("/api/settings/rules", json={"pattern": "old cafe", "category": "Dining"})
    assert created.status_code == 200
    preview = client.post("/api/settings/rules/preview", json={"pattern": "cafe"})
    assert preview.status_code == 200
    assert preview.json()["affected_count"] == 1
    suggestions = client.get("/api/transactions/category-suggestions?merchant=cafe")
    assert suggestions.status_code == 200
    assert suggestions.json()["suggestions"][0]["category"] == "Dining"
    merged = client.post("/api/settings/merchants/merge", json={"source": "Old Cafe", "target": "Cafe Central"})
    assert merged.status_code == 200
    assert db.get(Transaction, tx.id).normalized_merchant == "Cafe Central"


def test_briefing_schedule_round_trip_and_validation(client, monkeypatch):
    monkeypatch.setattr(settings, "PASSWORD", "")
    initial = client.get("/api/settings/briefing-schedule")
    assert initial.status_code == 200
    saved = client.put("/api/settings/briefing-schedule", json={
        "enabled": True,
        "cadence": "weekly",
        "weekday": 4,
        "time": "07:30",
        "timezone": "America/Toronto",
    })
    assert saved.status_code == 200
    assert saved.json()["cadence"] == "weekly"
    assert saved.json()["next_run"]
    invalid = client.put("/api/settings/briefing-schedule", json={"timezone": "Not/AZone"})
    assert invalid.status_code == 422


def test_backup_endpoint_returns_safe_errors(client, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "PASSWORD", "")
    monkeypatch.setattr(settings, "DB_PATH", str(tmp_path / "missing.db"))
    missing = client.get("/api/settings/export")
    assert missing.status_code == 404
    corrupt = tmp_path / "corrupt.db"
    corrupt.write_text("not sqlite")
    monkeypatch.setattr(settings, "DB_PATH", str(corrupt))
    unavailable = client.get("/api/settings/export")
    assert unavailable.status_code == 503


def test_csv_preview_does_not_write(client, db, monkeypatch):
    monkeypatch.setattr(settings, "PASSWORD", "")
    response = client.post(
        "/api/import/csv/preview",
        files={"file": ("bank.csv", "Date,Description,Amount\n2026-04-28,Test Merchant,-5.00\n", "text/csv")},
    )
    assert response.status_code == 200
    assert response.json()["writes_database"] is False
    assert db.query(Transaction).count() == 0
