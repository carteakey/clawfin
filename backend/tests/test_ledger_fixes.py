"""Regression tests for holdings history, agent transfer exclusion and categorizer patterns."""
import json
import re
from datetime import date

from backend.ai.tools import execute_tool
from backend.db.models import Account, AccountType, DataSource, Holding, Transaction
from backend.ingestion.categorizer import DEFAULT_RULES

HEADER = (
    "Account Name,Account Type,Exchange,Security Type,Ticker,Security Name,Quantity,Market Price,"
    "Market Value,Book Value,Market Value (CAD),Book Value (CAD),Gain/Loss (CAD),Gain/Loss %,"
    "Asset Class,Sector,Country,Currency,In-house Fund,Maturity Date,Yield\n"
)


def _holdings_csv(as_of: str, market_value: float) -> bytes:
    return (
        HEADER
        + f"TFSA,TFSA,TSX,ETF,XEQT,iShares Core Equity Portfolio,100,35.00,{market_value},3000.00,"
        f"{market_value},3000.00,0,0,Equity,Global,Global,CAD,No,,\n"
        + f'"As of {as_of} 10:00 GMT-04:00"\n'
    ).encode()


def _upload(client, content: bytes):
    return client.post(
        "/api/import/wealthsimple",
        files={"file": ("holdings.csv", content, "text/csv")},
    )


def test_holdings_import_keeps_previous_snapshots(client, db, monkeypatch):
    from backend.config import settings

    monkeypatch.setattr(settings, "PASSWORD", "")
    assert _upload(client, _holdings_csv("2026-10-01", 3500.00)).status_code == 200
    assert _upload(client, _holdings_csv("2026-11-01", 3700.00)).status_code == 200

    dates = sorted(h.as_of_date for h in db.query(Holding).all())
    assert dates == [date(2026, 10, 1), date(2026, 11, 1)]

    # Re-importing the same date replaces that snapshot rather than duplicating it.
    assert _upload(client, _holdings_csv("2026-11-01", 3800.00)).status_code == 200
    assert db.query(Holding).count() == 2


def test_holdings_totals_use_latest_snapshot_only(client, db, monkeypatch):
    from backend.config import settings

    monkeypatch.setattr(settings, "PASSWORD", "")
    _upload(client, _holdings_csv("2026-10-01", 3500.00))
    _upload(client, _holdings_csv("2026-11-01", 3700.00))

    dashboard = client.get("/api/dashboard?days=30").json()
    assert dashboard["kpis"]["holdings_market_value"] == 3700.00

    tool = json.loads(execute_tool("get_holdings", {}, db))
    assert tool["total_market"] == 3700.00

    listing = client.get("/api/holdings").json()
    assert listing["total_market_value"] == 3700.00


def test_agent_spending_excludes_transfers(db):
    account = Account(
        institution="Test Bank", name="Chequing", account_type=AccountType.CHEQUING,
        currency="CAD", balance=0, source=DataSource.SIMPLEFIN, external_id="chq",
    )
    db.add(account)
    db.flush()
    today = date.today()
    for seq, (amount, merchant, category) in enumerate([
        (-40.00, "Loblaws", "Groceries"),
        (-1500.00, "Credit card payment", "Transfer"),
    ]):
        db.add(Transaction(
            date=today, amount=amount, merchant=merchant, category=category,
            account_id=account.id, source=DataSource.SIMPLEFIN, currency="CAD",
            hash=Transaction.compute_hash(today, amount, merchant, account.id, seq), sequence=seq,
        ))
    db.commit()

    result = json.loads(execute_tool("query_spending", {"days": 30}, db))
    assert result["total"] == 40.00
    assert "Transfer" not in result["breakdown"]

    # Asking for transfers explicitly still works.
    transfers = json.loads(execute_tool("query_spending", {"days": 30, "category": "Transfer"}, db))
    assert transfers["total"] == 1500.00


def _rule_category(merchant: str) -> str | None:
    for pattern, category in DEFAULT_RULES:
        if re.search(pattern, merchant, re.IGNORECASE):
            return category
    return None


def test_short_patterns_need_word_boundaries():
    assert _rule_category("SINGAPORE AIRLINES") != "Shopping"
    assert _rule_category("PREVENTION SERVICES") != "Entertainment"
    assert _rule_category("ALLENS PUB") != "Health"
    assert _rule_category("GAP CANADA 1234") == "Shopping"
    assert _rule_category("TICKETMASTER EVENT") == "Entertainment"
    assert _rule_category("CLEARLY CONTACT LENSES") == "Health"
