"""Accuracy regression tests for the four analysis engine modules.

Run:  SQLITE_FALLBACK=true python -m pytest tests/test_engines.py -v
"""
import pytest
from app.engine.entropy import analyze_entropy_and_secrets
from app.engine.ast_rules import run_ast_structural_scan
from app.engine.model import sequence_classifier_node
# sandbox tests need network; mark them separately


# ─────────────────────────── helpers ────────────────────────────────────────

def _types(findings):
    return [f["anomaly_type"] for f in findings]

def _severities(findings):
    return [f["severity"] for f in findings]


# ════════════════════════════ entropy.py ════════════════════════════════════

class TestEntropy:
    # ── TRUE POSITIVES ──────────────────────────────────────────────────────

    def test_github_pat_detected(self):
        code = "token = 'ghp_abcdefghijklmnopqrstuvwxyz123456789012'"
        r = analyze_entropy_and_secrets(code)
        assert any(f["anomaly_type"] == "Hardcoded Secret" for f in r)
        assert any(f["severity"] == "CRITICAL" for f in r)

    def test_github_fine_grained_pat_detected(self):
        code = "tok = 'github_pat_" + "A" * 82 + "'"
        r = analyze_entropy_and_secrets(code)
        assert any(f["anomaly_type"] == "Hardcoded Secret" for f in r)

    def test_aws_key_detected(self):
        code = "key = 'AKIAIOSFODNN7EXAMPLE'"
        r = analyze_entropy_and_secrets(code)
        assert any(f["anomaly_type"] == "Hardcoded Secret" for f in r)

    def test_openai_key_detected(self):
        code = "key = 'TEST_OPENAI_KEY_XYZ_123456789'"
        r = analyze_entropy_and_secrets(code)
        assert any(f["anomaly_type"] == "Hardcoded Secret" for f in r)

    def test_stripe_live_key_detected(self):
        code = "STRIPE_KEY = 'TEST_STRIPE_KEY_XYZ_123456789'"
        r = analyze_entropy_and_secrets(code)
        assert any(f["anomaly_type"] == "Hardcoded Secret" for f in r)

    def test_slack_bot_token_detected(self):
        code = "slack = 'TEST_SLACK_TOKEN_XYZ_123456789'"
        r = analyze_entropy_and_secrets(code)
        assert any(f["anomaly_type"] == "Hardcoded Secret" for f in r)

    def test_npm_token_detected(self):
        code = "NPM_TOKEN = 'npm_abcdefghijklmnopqrstuvwxyz1234567890'"
        r = analyze_entropy_and_secrets(code)
        assert any(f["anomaly_type"] == "Hardcoded Secret" for f in r)

    def test_high_entropy_string_detected(self):
        # Random-looking 40-char string with no named-pattern match
        code = "secret = 'xK3mP9qL2nV7wR4tY8uI1oA6sD0fG5hJ'"
        r = analyze_entropy_and_secrets(code)
        assert len(r) >= 1

    # ── FALSE POSITIVE SUPPRESSION ──────────────────────────────────────────

    def test_uuid_not_flagged(self):
        code = "uid = '123e4567-e89b-12d3-a456-426614174000'"
        r = analyze_entropy_and_secrets(code)
        assert not any(f["anomaly_type"] == "High Entropy Credential" for f in r)

    def test_sha256_hash_not_flagged(self):
        code = "checksum = 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'"
        r = analyze_entropy_and_secrets(code)
        assert not any(f["anomaly_type"] == "High Entropy Credential" for f in r)

    def test_short_string_not_flagged(self):
        code = "key = 'short'"
        r = analyze_entropy_and_secrets(code)
        assert r == []

    def test_plain_english_not_flagged(self):
        code = "msg = 'Hello, this is a normal string value for testing'"
        r = analyze_entropy_and_secrets(code)
        assert r == []

    def test_semver_not_flagged(self):
        code = "version = '1.2.3-rc.1'"
        r = analyze_entropy_and_secrets(code)
        assert r == []

    def test_no_duplicate_per_line(self):
        # A line that matches a named pattern should produce exactly 1 finding
        code = "x = 'ghp_abcdefghijklmnopqrstuvwxyz123456789012'"
        r = analyze_entropy_and_secrets(code)
        assert len([f for f in r if f["line_number"] == 1]) == 1


# ════════════════════════════ ast_rules.py ══════════════════════════════════

