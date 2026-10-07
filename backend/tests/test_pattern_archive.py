"""Regression tests for shared auth-keyword pattern propagation (M7 — Pattern Archive).

Run:  SQLITE_FALLBACK=true python -m pytest tests/test_pattern_archive.py -v
"""
import pytest
from app.engine.pattern_archive import load_extra_auth_keywords, add_extra_auth_keyword


class TestLoadingAndStoring:
    @pytest.mark.asyncio
    async def test_no_keywords_stored_returns_empty_list(self, db_session):
        result = await load_extra_auth_keywords(db_session)
        assert result == []

    @pytest.mark.asyncio
    async def test_added_keyword_is_returned(self, db_session):
        await add_extra_auth_keyword("verify_session_token", db_session)
        await db_session.commit()

        result = await load_extra_auth_keywords(db_session)
        assert "verify_session_token" in result

    @pytest.mark.asyncio
    async def test_keyword_normalized_to_lowercase(self, db_session):
        await add_extra_auth_keyword("VerifySessionToken", db_session)
        await db_session.commit()

        result = await load_extra_auth_keywords(db_session)
        assert "verifysessiontoken" in result

    @pytest.mark.asyncio
    async def test_duplicate_keyword_not_added_twice(self, db_session):
        await add_extra_auth_keyword("duplicate_guard", db_session)
        await db_session.commit()
        await add_extra_auth_keyword("duplicate_guard", db_session)
        await db_session.commit()

        result = await load_extra_auth_keywords(db_session)
        assert result.count("duplicate_guard") == 1

    @pytest.mark.asyncio
    async def test_multiple_keywords_accumulate(self, db_session):
        await add_extra_auth_keyword("keyword_one", db_session)
        await db_session.commit()
        await add_extra_auth_keyword("keyword_two", db_session)
        await db_session.commit()

        result = await load_extra_auth_keywords(db_session)
        assert "keyword_one" in result
        assert "keyword_two" in result
