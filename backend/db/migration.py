"""Alembic integration for AutoFin's SQLite database."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy.engine import Engine


LEGACY_REVISION = "0001_initial"
HEAD_REVISION = "0003_ledger_safety"
LEGACY_TABLES = frozenset(
    {
        "accounts",
        "app_config",
        "categories",
        "category_rules",
        "fx_rates",
        "holdings",
        "snapshots",
        "transactions",
    }
)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ALEMBIC_INI = _PROJECT_ROOT / "alembic.ini"
_SCRIPT_LOCATION = Path(__file__).resolve().with_name("migrations")


def alembic_config(engine: Engine) -> Config:
    """Build an Alembic configuration for the supplied database engine."""
    config = Config(str(_ALEMBIC_INI))
    config.set_main_option("script_location", str(_SCRIPT_LOCATION))
    database_url = engine.url.render_as_string(hide_password=False).replace("%", "%%")
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def upgrade_database(engine: Engine) -> None:
    """Upgrade an empty, legacy, or already-current database to Alembic head."""
    config = alembic_config(engine)
    table_names = set(inspect(engine).get_table_names())

    if "alembic_version" not in table_names:
        existing_app_tables = table_names & LEGACY_TABLES
        if existing_app_tables:
            missing_tables = LEGACY_TABLES - table_names
            if missing_tables:
                missing = ", ".join(sorted(missing_tables))
                raise RuntimeError(
                    "Refusing to migrate a partial AutoFin schema. "
                    f"Missing tables: {missing}. Restore a complete backup before retrying."
                )
            command.stamp(config, LEGACY_REVISION)

    command.upgrade(config, "head")
