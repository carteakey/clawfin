"""Import API router — CSV upload, SimpleFin, Wealthsimple."""
import csv
import io
from datetime import date
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from backend.db.database import get_db
from backend.db.models import Transaction, Holding, Account, AccountType, DataSource
from backend.ingestion.parser import parse_csv
from backend.ingestion.wealthsimple import parse_holdings, parse_activity, detect_wealthsimple_type
from backend.ingestion.categorizer import categorize_transactions
from backend.ingestion.dedup import dedup_transactions
from backend.ingestion.simplefin import SimpleFinClient
from backend.config import settings

router = APIRouter()


# ─── CSV Import ──────────────────────────────────────────────────────

@router.post("/csv")
async def import_csv(
    file: UploadFile = File(...),
    bank_hint: str = Form(None),
    account_id: int = Form(None),
    db: Session = Depends(get_db),
):
    content = await file.read()
    csv_text = content.decode("utf-8-sig")  # Handle BOM

    result = parse_csv(csv_text, bank_hint=bank_hint)
    if result["error"]:
        raise HTTPException(status_code=400, detail=result["error"])

    transactions = result["transactions"]
    if not transactions:
        return {"bank": result["bank"], "imported": 0, "skipped": 0, "total_rows": result["row_count"]}

    # Categorize
    categorize_transactions(transactions, db)

    # Dedup
    new_txs, skipped = dedup_transactions(transactions, db, account_id=account_id)

    # Insert
    for tx in new_txs:
        db.add(Transaction(
            date=date.fromisoformat(tx["date"]),
            amount=tx["amount"],
            merchant=tx["merchant"],
            category=tx.get("category", "Other"),
            account_id=tx.get("account_id"),
            source=DataSource(tx.get("source", "manual")),
            currency=tx.get("currency", "CAD"),
            hash=tx["hash"],
            sequence=tx.get("sequence", 0),
            description=tx.get("description"),
        ))

    db.commit()

    return {
        "bank": result["bank"],
        "imported": len(new_txs),
        "skipped": skipped,
        "total_rows": result["row_count"],
    }


# ─── Wealthsimple Import ────────────────────────────────────────────

@router.post("/wealthsimple")
async def import_wealthsimple(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    content = await file.read()
    csv_text = content.decode("utf-8-sig")

    reader = csv.reader(io.StringIO(csv_text))
    try:
        header_row = next(reader)
    except StopIteration:
        raise HTTPException(status_code=400, detail="Empty CSV")

    rows = list(reader)
    ws_type = detect_wealthsimple_type(header_row)

    if ws_type == "holdings":
        holdings = parse_holdings(header_row, rows)

        # Clear existing holdings and replace (snapshot approach)
        db.query(Holding).filter(Holding.source == DataSource.WEALTHSIMPLE).delete()

        for h in holdings:
            as_of = h.get("as_of_date")
            db.add(Holding(
                asset_name=h["asset_name"],
                ticker=h.get("ticker"),
                quantity=h["quantity"],
                book_value=h["book_value"],
                market_value=h["market_value"],
                currency=h.get("currency", "CAD"),
                as_of_date=date.fromisoformat(as_of) if as_of else date.today(),
                source=DataSource.WEALTHSIMPLE,
            ))

        db.commit()
        return {"type": "holdings", "imported": len(holdings)}

    elif ws_type == "activity":
        activity = parse_activity(header_row, rows)
        categorize_transactions(activity, db)
        new_txs, skipped = dedup_transactions(activity, db)

        for tx in new_txs:
            db.add(Transaction(
                date=date.fromisoformat(tx["date"]),
                amount=tx["amount"],
                merchant=tx["merchant"],
                category=tx.get("category", "Other"),
                source=DataSource.WEALTHSIMPLE,
                currency=tx.get("currency", "CAD"),
                hash=tx["hash"],
                sequence=tx.get("sequence", 0),
                description=tx.get("description"),
            ))

        db.commit()
        return {"type": "activity", "imported": len(new_txs), "skipped": skipped}

    else:
        raise HTTPException(status_code=400, detail="Could not detect Wealthsimple export type")


# ─── SimpleFin ───────────────────────────────────────────────────────

class SimpleFinSetup(BaseModel):
    setup_token: str


@router.post("/simplefin/setup")
async def simplefin_setup(req: SimpleFinSetup):
    try:
        access_url = await SimpleFinClient.exchange_setup_token(req.setup_token)
        # In production, store encrypted. For now, return it.
        return {"access_url": access_url, "status": "connected"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"SimpleFin setup failed: {str(e)}")


@router.post("/simplefin/sync")
async def simplefin_sync(db: Session = Depends(get_db)):
    access_url = settings.SIMPLEFIN_ACCESS_URL
    if not access_url:
        raise HTTPException(status_code=400, detail="SimpleFin not configured. Set CLAWFIN_SIMPLEFIN_ACCESS_URL.")

    client = SimpleFinClient(access_url)
    raw_data = await client.fetch_accounts()

    # Sync accounts
    sf_accounts = client.normalize_accounts(raw_data)
    account_map = {}  # external_id -> db account_id

    for acct in sf_accounts:
        existing = db.query(Account).filter(Account.external_id == acct["external_id"]).first()
        if existing:
            existing.balance = acct["balance"]
            account_map[acct["external_id"]] = existing.id
        else:
            new_acct = Account(
                institution=acct["institution"],
                name=acct["name"],
                account_type=AccountType.CHEQUING,  # Default; user can change
                currency=acct["currency"],
                balance=acct["balance"],
                source=DataSource.SIMPLEFIN,
                external_id=acct["external_id"],
            )
            db.add(new_acct)
            db.flush()
            account_map[acct["external_id"]] = new_acct.id

    # Sync transactions
    sf_transactions = client.normalize_transactions(raw_data)
    for tx in sf_transactions:
        tx["account_id"] = account_map.get(tx.pop("external_account_id", ""))

    categorize_transactions(sf_transactions, db)
    new_txs, skipped = dedup_transactions(sf_transactions, db)

    for tx in new_txs:
        db.add(Transaction(
            date=date.fromisoformat(tx["date"]),
            amount=tx["amount"],
            merchant=tx["merchant"],
            category=tx.get("category", "Other"),
            account_id=tx.get("account_id"),
            source=DataSource.SIMPLEFIN,
            currency=tx.get("currency", "CAD"),
            hash=tx["hash"],
            sequence=tx.get("sequence", 0),
            description=tx.get("description"),
        ))

    db.commit()

    return {
        "accounts_synced": len(sf_accounts),
        "transactions_imported": len(new_txs),
        "transactions_skipped": skipped,
    }
