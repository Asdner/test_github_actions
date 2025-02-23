from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.declarative import declarative_base

DATABASE_URL = "sqlite+aiosqlite:///./app.py.db"

engine = create_async_engine(DATABASE_URL, echo=True, future=True)
Base = declarative_base()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async_session = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    async with async_session() as session:
        yield session
