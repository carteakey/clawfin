import hashlib
from datetime import datetime, date
from sqlalchemy import String, Float, Integer, DateTime, Date, Text, Boolean, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from backend.db.database import Base
import enum


# ─── Enums ───────────────────────────────────────────────────────────

class AccountType(str, enum.Enum):
    CHEQUING = "chequing"
    SAVINGS = "savings"
    CREDIT_CARD = "credit_card"
    TFSA = "tfsa"
    RRSP = "rrsp"
    FHSA = "fhsa"
    MARGIN = "margin"
    CRYPTO = "crypto"
    OTHER = "other"


class DataSource(str, enum.Enum):
    SIMPLEFIN = "simplefin"
    CSV_TD = "csv_td"
    CSV_RBC = "csv_rbc"
    CSV_SCOTIABANK = "csv_scotiabank"
    CSV_BMO = "csv_bmo"
    CSV_CIBC = "csv_cibc"
    WEALTHSIMPLE = "wealthsimple"
    MANUAL = "manual"


# ─── Models ──────────────────────────────────────────────────────────

class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    institution: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(200))
    account_type: Mapped[AccountType] = mapped_column(SAEnum(AccountType))
    currency: Mapped[str] = mapped_column(String(3), default="CAD")
    balance: Mapped[float] = mapped_column(Float, default=0.0)
    available_balance: Mapped[float | None] = mapped_column(Float, nullable=True)
    balance_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    source: Mapped[DataSource] = mapped_column(SAEnum(DataSource))
    external_id: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    amount: Mapped[float] = mapped_column(Float)
    merchant: Mapped[str] = mapped_column(String(500))
    normalized_merchant: Mapped[str | None] = mapped_column(String(500), nullable=True)
    category: Mapped[str] = mapped_column(String(100), default="Other", index=True)
    account_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    source: Mapped[DataSource] = mapped_column(SAEnum(DataSource))
    currency: Mapped[str] = mapped_column(String(3), default="CAD")
    hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    sequence: Mapped[int] = mapped_column(Integer, default=0)  # per-day counter for dedup
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    memo: Mapped[str | None] = mapped_column(Text, nullable=True)
    pending: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    @staticmethod
    def compute_hash(
        tx_date: date,
        amount: float,
        merchant: str,
        account_id: int | None = None,
        sequence: int = 0,
    ) -> str:
        """Hash with sequence counter to avoid collisions on identical same-day transactions."""
        raw = f"{tx_date.isoformat()}|{amount:.2f}|{merchant.strip().lower()}|{account_id or 0}|{sequence}"
        return hashlib.sha256(raw.encode()).hexdigest()


class Holding(Base):
    __tablename__ = "holdings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_name: Mapped[str] = mapped_column(String(200))
    ticker: Mapped[str | None] = mapped_column(String(20), nullable=True)
    quantity: Mapped[float] = mapped_column(Float)
    book_value: Mapped[float] = mapped_column(Float, default=0.0)
    market_value: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(3), default="CAD")
    account_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    as_of_date: Mapped[date] = mapped_column(Date)
    source: Mapped[DataSource] = mapped_column(SAEnum(DataSource), default=DataSource.WEALTHSIMPLE)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Snapshot(Base):
    __tablename__ = "snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, unique=True)
    net_worth: Mapped[float] = mapped_column(Float)
    total_assets: Mapped[float] = mapped_column(Float)
    total_liabilities: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3), default="CAD")
    breakdown: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CategoryRule(Base):
    __tablename__ = "category_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pattern: Mapped[str] = mapped_column(String(500))
    category: Mapped[str] = mapped_column(String(100))
    priority: Mapped[int] = mapped_column(Integer, default=0)
    is_regex: Mapped[bool] = mapped_column(Boolean, default=False)


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    icon: Mapped[str | None] = mapped_column(String(10), nullable=True)  # emoji
    color: Mapped[str | None] = mapped_column(String(7), nullable=True)  # hex
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class FxRate(Base):
    __tablename__ = "fx_rates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    from_currency: Mapped[str] = mapped_column(String(3))
    to_currency: Mapped[str] = mapped_column(String(3))
    rate: Mapped[float] = mapped_column(Float)
    rate_date: Mapped[date] = mapped_column(Date)
    source: Mapped[str] = mapped_column(String(50), default="bank_of_canada")


class AppConfig(Base):
    __tablename__ = "app_config"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Default categories to seed
DEFAULT_CATEGORIES = [
    {"name": "Income",        "icon": "💰", "color": "#1D9E75"},
    {"name": "Rent",          "icon": "🏠", "color": "#F472B6"},
    {"name": "Housing",       "icon": "🧱", "color": "#E879F9"},
    {"name": "Utilities",     "icon": "⚡", "color": "#FBBF24"},
    {"name": "Groceries",     "icon": "🛒", "color": "#34D399"},
    {"name": "Dining",        "icon": "🍽️", "color": "#FB923C"},
    {"name": "Transit",       "icon": "🚌", "color": "#60A5FA"},
    {"name": "Subscriptions", "icon": "🔁", "color": "#A78BFA"},
    {"name": "Insurance",     "icon": "🛡️", "color": "#94A3B8"},
    {"name": "Loan",          "icon": "🏦", "color": "#EF4444"},
    {"name": "Health",        "icon": "💊", "color": "#2DD4BF"},
    {"name": "Shopping",      "icon": "🛍️", "color": "#F87171"},
    {"name": "Entertainment", "icon": "🎬", "color": "#F87171"},
    {"name": "Fees",          "icon": "🧾", "color": "#A1A1AA"},
    {"name": "Transfer",      "icon": "↔️", "color": "#6B7280"},
    {"name": "Other",         "icon": "📦", "color": "#888780"},
]
