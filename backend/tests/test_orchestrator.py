"""Regression tests for the repo-wide audit orchestrator (M3, extended in M7).

Mocks the network-bound registry check the same way test_engines.py does for
sandbox.py directly, so these tests make no real HTTP requests. DB isolation
comes from conftest.py's db_session fixture.

Run:  SQLITE_FALLBACK=true python -m pytest tests/test_orchestrator.py -v
"""
import pytest
from app.engine.orchestrator import run_audit


@pytest.fixture(autouse=True)
def mock_registry_always_found(monkeypatch):
    async def fake_check(url, package):
        return True  # every package "exists" — isolates these tests from the network
    import app.engine.sandbox as sb
    monkeypatch.setattr(sb, "_check_registry", fake_check)


class TestEngineMerging:
    @pytest.mark.asyncio
    async def test_findings_combine_across_engines(self, db_session):
        files = [("app.py", """
API_KEY = "AKIAIOSFODNN7EXAMPLE"  # kshield: ignore

@router.post("/scan")
async def scan(db=Depends(get_db_session)):
    # TODO: verify with production keys before deploy
    pass
""")]
        result = await run_audit(files, db_session)
        types = {f["anomaly_type"] for f in result["findings"]}
        assert "Hardcoded Secret" in types
        assert "Broken Access Control" in types
        assert "AI Structural Hallucination" in types

    @pytest.mark.asyncio
    async def test_every_finding_carries_its_filename(self, db_session):
        files = [
            ("a.py", "API_KEY = 'AKIAIOSFODNN7EXAMPLE'\n"),  # kshield: ignore
            ("b.py", "@router.post('/x')\nasync def x(): pass\n"),
        ]
        result = await run_audit(files, db_session)
        filenames = {f["filename"] for f in result["findings"]}
        assert filenames == {"a.py", "b.py"}

    @pytest.mark.asyncio
    async def test_clean_file_produces_no_findings(self, db_session):
        files = [("clean.py", "def add(a, b):\n    return a + b\n")]
        result = await run_audit(files, db_session)
        assert result["findings"] == []


class TestSyntaxViolationSurfacing:
    @pytest.mark.asyncio
    async def test_parse_error_becomes_a_finding(self, db_session):
        files = [("broken.py", "def oops(:\n")]
        result = await run_audit(files, db_session)
        assert any(f["anomaly_type"] == "Syntax Violation" for f in result["findings"])

    @pytest.mark.asyncio
    async def test_parse_error_does_not_block_other_files(self, db_session):
        files = [
            ("broken.py", "def oops(:\n"),
            ("secret.py", "API_KEY = 'AKIAIOSFODNN7EXAMPLE'\n"),  # kshield: ignore
        ]
        result = await run_audit(files, db_session)
        assert any(f["anomaly_type"] == "Hardcoded Secret" for f in result["findings"])


class TestTestFileRouteExclusion:
    # Real bug found in the adk-python pilot: 261 of 326 "Broken Access
    # Control" findings (80%) were routes defined inside test files — a
    # pytest test calling a route function directly to unit-test it doesn't
    # need an auth guard and never runs as a reachable production endpoint.
    @pytest.mark.asyncio
    async def test_route_in_test_file_not_flagged(self, db_session):
        files = [("tests/test_bots.py", "@router.post('/{bot_id}')\ndef update_bot(bot_id): pass\n")]
        result = await run_audit(files, db_session)
        assert not any(f["anomaly_type"] == "Broken Access Control" for f in result["findings"])

    @pytest.mark.asyncio
    async def test_same_route_in_production_file_still_flagged(self, db_session):
        files = [("app/api/routes/bots.py", "@router.post('/{bot_id}')\ndef update_bot(bot_id): pass\n")]
        result = await run_audit(files, db_session)
        assert any(f["anomaly_type"] == "Broken Access Control" for f in result["findings"])


