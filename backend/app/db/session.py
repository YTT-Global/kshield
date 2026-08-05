import os
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base

_SQLITE_FALLBACK = os.getenv("SQLITE_FALLBACK", "false").lower() in ("true", "1", "yes")

if _SQLITE_FALLBACK:
    _db_dir = Path.home() / ".kshield"
    _db_dir.mkdir(parents=True, exist_ok=True)
    # DATABASE_URL override lets tests point at an isolated DB (e.g. in-memory)
    # instead of the real local install at ~/.kshield/kshield.db.
    DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///{_db_dir}/kshield.db")
else:
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/kshield"
    )

engine_kwargs: dict = {"echo": False}

if "postgresql" in DATABASE_URL:
    engine_kwargs.update({
        "pool_size": 20,
        "max_overflow": 10,
        "pool_pre_ping": True,
    })

engine = create_async_engine(DATABASE_URL, **engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()


async def _sqlite_migrate(conn) -> None:
    """Apply additive schema changes to existing SQLite DBs that predate them."""
    migrations = [
        "ALTER TABLE vulnerabilities ADD COLUMN suppressed BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE false_positives ADD COLUMN signature TEXT",
    ]
    for sql in migrations:
        try:
            await conn.execute(__import__("sqlalchemy").text(sql))
        except Exception:
            pass  # column already exists — safe to ignore


async def init_db() -> None:
    if _SQLITE_FALLBACK:
        from app.models import scans, vulnerabilities, false_positives, configurations, audit_runs  # noqa: F401
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await _sqlite_migrate(conn)


async def close_db() -> None:
    if engine:
        await engine.dispose()


async def get_db_session():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
