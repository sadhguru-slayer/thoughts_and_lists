import os
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy import create_engine
from alembic import context
from dotenv import load_dotenv
from app.database import Base  # your Base
import app.models.journal
import app.models.models

# Load .env
load_dotenv()

# Alembic Config object
config = context.config

# Configure logging
fileConfig(config.config_file_name)

# Metadata for autogenerate
target_metadata = Base.metadata

# Get URL directly from environment
DATABASE_URL = os.getenv("DATABASE_URL")

def run_migrations_offline():
    """Run migrations without connecting to DB"""
    context.configure(
        url=DATABASE_URL,  # pass URL directly
        target_metadata=target_metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncConnection

def run_migrations_online():
    """Run migrations with async engine"""
    connectable = create_async_engine(DATABASE_URL, poolclass=pool.NullPool,connect_args={"statement_cache_size": 0})

    async def do_migrations():
        async with connectable.connect() as connection:
            await connection.run_sync(lambda sync_conn: context.configure(
                connection=sync_conn,
                target_metadata=target_metadata
            ))
            async with connection.begin():
                await connection.run_sync(lambda sync_conn: context.run_migrations())

    asyncio.run(do_migrations())

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()