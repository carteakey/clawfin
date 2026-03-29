import io
from backend.ingestion.parser import parse_csv

def test_auto_detect_td_csv():
    """Ensure TD Canada Trust CSVs are detected and parsed correctly."""
    csv_content = (
        "Date,Transaction Description,Debit,Credit,Balance\n"
        "05/26/2025,UBER EATS,12.50,,1500.00\n"
        "05/27/2025,PAYROLL DEPOSIT,,2000.00,3500.00\n"
    )
    result = parse_csv(csv_content)
    
    assert result["error"] is None
    assert result["bank"] == "td"
    assert len(result["transactions"]) == 2
    
    tx1 = result["transactions"][0]
    assert tx1["date"] == "2025-05-26"
    assert tx1["merchant"] == "UBER EATS"
    assert tx1["amount"] == -12.50
    assert tx1["currency"] == "CAD"
    
    tx2 = result["transactions"][1]
    assert tx2["date"] == "2025-05-27"
    assert tx2["merchant"] == "PAYROLL DEPOSIT"
    assert tx2["amount"] == 2000.00

def test_auto_detect_rbc_csv():
    """Ensure RBC Royal Bank CSVs are detected and parsed correctly."""
    csv_content = (
        '"Account Type","Account Number","Transaction Date","Cheque Number","Description 1","Description 2","CAD$","USD$"\n'
        '"Chequing","123-456","5/26/2025","","STARBUCKS STORE 12345","","-4.50",""\n'
        '"Chequing","123-456","5/27/2025","","E-TRANSFER RECV","","150.00",""\n'
    )
    result = parse_csv(csv_content)
    
    assert result["error"] is None
    assert result["bank"] == "rbc"
    assert len(result["transactions"]) == 2
    
    tx1 = result["transactions"][0]
    assert tx1["date"] == "2025-05-26"
    assert tx1["merchant"] == "STARBUCKS STORE 12345"
    assert tx1["amount"] == -4.50
    
    tx2 = result["transactions"][1]
    assert tx2["amount"] == 150.00

def test_auto_detect_scotiabank_csv():
    """Ensure Scotiabank CSVs are detected and parsed correctly."""
    csv_content = (
        "Date,Amount,Description\n"
        "05/26/2025,-12.99,NETFLIX.COM\n"
    )
    result = parse_csv(csv_content)
    
    assert result["error"] is None
    assert result["bank"] == "scotiabank"
    assert len(result["transactions"]) == 1
    assert result["transactions"][0]["amount"] == -12.99
    assert result["transactions"][0]["merchant"] == "NETFLIX.COM"

def test_auto_detect_bmo_csv():
    """Ensure BMO CSVs are detected and parsed correctly."""
    csv_content = (
        "First Bank Card,Transaction Type,Date Posted,Transaction Amount,Description\n"
        "'500123456789',DEBIT,20250526,-55.00,AMAZON.CA\n"
    )
    result = parse_csv(csv_content)
    
    assert result["error"] is None
    assert result["bank"] == "bmo"
    assert len(result["transactions"]) == 1
    assert result["transactions"][0]["date"] == "2025-05-26"
    assert result["transactions"][0]["amount"] == -55.00
    assert result["transactions"][0]["merchant"] == "AMAZON.CA"

def test_auto_detect_cibc_csv():
    """Ensure CIBC CSVs are detected and parsed correctly."""
    csv_content = (
        "Transaction Date,Posting Date,Description,Debit,Credit\n"
        "2025-05-26,2025-05-26,SHOPPERS DRUG MART,50.00,\n"
        "2025-05-27,2025-05-27,PAYMENT THANK YOU,,1000.00\n"
    )
    result = parse_csv(csv_content)
    
    assert result["error"] is None
    assert result["bank"] == "cibc"
    assert len(result["transactions"]) == 2
    assert result["transactions"][0]["amount"] == -50.00  # Debits are positive in col 3, but normalized to negative
    assert result["transactions"][1]["amount"] == 1000.00 # Credits are positive in col 4
