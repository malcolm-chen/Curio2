import os
import sys
from logging.config import fileConfig
from urllib.parse import quote_plus

from sqlalchemy import engine_from_config, pool

from alembic import context

# Add the parent directory to the path so we can import from models.py
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import Base from models.py (not app.py to avoid loading Flask app during migrations)
from models import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata from your SQLAlchemy models
target_metadata = Base.metadata

# Construct database URL from environment variables (same logic as app.py)
postgres_user = os.getenv("POSTGRES_USER")
postgres_password = os.getenv("POSTGRES_PASSWORD")
postgres_host = os.getenv("POSTGRES_HOST")
postgres_port = os.getenv("POSTGRES_PORT")
postgres_db = os.getenv("POSTGRES_DB")

if postgres_user and postgres_password and postgres_host and postgres_db:
    if not postgres_port:
        postgres_port = "5432"
    encoded_password = quote_plus(postgres_password)
    database_url = f"postgresql://{postgres_user}:{encoded_password}@{postgres_host}:{postgres_port}/{postgres_db}"
else:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        # Last resort: use defaults
        postgres_user = postgres_user or "curio"
        postgres_password = postgres_password or "curio_password"
        postgres_host = postgres_host or "postgres"
        postgres_port = postgres_port or "5432"
        postgres_db = postgres_db or "curio_db"
        encoded_password = quote_plus(postgres_password)
        database_url = f"postgresql://{postgres_user}:{encoded_password}@{postgres_host}:{postgres_port}/{postgres_db}"

# Override the sqlalchemy.url in alembic.ini with our constructed URL
config.set_main_option("sqlalchemy.url", database_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