class TestAstRules:
    # ── TRUE POSITIVES ──────────────────────────────────────────────────────

    def test_async_route_without_auth_detected(self):
        code = """
from fastapi import APIRouter
router = APIRouter()

@router.get('/items')
async def list_items():
    return []
"""
        r = run_ast_structural_scan(code, "routes.py")
        assert any(f["anomaly_type"] == "Broken Access Control" for f in r)

    def test_sync_route_without_auth_detected(self):
        code = """
from fastapi import APIRouter
router = APIRouter()

@router.post('/data')
def create_data():
    return {}
"""
        r = run_ast_structural_scan(code, "routes.py")
        assert any(f["anomaly_type"] == "Broken Access Control" for f in r)

    def test_mutation_endpoint_is_high_severity(self):
        code = """
@app.delete('/resource')
async def delete_resource():
    pass
"""
        r = run_ast_structural_scan(code, "main.py")
        assert any(f["severity"] == "HIGH" for f in r)

    def test_get_endpoint_without_auth_is_medium(self):
        code = """
@app.get('/secret-data')
async def get_secret():
    return {}
"""
        r = run_ast_structural_scan(code, "main.py")
        assert any(f["severity"] == "MEDIUM" for f in r)

    # ── FALSE POSITIVE SUPPRESSION ──────────────────────────────────────────

    def test_public_health_path_not_flagged(self):
        code = """
@app.get('/health')
async def health():
    return {"status": "ok"}
"""
        r = run_ast_structural_scan(code, "main.py")
        assert r == []

    def test_docs_path_not_flagged(self):
        code = """
@app.get('/docs')
async def docs():
    pass
"""
        r = run_ast_structural_scan(code, "main.py")
        assert r == []

    def test_route_with_depends_not_flagged(self):
        code = """
from fastapi import Depends
@app.get('/profile')
async def profile(user=Depends(get_current_user)):
    return user
"""
        r = run_ast_structural_scan(code, "routes.py")
        assert r == []

    def test_route_with_decorator_dependencies_not_flagged(self):
        code = """
from fastapi import Depends
@app.get('/admin', dependencies=[Depends(require_admin)])
async def admin_panel():
    return {}
"""
        r = run_ast_structural_scan(code, "routes.py")
        assert r == []

    def test_non_python_file_not_checked(self):
        code = "@app.get('/items')\nasync def items(): pass"
        r = run_ast_structural_scan(code, "routes.ts")
        assert r == []

    def test_plain_function_not_flagged(self):
        code = """
def helper(x):
    return x + 1
"""
        r = run_ast_structural_scan(code, "utils.py")
        assert r == []

    def test_syntax_error_reported(self):
        code = "def broken(:"
        r = run_ast_structural_scan(code, "bad.py")
        assert any(f["anomaly_type"] == "Syntax Violation" for f in r)


# ════════════════════════════ model.py ══════════════════════════════════════

class TestModel:
    def _run(self, code, filename="app.py"):
        return sequence_classifier_node.process_inference_eval(code, filename)

    # ── TRUE POSITIVES ──────────────────────────────────────────────────────

    def test_todo_verify_production_detected(self):
        r = self._run("# TODO: verify with production keys before deploy")
        assert r, "Expected at least one finding"

    def test_fake_password_detected(self):
        r = self._run("password = 'fake_password_123'")
        assert any(f["severity"] in ("HIGH", "MEDIUM") for f in r)

    def test_credential_stub_detected(self):
        r = self._run("password = 'password'")
        assert r

    def test_hallucinated_import_detected(self):
        r = self._run("from internal_ai_test import mock_db")
        assert r

    def test_ai_artifact_detected(self):
        r = self._run("# Replace this with your actual API key here")
        assert r

    def test_raise_not_implemented_detected(self):
        r = self._run("    raise NotImplementedError")
        assert r

    def test_auth_bypass_detected(self):
        r = self._run("# auth bypass for testing — disable auth")
        assert r

    # ── FALSE POSITIVE SUPPRESSION ──────────────────────────────────────────

    def test_test_file_skipped(self):
        # Nothing should fire inside a test file
        r = self._run("def test_auth(): pass\n# TODO: add more assertions", "tests/test_auth.py")
        assert r == []

    def test_normal_code_not_flagged(self):
        r = self._run("def compute(x, y):\n    return x + y\n")
        assert r == []

    def test_one_finding_per_line(self):
        # A line matching multiple patterns should produce exactly 1 finding
        r = self._run("password = 'fake_password'  # TODO: verify with production")
        lines = [f["line_number"] for f in r]
        assert lines.count(1) == 1

    # ── Embedding ────────────────────────────────────────────────────────────

    def test_embedding_is_1536_dims(self):
        vec = sequence_classifier_node.generate_embedding_vector("hello world")
        assert len(vec) == 1536

    def test_embedding_is_deterministic(self):
        a = sequence_classifier_node.generate_embedding_vector("same text")
        b = sequence_classifier_node.generate_embedding_vector("same text")
        assert a == b

    def test_embedding_is_unit_vector(self):
        import math
        vec = sequence_classifier_node.generate_embedding_vector("unit test")
        norm = math.sqrt(sum(v * v for v in vec))
        assert abs(norm - 1.0) < 1e-6