class TestGeneratedFileExclusion:
    # The lockfile false-positive bug found while testing M3 — a real base64
    # integrity hash reads as a high-entropy "secret" if not excluded.
    @pytest.mark.asyncio
    async def test_package_lock_json_not_scanned_for_secrets(self, db_session):
        content = '{"packages": {"foo": {"integrity": "sha512-' + "A" * 80 + '=="}}}'
        files = [("package-lock.json", content)]
        result = await run_audit(files, db_session)
        assert result["findings"] == []

    @pytest.mark.asyncio
    async def test_yarn_lock_not_scanned(self, db_session):
        content = "foo@^1.0.0:\n  integrity " + "x" * 90 + "\n"
        files = [("yarn.lock", content)]
        result = await run_audit(files, db_session)
        assert result["findings"] == []

    @pytest.mark.asyncio
    async def test_regular_json_file_still_scanned(self, db_session):
        # only known lockfile basenames are excluded — an arbitrary .json
        # containing a real-looking secret should still be caught.
        content = '{"key": "AKIAIOSFODNN7EXAMPLE"}'  # kshield: ignore
        files = [("config.json", content)]
        result = await run_audit(files, db_session)
        assert any(f["anomaly_type"] == "Hardcoded Secret" for f in result["findings"])


class TestGraphIsReturned:
    @pytest.mark.asyncio
    async def test_graph_object_present_alongside_findings(self, db_session):
        files = [("app.py", "@router.get('/x')\nasync def x(): pass\n")]
        result = await run_audit(files, db_session)
        assert "graph" in result
        assert len(result["graph"].routes) == 1


class TestSandboxFirstPartyExclusion:
    # Real bug found during the groundwork pilot: a local package ("deals/")
    # got flagged as a hallucinated PyPI dependency, because sandbox.py never
    # knew this was a repo-wide audit with other files to cross-reference
    # against. Mocks the registry as "not found" specifically, so a passing
    # test here proves the skip happens before the network check even matters
    # — not that the real registry happened to have it.
    @pytest.mark.asyncio
    async def test_local_package_not_flagged_as_hallucinated(self, db_session, monkeypatch):
        async def fake_not_found(url, package):
            return False
        import app.engine.sandbox as sb
        monkeypatch.setattr(sb, "_check_registry", fake_not_found)

        files = [
            ("deals/__init__.py", ""),
            ("deals/service.py", "def advance_stage(): pass\n"),
            ("webhooks/router.py", "from deals.service import advance_stage\n"),
        ]
        result = await run_audit(files, db_session)
        assert not any(f["anomaly_type"] == "Dependency Hallucination" for f in result["findings"])

    @pytest.mark.asyncio
    async def test_same_package_checked_once_across_many_files(self, db_session, monkeypatch):
        # Real bug found in the webstudio pilot — a 2600+ file repo timed out
        # entirely because the same popular packages were re-checked against
        # the registry once per file that imported them, with no caching.
        call_count = {"n": 0}

        async def counting_check(url, package):
            call_count["n"] += 1
            return True

        import app.engine.sandbox as sb
        monkeypatch.setattr(sb, "_check_registry", counting_check)

        files = [(f"src/component_{i}.tsx", "import React from 'react';\n") for i in range(20)]
        await run_audit(files, db_session)
        assert call_count["n"] == 1, f"expected exactly 1 registry call for 'react' across 20 files, got {call_count['n']}"

    @pytest.mark.asyncio
    async def test_unique_package_checks_run_concurrently(self, db_session, monkeypatch):
        # Real bug found in the y-n8n pilot (13,000+ files): even with the
        # cache above, hundreds of genuinely unique packages checked one at a
        # time, sequentially, took minutes and blocked the whole server. This
        # proves they now run concurrently — 40 unique packages with an
        # artificial 100ms delay each would take 4s sequentially, but should
        # complete in well under 1s at a concurrency of 20.
        import asyncio
        import time

        async def slow_check(url, package):
            await asyncio.sleep(0.1)
            return True

        import app.engine.sandbox as sb
        monkeypatch.setattr(sb, "_check_registry", slow_check)

        files = [(f"src/file_{i}.py", f"import unique_pkg_{i}\n") for i in range(40)]
        start = time.monotonic()
        await run_audit(files, db_session)
        elapsed = time.monotonic() - start

        assert elapsed < 1.0, f"expected concurrent checks to finish in well under 1s, took {elapsed:.2f}s — looks sequential"

    @pytest.mark.asyncio
    async def test_registry_verified_package_not_flagged_as_typosquat_end_to_end(self, db_session, monkeypatch):
        # Real bug found in the adk-python pilot: "retry" is a real, published
        # PyPI package but is edit-distance 2 from "poetry" (a popular name),
        # so it read as a possible typosquat even though the registry check
        # in the very same audit run already confirmed it's real. Proves the
        # M5 (dependency hygiene) and M3 (registry check) passes now share
        # results instead of running independently of each other.
        async def fake_found(url, package):
            return True  # "retry" genuinely exists
        import app.engine.sandbox as sb
        monkeypatch.setattr(sb, "_check_registry", fake_found)

        files = [("app.py", "import retry\n")]
        result = await run_audit(files, db_session)
        assert not any(f["anomaly_type"] == "Possible Typosquat" for f in result["findings"])

    @pytest.mark.asyncio
    async def test_genuinely_unknown_package_still_flagged(self, db_session, monkeypatch):
        async def fake_not_found(url, package):
            return False
        import app.engine.sandbox as sb
        monkeypatch.setattr(sb, "_check_registry", fake_not_found)

        files = [("app.py", "import totally_hallucinated_package_xyz\n")]
        result = await run_audit(files, db_session)
        assert any(f["anomaly_type"] == "Dependency Hallucination" for f in result["findings"])

    @pytest.mark.asyncio
    async def test_monorepo_workspace_package_not_flagged(self, db_session, monkeypatch):
        # Real bug found in the webstudio pilot: "@webstudio-is/template" is
        # a workspace package (its own package.json declares that name), not
        # a real external dependency — indistinguishable from a real scoped
        # npm package by import shape alone.
        async def fake_not_found(url, package):
            return False
        import app.engine.sandbox as sb
        monkeypatch.setattr(sb, "_check_registry", fake_not_found)

        files = [
            ("packages/template/package.json", '{"name": "@webstudio-is/template"}'),
            ("apps/builder/src/index.tsx", "import { Scaffold } from '@webstudio-is/template';\n"),
        ]
        result = await run_audit(files, db_session)
        assert not any(f["anomaly_type"] in ("Dependency Hallucination", "Undeclared Dependency") for f in result["findings"])


