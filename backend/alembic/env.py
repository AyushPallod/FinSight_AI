import sys
import os
from logging.config import fileConfig
from sqlalchemy import pool
from alembic import context

# 1. Setup Python path so Alembic can import modules from our app directory
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

# 2. Import database components and model registration metadata
from app.core.database import Base, DATABASE_URL
from app.models.user import User  # noqa: F401
from app.models.document import Document  # noqa: F401
from app.models.chat import ChatMessage  # noqa: F401

# This is the Alembic Config object, which provides access to the values within the .ini file.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 3. Set the metadata target for autogenerate detection
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    # Pull the database URL dynamically
    url = DATABASE_URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # Enables SQLite compatibility for modifying tables
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    # Create engine using dynamic database URL
    from sqlalchemy import create_engine

    connectable = create_engine(DATABASE_URL, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # Enables SQLite compatibility for modifying tables
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
