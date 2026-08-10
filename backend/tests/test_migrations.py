from alembic import command
import pytest
from sqlalchemy import create_engine, inspect, text

from backend.db import models  # noqa: F401 - registers model metadata
from backend.db.database import Base
from backend.db.migration import (
    HEAD_REVISION,
    LEGACY_REVISION,
    alembic_config,
    upgrade_database,
)


def _sqlite_engine(tmp_path, name):
    return create_engine(f"sqlite:///{tmp_path / name}")


def _database_revision(engine):
    with engine.connect() as connection:
        return connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()


def _assert_current_schema(engine):
    inspector = inspect(engine)
    assert set(Base.metadata.tables).issubset(inspector.get_table_names())

    for table_name, table in Base.metadata.tables.items():
        expected_columns = set(table.columns.keys())
        actual_columns = {
            column["name"] for column in inspector.get_columns(table_name)
        }
        assert expected_columns == actual_columns

    transaction_indexes = {
        index["name"] for index in inspector.get_indexes("transactions")
    }
    assert "ix_transactions_pending" in transaction_indexes


def test_fresh_database_migrates_to_current_schema(tmp_path):
    engine = _sqlite_engine(tmp_path, "fresh.db")

    upgrade_database(engine)

    assert _database_revision(engine) == HEAD_REVISION
    _assert_current_schema(engine)


def test_pre_revival_database_upgrades_without_data_loss(tmp_path):
    engine = _sqlite_engine(tmp_path, "legacy.db")
    command.upgrade(alembic_config(engine), LEGACY_REVISION)

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO accounts (
                    id, institution, name, account_type, currency, balance,
                    source, external_id, created_at, updated_at
                ) VALUES (
                    1, 'Test Bank', 'Chequing', 'CHEQUING', 'CAD', 123.45,
                    'SIMPLEFIN', 'legacy-account', :created_at, :updated_at
                )
                """
            ),
            {"created_at": "2026-01-01 00:00:00", "updated_at": "2026-01-01 00:00:00"},
        )
        connection.execute(
            text(
                """
                INSERT INTO transactions (
                    id, date, amount, merchant, normalized_merchant, category,
                    account_id, source, currency, hash, sequence, description,
                    created_at
                ) VALUES (
                    1, '2026-01-02', -12.34, 'LEGACY MERCHANT', 'legacy merchant',
                    'Other', 1, 'SIMPLEFIN', 'CAD', 'legacy-hash', 0,
                    'preserve me', :created_at
                )
                """
            ),
            {"created_at": "2026-01-02 00:00:00"},
        )
        connection.execute(text("DROP TABLE alembic_version"))

    upgrade_database(engine)

    assert _database_revision(engine) == HEAD_REVISION
    _assert_current_schema(engine)
    with engine.connect() as connection:
        account = connection.execute(
            text(
                """
                SELECT institution, balance, simplefin_account_present, on_budget
                FROM accounts WHERE id = 1
                """
            )
        ).mappings().one()
        transaction = connection.execute(
            text(
                """
                SELECT merchant, description, memo, pending
                FROM transactions WHERE id = 1
                """
            )
        ).mappings().one()

    assert account["institution"] == "Test Bank"
    assert account["balance"] == 123.45
    assert account["simplefin_account_present"] == 1
    assert account["on_budget"] == 1
    assert transaction["merchant"] == "LEGACY MERCHANT"
    assert transaction["description"] == "preserve me"
    assert transaction["memo"] is None
    assert transaction["pending"] == 0


def test_current_unversioned_database_bootstraps_idempotently(tmp_path):
    engine = _sqlite_engine(tmp_path, "current.db")
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO app_config (key, value, updated_at)
                VALUES ('migration-test', 'preserved', '2026-01-01 00:00:00')
                """
            )
        )

    upgrade_database(engine)
    upgrade_database(engine)

    assert _database_revision(engine) == HEAD_REVISION
    _assert_current_schema(engine)
    with engine.connect() as connection:
        value = connection.execute(
            text("SELECT value FROM app_config WHERE key = 'migration-test'")
        ).scalar_one()
    assert value == "preserved"


def test_partial_unversioned_schema_is_refused(tmp_path):
    engine = _sqlite_engine(tmp_path, "partial.db")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE accounts (id INTEGER PRIMARY KEY)"))

    with pytest.raises(RuntimeError, match="partial AutoFin schema"):
        upgrade_database(engine)


def test_schema_downgrade_is_refused_without_modifying_revision(tmp_path):
    engine = _sqlite_engine(tmp_path, "downgrade.db")
    upgrade_database(engine)

    with pytest.raises(RuntimeError, match="restore a database backup"):
        command.downgrade(alembic_config(engine), LEGACY_REVISION)

    assert _database_revision(engine) == HEAD_REVISION
