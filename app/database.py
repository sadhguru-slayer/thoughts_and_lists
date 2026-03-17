import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from typing import AsyncGenerator
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set")

engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    connect_args={"statement_cache_size": 0},
    )

class Base(DeclarativeBase):
    pass

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session

async def init_db():
    from app.models import models
    async with engine.begin() as conn:
        # Create all tables for all models
        await conn.run_sync(Base.metadata.create_all)