"""Tests for SimpleFIN account sync metadata."""
from datetime import datetime, timedelta

from backend.config import settings
from backend.db.models import Account
from backend.routers.import_data import _simplefin_stale_reason
from backend.ingestion.simplefin import SimpleFinClient


def _posted(days_ago: int) -> int:
    return int((datetime.now() - timedelta(days=days_ago)).timestamp())


def test_simplefin_sync_persists_account_metadata(client, db, monkeypatch):
    monkeypatch.setattr(settings, "SIMPLEFIN_ACCESS_URL", "https://user:pass@example.com/simplefin")

    async def fake_fetch(self, start_date=None, end_date=None):
        return {
            "accounts": [
                {
                    "id": "acct-a",
                    "name": "Chequing",
                    "org": {"name": "Test Bank"},
                    "balance": "100.00",
                    "available-balance": "90.00",
                    "balance-date": str(_posted(0)),
                    "currency": "CAD",
                    "transactions": [
                        {"id": "tx-a", "posted": _posted(1), "amount": "-12.34", "description": "LOBLAWS"},
                    ],
                }
            ]
        }

    monkeypatch.setattr(SimpleFinClient, "fetch_accounts", fake_fetch)

    response = client.post("/api/import/simplefin/sync")

    assert response.status_code == 200
    assert response.json()["accounts_synced"] == 1
    account = db.query(Account).filter(Account.external_id == "acct-a").one()
    assert account.last_sync_at is not None
    assert account.last_successful_balance_date is not None
    assert account.last_successful_transaction_date is not None
    assert account.last_sync_error is None
    assert account.simplefin_account_present is True
    assert account.stale_reason is None


def test_simplefin_sync_marks_missing_accounts_stale(client, db, monkeypatch):
    monkeypatch.setattr(settings, "SIMPLEFIN_ACCESS_URL", "https://user:pass@example.com/simplefin")

    responses = [
        {
            "accounts": [
                {
                    "id": "acct-a",
                    "name": "Chequing",
                    "org": {"name": "Test Bank"},
                    "balance": "100.00",
                    "currency": "CAD",
                    "transactions": [],
                },
                {
                    "id": "acct-b",
                    "name": "Visa",
                    "org": {"name": "Test Bank"},
                    "balance": "-25.00",
                    "currency": "CAD",
                    "transactions": [],
                },
            ]
        },
        {
            "accounts": [
                {
                    "id": "acct-a",
                    "name": "Chequing",
                    "org": {"name": "Test Bank"},
                    "balance": "100.00",
                    "currency": "CAD",
                    "transactions": [],
                }
            ]
        },
    ]

    async def fake_fetch(self, start_date=None, end_date=None):
        return responses.pop(0)

    monkeypatch.setattr(SimpleFinClient, "fetch_accounts", fake_fetch)

    first = client.post("/api/import/simplefin/sync")
    second = client.post("/api/import/simplefin/sync")

    assert first.status_code == 200
    assert second.status_code == 200
    missing = db.query(Account).filter(Account.external_id == "acct-b").one()
    assert missing.simplefin_account_present is False
    assert missing.stale_reason == "missing_from_simplefin_response"
    assert any(
        row["stale_reason"] == "missing_from_simplefin_response"
        for row in second.json()["stale_accounts"]
    )


def test_simplefin_stale_reason_uses_sync_timestamp_not_activity_date():
    account = Account(
        institution="Test Bank",
        name="Quiet Savings",
        account_type="savings",
        currency="CAD",
        balance=1000,
        source="simplefin",
        external_id="acct-quiet",
        last_sync_at=datetime(2026, 4, 25, 8, 0),
        last_successful_transaction_date=datetime(2026, 1, 1).date(),
    )

    assert _simplefin_stale_reason(account, today=datetime(2026, 4, 25).date()) is None

    account.last_sync_at = datetime(2026, 4, 21, 8, 0)
    assert _simplefin_stale_reason(account, today=datetime(2026, 4, 25).date()) == "simplefin_sync_stale"
