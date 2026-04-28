from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from pathlib import Path
from backend.config import settings


class Base(DeclarativeBase):
    pass


def get_engine():
    db_path = Path(settings.DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        echo=False,
    )


engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI dependency for DB sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables and apply idempotent column migrations."""
    from backend.db import models  # noqa: F401 — ensures models are registered
    Base.metadata.create_all(bind=engine)
    _apply_column_migrations()
    _encrypt_sensitive_config_values()


def _apply_column_migrations():
    """Add any columns declared on models that are missing on existing tables.

    SQLite doesn't support true migrations without Alembic; this handles the
    additive case (new nullable/defaulted columns) which is all we currently do.
    """
    from sqlalchemy import inspect, text
    from backend.db import models  # noqa: F401

    inspector = inspect(engine)
    migrations = [
        ("accounts", "available_balance", "FLOAT"),
        ("accounts", "balance_date",      "DATETIME"),
        ("accounts", "last_sync_at",      "DATETIME"),
        ("accounts", "last_successful_balance_date", "DATETIME"),
        ("accounts", "last_successful_transaction_date", "DATE"),
        ("accounts", "last_sync_error",   "TEXT"),
        ("accounts", "simplefin_account_present", "BOOLEAN NOT NULL DEFAULT 1"),
        ("accounts", "stale_reason",      "VARCHAR(100)"),
        ("accounts", "on_budget",         "BOOLEAN NOT NULL DEFAULT 1"),
        ("transactions", "memo",          "TEXT"),
        ("transactions", "pending",       "BOOLEAN NOT NULL DEFAULT 0"),
    ]

    for table, column, coltype in migrations:
        if not inspector.has_table(table):
            continue
        existing = {c["name"] for c in inspector.get_columns(table)}
        if column in existing:
            continue
        with engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}"))


def _encrypt_sensitive_config_values():
    """Upgrade existing plaintext sensitive AppConfig values in-place."""
    from backend.db.models import AppConfig
    from backend.security import encrypt_value, is_encrypted

    sensitive_keys = {"ai_api_key_override", "simplefin_access_url"}
    with SessionLocal() as db:
        changed = False
        rows = db.query(AppConfig).filter(AppConfig.key.in_(sensitive_keys)).all()
        for row in rows:
            if row.value and not is_encrypted(row.value):
                row.value = encrypt_value(row.value)
                changed = True
        if changed:
            db.commit()