class TestPatternArchiveIntegration:
    @pytest.mark.asyncio
    async def test_custom_auth_keyword_suppresses_finding(self, db_session):
        from app.engine.pattern_archive import add_extra_auth_keyword
        await add_extra_auth_keyword("ensure_caller_permitted", db_session)
        await db_session.commit()

        files = [("app.py", """
@router.get("/widgets")
async def widgets(user=Depends(ensure_caller_permitted)):
    pass
""")]
        result = await run_audit(files, db_session)
        assert not any(f["anomaly_type"] == "Broken Access Control" for f in result["findings"])


class TestQuietOfficeIntegration:
    @pytest.mark.asyncio
    async def test_dismissed_finding_pattern_is_quieted_next_time(self, db_session):
        from app.engine.quiet_office import record_dismissal

        description = "Import 'internal_metrics_shim' is used in app.py but not declared in requirements.txt or package.json found in this audit."
        await record_dismissal(description, "Undeclared Dependency", "this is our own internal tool", db_session)
        await db_session.commit()

        files = [("app.py", "import internal_metrics_shim\n")]
        result = await run_audit(files, db_session)
        matching = [f for f in result["findings"] if f["anomaly_type"] == "Undeclared Dependency"]
        assert matching, "expected the finding to still be present, just suppressed"
        assert matching[0]["suppressed"] is True
        assert "suppressed_reason" in matching[0]


