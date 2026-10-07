"""Shared pytest fixtures. Sets up one isolated SQLite DB for the whole test
session — pytest always imports conftest.py before any test module, so this
runs before app.db.session's engine gets created, guaranteeing every test file
shares the same isolated DB and never touches the real ~/.kshield/kshield.db.

Run:  SQLITE_FALLBACK=true python -m pytest tests/ -v
"""
import os
import tempfile

TEST_DB_PATH = os.path.join(tempfile.gettempdir(), "kshield_test_suite.db")
if os.path.exists(TEST_DB_PATH):
    os.remove(TEST_DB_PATH)
os.environ["SQLITE_FALLBACK"] = "true"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_PATH}"

import pytest_asyncio
from sqlalchemy import delete
from app.db.session import init_db, AsyncSessionLocal


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _init_test_db():
    await init_db()


@pytest_asyncio.fixture
async def db_session():
    async with AsyncSessionLocal() as session:
        yield session

    # Tests commit their own writes (so a single test's write is visible to
    # its own subsequent reads), which means a plain rollback() here wouldn't
    # undo anything. Explicitly wipe the tables M7 writes to, so state never
    # leaks from one test into the next regardless of run order.
    from app.models.configurations import Configuration
    from app.models.false_positives import FalsePositive
    async with AsyncSessionLocal() as cleanup:
        await cleanup.execute(delete(Configuration))
        await cleanup.execute(delete(FalsePositive))
        await cleanup.commit()
