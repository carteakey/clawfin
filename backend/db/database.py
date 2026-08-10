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
    """Upgrade the database schema and apply idempotent data upgrades."""
    from backend.db import models  # noqa: F401 — ensures models are registered
    from backend.db.migration import upgrade_database

    upgrade_database(engine)
    _encrypt_sensitive_config_values()


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
