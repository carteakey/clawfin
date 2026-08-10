"""Add sync metadata, budget scope, and pending transaction fields.

Revision ID: 0002_sync_metadata
Revises: 0001_initial
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_sync_metadata"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ACCOUNT_COLUMNS = (
    sa.Column("available_balance", sa.Float(), nullable=True),
    sa.Column("balance_date", sa.DateTime(), nullable=True),
    sa.Column("last_sync_at", sa.DateTime(), nullable=True),
    sa.Column("last_successful_balance_date", sa.DateTime(), nullable=True),
    sa.Column("last_successful_transaction_date", sa.Date(), nullable=True),
    sa.Column("last_sync_error", sa.Text(), nullable=True),
    sa.Column(
        "simplefin_account_present",
        sa.Boolean(),
        nullable=False,
        server_default=sa.text("1"),
    ),
    sa.Column("stale_reason", sa.String(length=100), nullable=True),
    sa.Column("on_budget", sa.Boolean(), nullable=False, server_default=sa.text("1")),
)

TRANSACTION_COLUMNS = (
    sa.Column("memo", sa.Text(), nullable=True),
    sa.Column("pending", sa.Boolean(), nullable=False, server_default=sa.text("0")),
)


def _add_missing_columns(table_name: str, columns: tuple[sa.Column, ...]) -> None:
    inspector = sa.inspect(op.get_bind())
    existing = {column["name"] for column in inspector.get_columns(table_name)}
    for column in columns:
        if column.name not in existing:
            op.add_column(table_name, column)


def upgrade() -> None:
    _add_missing_columns("accounts", ACCOUNT_COLUMNS)
    _add_missing_columns("transactions", TRANSACTION_COLUMNS)

    inspector = sa.inspect(op.get_bind())
    transaction_indexes = {index["name"] for index in inspector.get_indexes("transactions")}
    if "ix_transactions_pending" not in transaction_indexes:
        op.create_index("ix_transactions_pending", "transactions", ["pending"])


def downgrade() -> None:
    raise RuntimeError("AutoFin schema downgrades are not supported; restore a database backup instead.")