class TestSuppressConfigIntegration:
    """Real bug found in review: run_audit() (the kshield agent / /api/v1/audit
    path) silently ignored both .kshield.yml's suppress config and the
    dashboard's global "Suppress Rule" action — only quiet_office's dismissed-
    finding memory applied here, unlike scan.py's single-file path, which
    already merges both. Same repo, same rule, different outcome depending on
    whether you ran `kshield hook` or `kshield agent`."""

    @pytest.mark.asyncio
    async def test_kshield_yml_style_rule_suppression_is_respected(self, db_session):
        files = [("app.py", 'API_KEY = "AKIAIOSFODNN7EXAMPLE"\n')]  # kshield: ignore
        suppress = {"severities": [], "rules": ["Hardcoded Secret"], "paths": []}
        result = await run_audit(files, db_session, suppress)
        matching = [f for f in result["findings"] if f["anomaly_type"] == "Hardcoded Secret"]
        assert matching, "expected the finding to still be present, just suppressed"
        assert matching[0]["suppressed"] is True

    @pytest.mark.asyncio
    async def test_kshield_yml_style_severity_suppression_is_respected(self, db_session):
        files = [("app.py", 'API_KEY = "AKIAIOSFODNN7EXAMPLE"\n')]  # kshield: ignore
        suppress = {"severities": ["CRITICAL"], "rules": [], "paths": []}
        result = await run_audit(files, db_session, suppress)
        matching = [f for f in result["findings"] if f["anomaly_type"] == "Hardcoded Secret"]
        assert matching[0]["suppressed"] is True

    @pytest.mark.asyncio
    async def test_kshield_yml_style_path_suppression_is_respected(self, db_session):
        files = [("vendor/app.py", 'API_KEY = "AKIAIOSFODNN7EXAMPLE"\n')]  # kshield: ignore
        suppress = {"severities": [], "rules": [], "paths": ["vendor/**"]}
        result = await run_audit(files, db_session, suppress)
        matching = [f for f in result["findings"] if f["anomaly_type"] == "Hardcoded Secret"]
        assert matching[0]["suppressed"] is True

    @pytest.mark.asyncio
    async def test_globally_suppressed_rule_is_respected(self, db_session):
        from app.models.false_positives import FalsePositive

        db_session.add(FalsePositive(
            id="test-global-suppress",
            file_signature="*",
            rule_id="Hardcoded Secret",
            justification="Suppressed via dashboard",
        ))
        await db_session.commit()

        files = [("app.py", 'API_KEY = "AKIAIOSFODNN7EXAMPLE"\n')]  # kshield: ignore
        result = await run_audit(files, db_session)
        matching = [f for f in result["findings"] if f["anomaly_type"] == "Hardcoded Secret"]
        assert matching[0]["suppressed"] is True

    @pytest.mark.asyncio
    async def test_suppress_config_and_quiet_office_do_not_clobber_each_other(self, db_session):
        # A finding suppressed by the .kshield.yml-style pass must still be
        # suppressed after quiet_office runs afterward, even though it has no
        # dismissed-signature match of its own — this is the exact order-
        # safety bug the "sticky" fix in suppress.py/quiet_office.py guards.
        files = [("app.py", 'API_KEY = "AKIAIOSFODNN7EXAMPLE"\n')]  # kshield: ignore
        suppress = {"severities": [], "rules": ["Hardcoded Secret"], "paths": []}
        result = await run_audit(files, db_session, suppress)
        matching = [f for f in result["findings"] if f["anomaly_type"] == "Hardcoded Secret"]
        assert matching[0]["suppressed"] is True
        assert "suppressed_reason" not in matching[0], "should not fabricate a quiet_office reason for an unrelated suppression"

    @pytest.mark.asyncio
    async def test_unrelated_finding_not_suppressed_by_unrelated_config(self, db_session):
        files = [("app.py", 'API_KEY = "AKIAIOSFODNN7EXAMPLE"\n')]  # kshield: ignore
        suppress = {"severities": [], "rules": ["Possible Typosquat"], "paths": []}
        result = await run_audit(files, db_session, suppress)
        matching = [f for f in result["findings"] if f["anomaly_type"] == "Hardcoded Secret"]
        assert matching[0]["suppressed"] is False
