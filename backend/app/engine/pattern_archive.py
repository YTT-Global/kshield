import json
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.configurations import Configuration

_AUTH_KEYWORDS_CONFIG_KEY = "access_control.extra_auth_keywords"


async def load_extra_auth_keywords(db: AsyncSession) -> list[str]:
    result = await db.execute(select(Configuration).where(Configuration.key == _AUTH_KEYWORDS_CONFIG_KEY))
    row = result.scalar_one_or_none()
    if not row:
        return []
    try:
        return json.loads(row.value)
    except (json.JSONDecodeError, ValueError):
        return []


async def add_extra_auth_keyword(keyword: str, db: AsyncSession) -> list[str]:
    """One guard's newly recognized lock shape, added once, applied everywhere —
    every future audit's access_control check picks this up automatically."""
    normalized = keyword.strip().lower()

    result = await db.execute(select(Configuration).where(Configuration.key == _AUTH_KEYWORDS_CONFIG_KEY))
    row = result.scalar_one_or_none()
    existing = json.loads(row.value) if row else []

    if normalized and normalized not in existing:
        existing.append(normalized)

    if row:
        row.value = json.dumps(existing)
    else:
        db.add(Configuration(key=_AUTH_KEYWORDS_CONFIG_KEY, value=json.dumps(existing)))

    return existing
