"""Tests for scheduled transaction briefing endpoints."""
from datetime import date, datetime, timedelta

import pytest

from backend.config import settings
from backend.db.models import Account, AccountType, DataSource, Transaction


def _add_account(db):
    account = Account(
        institution="Test Bank",
        name="Chequing",
        account_type=AccountType.CHEQUING,
        currency="CAD",
        balance=1250.00,
        available_balance=1200.00,
        balance_date=datetime(2026, 4, 25, 12, 0),
        last_sync_at=datetime(2026, 4, 25, 12, 0),
        source=DataSource.SIMPLEFIN,
        external_id="acct-1",
    )
    db.add(account)
    db.flush()
    return account


def _add_tx(db, tx_date, amount, merchant, category="Other", account_id=None, pending=False, sequence=0):
    db.add(Transaction(
        date=tx_date,
        amount=amount,
        merchant=merchant,
        normalized_merchant=merchant.title(),
        category=category,
        account_id=account_id,
        source=DataSource.SIMPLEFIN,
        currency="CAD",
        hash=Transaction.compute_hash(tx_date, amount, merchant, account_id, sequence),
        sequence=sequence,
        pending=pending,
    ))


@pytest.fixture(autouse=True)
def automation_token(monkeypatch):
    monkeypatch.setattr(settings, "AUTOMATION_TOKEN", "test-token")


def test_briefing_requires_automation_token(client):
    response = client.post("/api/briefings/transactions", json={"period": "daily", "mode": "context"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing automation token"


def test_daily_context_briefing_returns_metrics(client, db):
    account = _add_account(db)
    _add_tx(db, date(2026, 4, 25), -42.50, "Loblaws", "Groceries", account.id)
    _add_tx(db, date(2026, 4, 25), -15.00, "Tim Hortons", "Dining", account.id, pending=True)
    _add_tx(db, date(2026, 4, 25), 2500.00, "Payroll", "Income", account.id)
    _add_tx(db, date(2026, 4, 24), -20.00, "Loblaws", "Groceries", account.id, sequence=1)
    db.commit()

    response = client.post(
        "/api/briefings/transactions",
        headers={"X-ClawFin-Automation-Token": "test-token"},
        json={"period": "daily", "mode": "context", "end_date": "2026-04-25"},
    )

    assert response.status_code == 200
    payload = response.json()
    context = payload["context"]
    assert payload["mode"] == "context"
    assert "summary" not in payload
    assert context["range"] == {"start": "2026-04-25", "end": "2026-04-25", "days": 1}
    assert context["totals"]["income"] == 2500.00
    assert context["totals"]["expenses"] == 57.50
    assert context["totals"]["net_cash_flow"] == 2442.50
    assert context["counts"]["transactions"] == 3
    assert context["counts"]["pending"] == 1
    assert context["top_categories"][0]["name"] == "Groceries"
    assert context["top_merchants"][0]["name"] == "Loblaws"
    assert context["account_freshness"]["reconnect_nudge"] is False


def test_weekly_context_can_include_transactions(client, db):
    account = _add_account(db)
    _add_tx(db, date(2026, 4, 20), -100.00, "Costco", "Groceries", account.id)
    _add_tx(db, date(2026, 4, 19), -30.00, "Netflix", "Subscriptions", account.id)
    db.commit()

    response = client.post(
        "/api/briefings/transactions",
        headers={"X-ClawFin-Automation-Token": "test-token"},
        json={
            "period": "weekly",
            "mode": "context",
            "end_date": "2026-04-25",
            "include_transactions": True,
        },
    )

    assert response.status_code == 200
    context = response.json()["context"]
    assert context["range"]["start"] == "2026-04-19"
    assert context["top_merchants"][0]["name"] == "Costco"
    assert context["transactions"][0]["merchant"] == "Costco"
    assert context["privacy"]["transactions_included"] is True


def test_generate_briefing_calls_ai_provider(client, db, monkeypatch):
    account = _add_account(db)
    _add_tx(db, date(2026, 4, 25), -42.50, "Loblaws", "Groceries", account.id)
    db.commit()

    async def fake_chat_completion(messages, tools=None, temperature=0.3):
        assert tools is None
        assert temperature == 0.2
        assert "Loblaws" in messages[1]["content"]
        return {"content": "Weekly status: spent CAD 42.50 on groceries.", "tool_calls": None}

    monkeypatch.setattr("backend.ai.briefings.provider.chat_completion", fake_chat_completion)

    response = client.post(
        "/api/briefings/transactions",
        headers={"X-ClawFin-Automation-Token": "test-token"},
        json={"period": "weekly", "mode": "generate", "end_date": "2026-04-25"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"] == "Weekly status: spent CAD 42.50 on groceries."


def test_chat_briefing_uses_user_safe_endpoint(client, db, monkeypatch):
    from backend.config import settings

    monkeypatch.setattr(settings, "PASSWORD", "")
    account = _add_account(db)
    _add_tx(db, date(2026, 4, 25), -42.50, "Loblaws", "Groceries", account.id)
    db.commit()

    async def fake_chat_completion(messages, tools=None, temperature=0.3):
        assert "Loblaws" in messages[1]["content"]
        return {"content": "Weekly status from chat briefing.", "tool_calls": None}

    monkeypatch.setattr("backend.ai.briefings.provider.chat_completion", fake_chat_completion)

    response = client.post(
        "/api/chat/briefing",
        json={"period": "weekly"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"] == "Weekly status from chat briefing."
    assert payload["context"]["period"] == "weekly"

