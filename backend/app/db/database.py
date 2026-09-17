from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

from app.core.config import settings

# Engine works with either PostgreSQL (postgresql+asyncpg://) or SQLite (sqlite+aiosqlite://)
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    # SQLite requires check_same_thread=False and increased busy timeout
    connect_args={"check_same_thread": False, "timeout": 30} if "sqlite" in settings.DATABASE_URL else {}
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()


async def get_db():
    """Dependency providing a transactional async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Create all database tables on application startup."""
    import app.db.models  # Ensure all model tables are registered with Base.metadata
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
