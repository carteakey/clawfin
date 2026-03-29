import io
import csv
from datetime import date
from backend.ingestion.wealthsimple import parse_holdings, parse_activity

def _csv_to_rows(content: str):
    reader = csv.reader(io.StringIO(content))
    rows = list(reader)
    return rows[0], rows[1:]

def test_parse_wealthsimple_holdings_21_col():
    """Ensure the 21-column Wealthsimple holdings CSV is parsed correctly."""
    csv_content = (
        "Account Name,Account Type,Exchange,Security Type,Ticker,Security Name,Quantity,Market Price,Market Value,Book Value,Market Value (CAD),Book Value (CAD),Gain/Loss (CAD),Gain/Loss %,Asset Class,Sector,Country,Currency,In-house Fund,Maturity Date,Yield\n"
        "Non-registered,Cash,TSX,ETF,XEQT,iShares Core Equity Portfolio,150.5,35.00,5267.50,5000.00,5267.50,5000.00,267.50,5.35,Equity,Global,Global,CAD,No,,\n"
        "TFSA,TFSA,NASDAQ,Stock,AAPL,Apple Inc.,10.0,200.00,2000.00,1800.00,2740.00,2466.00,274.00,11.11,Equity,Technology,US,USD,No,,\n"
        '"As of 2025-05-26 10:00 GMT-04:00"\n'
    )
    headers, rows = _csv_to_rows(csv_content)
    holdings = parse_holdings(headers, rows)
    
    assert len(holdings) == 2
    
    h1 = holdings[0]
    assert h1["asset_name"] == "iShares Core Equity Portfolio"
    assert h1["ticker"] == "XEQT"
    assert h1["quantity"] == 150.5
    assert h1["book_value"] == 5000.00
    assert h1["market_value"] == 5267.50
    assert h1["currency"] == "CAD"
    assert h1["as_of_date"] == "2025-05-26"
    assert h1["account_type_hint"] == "Cash"

    h2 = holdings[1]
    assert h2["asset_name"] == "Apple Inc."
    assert h2["ticker"] == "AAPL"
    assert h2["quantity"] == 10.0
    assert h2["book_value"] == 2466.00   # Book value (CAD)
    assert h2["market_value"] == 2740.00 # Market value (CAD)
    assert h2["currency"] == "USD"
    assert h2["as_of_date"] == "2025-05-26"
    assert h2["account_type_hint"] == "TFSA"

def test_parse_wealthsimple_activity():
    """Ensure Wealthsimple activity CSV is parsed correctly."""
    csv_content = (
        "Date,Account,Type,Symbol,Description,Quantity,Price,Amount,Currency\n"
        "2025-05-26,TFSA,Buy,XEQT,iShares Core,10.0,35.00,350.00,CAD\n"
        "2025-05-27,Cash,Deposit,,Fund Transfer,,,-1000.00,CAD\n"
    )
    headers, rows = _csv_to_rows(csv_content)
    transactions = parse_activity(headers, rows)
    
    assert len(transactions) == 2
    
    t1 = transactions[0]
    assert t1["date"] == "2025-05-26"
    assert t1["merchant"] == "Buy XEQT iShares Core"
    assert t1["amount"] == 350.00
    assert t1["currency"] == "CAD"
    assert t1["source"] == "wealthsimple"
