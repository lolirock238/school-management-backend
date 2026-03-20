from logging.config import fileConfig
import sys
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy import pool
from alembic import context

# Add the parent directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import your models
from app.database import db
from app.models import *

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None and os.path.isfile(config.config_file_name):
    fileConfig(config.config_file_name)

# Set the target metadata
target_metadata = db.metadata

# Get database URL from Flask app config
from app import create_app
flask_app = create_app()
db_url = flask_app.config.get('SQLALCHEMY_DATABASE_URI')
config.set_main_option('sqlalchemy.url', db_url)


def run_migrations_offline() -> None:
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
    connectable = create_engine(db_url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()