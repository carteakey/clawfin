"""Tests for dashboard budget-account scoping."""
from datetime import date

from backend.db.models import Account, AccountType, DataSource, Transaction


def _account(db, name, account_type):
    account = Account(
        institution="Test Bank",
        name=name,
        account_type=account_type,
        currency="CAD",
        balance=100,
        source=DataSource.SIMPLEFIN,
        external_id=name,
    )
    db.add(account)
    db.flush()
    return account


def _tx(db, account, amount, merchant, sequence=0):
    tx_date = date.today()
    db.add(Transaction(
        date=tx_date,
        amount=amount,
        merchant=merchant,
        category="Other",
        account_id=account.id,
        source=DataSource.SIMPLEFIN,
        currency="CAD",
        hash=Transaction.compute_hash(tx_date, amount, merchant, account.id, sequence),
        sequence=sequence,
    ))


def test_dashboard_spending_excludes_investment_accounts(client, db, monkeypatch):
    from backend.config import settings

    monkeypatch.setattr(settings, "PASSWORD", "")
    chequing = _account(db, "Chequing", AccountType.CHEQUING)
    tfsa = _account(db, "TFSA", AccountType.TFSA)
    _tx(db, chequing, -25.00, "Loblaws")
    _tx(db, tfsa, -500.00, "Buy XEQT")
    db.commit()

    response = client.get("/api/dashboard?days=30")

    assert response.status_code == 200
    payload = response.json()
    assert payload["kpis"]["expenses"] == 25.00
    assert payload["transaction_count"] == 1