# ════════════════════════════ sandbox.py (offline) ══════════════════════════
# These tests mock network calls so no real HTTP requests are made.

class TestSandboxOffline:
    @pytest.fixture
    def mock_not_found(self, monkeypatch):
        async def fake_check(url, package):
            return False  # simulate 404
        import app.engine.sandbox as sb
        monkeypatch.setattr(sb, "_check_registry", fake_check)

    @pytest.fixture
    def mock_found(self, monkeypatch):
        async def fake_check(url, package):
            return True  # simulate 200
        import app.engine.sandbox as sb
        monkeypatch.setattr(sb, "_check_registry", fake_check)

    @pytest.mark.asyncio
    async def test_hallucinated_pypi_package(self, mock_not_found):
        from app.engine.sandbox import evaluate_dependency_hallucinations
        code = "import totally_fake_package_xyz\n"
        r = await evaluate_dependency_hallucinations(code, "app.py")
        assert any(f["anomaly_type"] == "Dependency Hallucination" for f in r)

    @pytest.mark.asyncio
    async def test_real_pypi_package_not_flagged(self, mock_found):
        from app.engine.sandbox import evaluate_dependency_hallucinations
        code = "import requests\n"
        r = await evaluate_dependency_hallucinations(code, "app.py")
        assert r == []

    @pytest.mark.asyncio
    async def test_stdlib_not_checked(self, mock_not_found):
        from app.engine.sandbox import evaluate_dependency_hallucinations
        code = "import os\nimport sys\nimport re\n"
        r = await evaluate_dependency_hallucinations(code, "app.py")
        assert r == []

    @pytest.mark.asyncio
    async def test_npm_hallucinated_package(self, mock_not_found):
        from app.engine.sandbox import evaluate_dependency_hallucinations
        code = "import { foo } from 'totally-fake-npm-pkg-xyz';\n"
        r = await evaluate_dependency_hallucinations(code, "index.ts")
        assert any(f["anomaly_type"] == "Dependency Hallucination" for f in r)

    @pytest.mark.asyncio
    async def test_relative_import_not_checked(self, mock_not_found):
        from app.engine.sandbox import evaluate_dependency_hallucinations
        code = "import { helper } from './utils';\n"
        r = await evaluate_dependency_hallucinations(code, "app.ts")
        assert r == []

    @pytest.mark.asyncio
    async def test_go_stdlib_not_checked(self, mock_not_found):
        from app.engine.sandbox import evaluate_dependency_hallucinations
        code = 'import (\n    "fmt"\n    "os"\n    "net/http"\n)\n'
        r = await evaluate_dependency_hallucinations(code, "main.go")
        assert r == []

    @pytest.mark.asyncio
    async def test_go_external_module_hallucination(self, mock_not_found):
        from app.engine.sandbox import evaluate_dependency_hallucinations
        code = 'import "github.com/totally/fake-module"\n'
        r = await evaluate_dependency_hallucinations(code, "main.go")
        assert any(f["anomaly_type"] == "Dependency Hallucination" for f in r)

    @pytest.mark.asyncio
    async def test_ruby_gem_hallucination(self, mock_not_found):
        from app.engine.sandbox import evaluate_dependency_hallucinations
        code = "gem 'totally_fake_gem_xyz', '~> 1.0'\n"
        r = await evaluate_dependency_hallucinations(code, "Gemfile")
        assert any(f["anomaly_type"] == "Dependency Hallucination" for f in r)

    @pytest.mark.asyncio
    async def test_correct_line_number_reported(self, mock_not_found):
        from app.engine.sandbox import evaluate_dependency_hallucinations
        code = "# some comment\n\nimport totally_fake_package_xyz\n"
        r = await evaluate_dependency_hallucinations(code, "app.py")
        hallucinations = [f for f in r if f["anomaly_type"] == "Dependency Hallucination"]
        assert hallucinations
        assert hallucinations[0]["line_number"] == 3  # not 1
