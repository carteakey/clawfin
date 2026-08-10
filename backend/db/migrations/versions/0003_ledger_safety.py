"""Add ledger split metadata and categorization diagnostics.

Revision ID: 0003_ledger_safety
Revises: 0002_sync_metadata
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_ledger_safety"
down_revision: Union[str, None] = "0002_sync_metadata"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TRANSACTION_COLUMNS = (
    sa.Column("category_reason", sa.String(length=40), nullable=True),
    sa.Column("split_parent", sa.Boolean(), nullable=False, server_default=sa.text("0")),
    sa.Column("parent_transaction_id", sa.Integer(), nullable=True),
    sa.Column("split_group_id", sa.String(length=36), nullable=True),
)


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing = {column["name"] for column in inspector.get_columns("transactions")}
    for column in TRANSACTION_COLUMNS:
        if column.name not in existing:
            op.add_column("transactions", column)

    indexes = {index["name"] for index in inspector.get_indexes("transactions")}
    for name, column in (
        ("ix_transactions_split_parent", "split_parent"),
        ("ix_transactions_parent_transaction_id", "parent_transaction_id"),
        ("ix_transactions_split_group_id", "split_group_id"),
    ):
        if name not in indexes:
            op.create_index(name, "transactions", [column])


def downgrade() -> None:
    raise RuntimeError("AutoFin schema downgrades are not supported; restore a database backup instead.")
