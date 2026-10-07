"""Integration tests for POST /api/v1/audit and audit_runs persistence (M6).

DB isolation is set up once in conftest.py (imported before this file, by
pytest's own collection order) so this file just reuses that shared DB.

Run:  SQLITE_FALLBACK=true python -m pytest tests/test_audit_api.py -v
"""
import sqlite3
import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import TEST_DB_PATH as _TEST_DB_PATH


@pytest.fixture(autouse=True)
def mock_registry_always_found(monkeypatch):
    async def fake_check(url, package):
        return True
    import app.engine.sandbox as sb
    monkeypatch.setattr(sb, "_check_registry", fake_check)


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:  # triggers the real lifespan -> init_db()
        yield c


def _query_audit_run(name):
    conn = sqlite3.connect(_TEST_DB_PATH)
    row = conn.execute(
        "SELECT name, file_count, findings_count, critical_count, high_count "
        "FROM audit_runs WHERE name = ? ORDER BY created_at DESC LIMIT 1",
        (name,),
    ).fetchone()
    conn.close()
    return row


class TestAuditEndpointResponse:
    def test_response_shape(self, client):
        payload = {
            "name": "shape-test",
            "files": [{"filename": "app.py", "content": "def f():\n    pass\n"}],
        }
        resp = client.post("/api/v1/audit", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        for key in ("name", "file_count", "route_count", "findings_count", "findings", "routes"):
            assert key in body

    def test_findings_reflect_real_content(self, client):
        payload = {
            "name": "content-test",
            "files": [{"filename": "app.py", "content": "API_KEY = 'AKIAIOSFODNN7EXAMPLE'\n"}],  # kshield: ignore
        }
        resp = client.post("/api/v1/audit", json=payload)
        body = resp.json()
        assert body["findings_count"] >= 1
        assert any(f["anomaly_type"] == "Hardcoded Secret" for f in body["findings"])

    def test_empty_file_list_is_clean(self, client):
        payload = {"name": "empty-test", "files": []}
        resp = client.post("/api/v1/audit", json=payload)
        assert resp.status_code == 200
        assert resp.json()["findings_count"] == 0


class TestAuditRunPersistence:
    def test_run_persisted_with_correct_counts(self, client):
        payload = {
            "name": "persistence-test-1",
            "files": [{"filename": "app.py", "content": "API_KEY = 'AKIAIOSFODNN7EXAMPLE'\n"}],  # kshield: ignore
        }
        client.post("/api/v1/audit", json=payload)

        row = _query_audit_run("persistence-test-1")
        assert row is not None
        name, file_count, findings_count, critical_count, high_count = row
        assert file_count == 1
        assert findings_count == 1
        assert critical_count == 1  # hardcoded AWS key is CRITICAL
        assert high_count == 0

    def test_clean_run_persists_zero_counts(self, client):
        payload = {
            "name": "persistence-test-clean",
            "files": [{"filename": "app.py", "content": "def add(a, b):\n    return a + b\n"}],
        }
        client.post("/api/v1/audit", json=payload)

        row = _query_audit_run("persistence-test-clean")
        assert row is not None
        assert row[2] == 0  # findings_count
        assert row[3] == 0  # critical_count
        assert row[4] == 0  # high_count

    def test_repeated_runs_of_same_name_each_get_a_row(self, client):
        payload = {
            "name": "persistence-test-repeat",
            "files": [{"filename": "app.py", "content": "def f(): pass\n"}],
        }
        client.post("/api/v1/audit", json=payload)
        client.post("/api/v1/audit", json=payload)

        conn = sqlite3.connect(_TEST_DB_PATH)
        count = conn.execute(
            "SELECT COUNT(*) FROM audit_runs WHERE name = ?",
            ("persistence-test-repeat",),
        ).fetchone()[0]
        conn.close()
        assert count == 2
