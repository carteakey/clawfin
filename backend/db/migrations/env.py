from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

from backend.config import settings
from backend.db.database import Base
from backend.db import models  # noqa: F401 - registers model metadata


config = context.config
target_metadata = Base.metadata

if not config.get_main_option("sqlalchemy.url"):
    db_path = Path(settings.DB_PATH).expanduser().resolve()
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
