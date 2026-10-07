"""Regression tests for signature-based false-positive suppression (M7 — Quiet Office).

Run:  SQLITE_FALLBACK=true python -m pytest tests/test_quiet_office.py -v
"""
import pytest
from app.engine.quiet_office import suppress_similar_findings, record_dismissal, _signature


class TestSignatureNormalization:
    def test_quoted_identifiers_stripped(self):
        a = _signature("Import 'foo' is used but not declared.")
        b = _signature("Import 'bar' is used but not declared.")
        assert a == b

    def test_file_paths_stripped(self):
        a = _signature("Found in app/main.py at line 5.")
        b = _signature("Found in lib/utils.js at line 5.")
        assert a == b

    def test_genuinely_different_text_not_collapsed(self):
        a = _signature("Import 'foo' is used but not declared.")
        b = _signature("This route has no authentication guard.")
        assert a != b


class TestAutoSuppression:
    # ── TRUE POSITIVES ──────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_dismissed_pattern_suppresses_a_different_but_similar_finding(self, db_session):
        # This is the exact case a hash-based embedding can't handle: two
        # different imports, two different files, same template shape.
        dismissed_desc = "Import 'internal_metrics_shim' is used in app/a.py but not declared in requirements.txt or package.json found in this audit."
        await record_dismissal(dismissed_desc, "Undeclared Dependency", "our own internal tooling", db_session)
        await db_session.commit()

        new_finding = {
            "anomaly_type": "Undeclared Dependency",
            "description": "Import 'internal_logging_shim' is used in app/b.py but not declared in requirements.txt or package.json found in this audit.",
            "severity": "LOW",
        }
        result = await suppress_similar_findings([new_finding], db_session)
        assert result[0]["suppressed"] is True
        assert "internal tooling" in result[0]["suppressed_reason"]

    @pytest.mark.asyncio
    async def test_exact_repeat_is_suppressed(self, db_session):
        desc = "Import 'known_ok_pkg' is used in x.py but not declared in requirements.txt or package.json found in this audit."
        await record_dismissal(desc, "Undeclared Dependency", "fine", db_session)
        await db_session.commit()

        result = await suppress_similar_findings(
            [{"anomaly_type": "Undeclared Dependency", "description": desc, "severity": "LOW"}], db_session
        )
        assert result[0]["suppressed"] is True

    # ── FALSE POSITIVE SUPPRESSION (i.e. this suite's own false positives) ──

    @pytest.mark.asyncio
    async def test_empty_findings_list_returns_empty(self, db_session):
        assert await suppress_similar_findings([], db_session) == []

    @pytest.mark.asyncio
    async def test_no_prior_dismissals_nothing_suppressed(self, db_session):
        finding = {"anomaly_type": "Hardcoded Secret", "description": "some new finding", "severity": "CRITICAL"}
        result = await suppress_similar_findings([finding], db_session)
        assert result[0]["suppressed"] is False
        assert "suppressed_reason" not in result[0]

    @pytest.mark.asyncio
    async def test_different_anomaly_type_not_suppressed_even_if_text_matches(self, db_session):
        desc = "Import 'foo' is used but not declared."
        await record_dismissal(desc, "Undeclared Dependency", "fine", db_session)
        await db_session.commit()

        finding = {"anomaly_type": "Possible Typosquat", "description": desc, "severity": "HIGH"}
        result = await suppress_similar_findings([finding], db_session)
        assert result[0]["suppressed"] is False

    @pytest.mark.asyncio
    async def test_genuinely_different_finding_of_same_type_not_suppressed(self, db_session):
        await record_dismissal(
            "Import 'ok_pkg' is used in a.py but not declared in requirements.txt or package.json found in this audit.",
            "Undeclared Dependency", "fine", db_session,
        )
        await db_session.commit()

        finding = {
            "anomaly_type": "Undeclared Dependency",
            "description": "Something completely unrelated about a different kind of problem entirely.",
            "severity": "LOW",
        }
        result = await suppress_similar_findings([finding], db_session)
        assert result[0]["suppressed"] is False
