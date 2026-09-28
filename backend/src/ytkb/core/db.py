from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from ytkb.core.config import settings

engine = create_async_engine(
    url=settings.database_url,
    echo=settings.environment == "local",
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)