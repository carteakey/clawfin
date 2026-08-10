"""Stable response-shape assertions for ledger filters and exports."""

from datetime import date

from backend.config import settings
from backend.db.models import Account, AccountType, DataSource, Transaction


def test_ledger_shape_includes_filter_metadata(client, db, monkeypatch):
    monkeypatch.setattr(settings, "PASSWORD", "")
    account = Account(
        institution="Manual",
        name="Cash",
        account_type=AccountType.CHEQUING,
        currency="CAD",
        source=DataSource.MANUAL,
    )
    db.add(account)
    db.flush()
    tx = Transaction(
        date=date(2026, 4, 28),
        amount=-4.5,
        merchant="Coffee",
        category="Dining",
        account_id=account.id,
        source=DataSource.MANUAL,
        currency="CAD",
        hash=Transaction.compute_hash(date(2026, 4, 28), -4.5, "Coffee", account.id),
        category_reason="manual",
    )
    db.add(tx)
    db.commit()
    response = client.get("/api/transactions?days=3650&category=Dining&source=manual&limit=10&offset=0")
    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"total", "transactions"}
    assert payload["total"] == 1
    assert {"id", "date", "amount", "merchant", "category", "category_reason", "pending", "source"}.issubset(payload["transactions"][0])


def test_csv_export_shape_contains_diagnostics_and_split_columns(client, monkeypatch):
    monkeypatch.setattr(settings, "PASSWORD", "")
    response = client.get("/api/transactions/export.csv?days=3650")
    assert response.status_code == 200
    header = response.text.splitlines()[0].split(",")
    assert "category_reason" in header
    assert "parent_transaction_id" in header
    assert "split_group_id" in header
