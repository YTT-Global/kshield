"""Regression tests for ksword — kshield's local-first remediation agent.

Run:  SQLITE_FALLBACK=true python -m pytest tests/test_ksword.py -v
"""
import ast

from app.engine.ksword import construct_remediation_patch
from app.engine.entropy import analyze_entropy_and_secrets
from app.engine.ast_rules import run_ast_structural_scan


def _apply(original: str, patch_diff: str, filename: str = "app.py") -> str:
    """Applies a unified diff produced by ksword back onto the original text,
    so tests can assert on the *result*, not just trust the diff header.

    Writes patch_diff to disk byte-for-byte, exactly like actions.py's
    apply-patch endpoint does — no extra trailing newline added here. A
    missing trailing newline in ksword's own output is exactly the kind of
    bug this is meant to catch, not paper over (real bug: `git apply` failed
    with "corrupt patch" against the live endpoint because `"\\n".join(...)`
    never terminates the final line, and an earlier version of this helper
    added the newline itself, silently hiding it from every test here)."""
    import subprocess
    import tempfile
    import os as _os

    assert not patch_diff or patch_diff.endswith("\n"), (
        "patch_diff must end with a newline or git apply rejects it as corrupt"
    )

    with tempfile.TemporaryDirectory() as d:
        target = _os.path.join(d, filename)
        with open(target, "w") as fh:
            fh.write(original)
        patch_path = _os.path.join(d, "p.diff")
        with open(patch_path, "w") as fh:
            fh.write(patch_diff)
        result = subprocess.run(
            ["git", "apply", "--unsafe-paths", "-p1", patch_path],
            cwd=d, capture_output=True, text=True,
        )
        assert result.returncode == 0, f"patch failed to apply: {result.stderr}"
        with open(target) as fh:
            return fh.read()


class TestHardcodedSecret:
    def test_extracts_to_env_var_and_applies_cleanly(self):
        code = 'import os\napi_key = "ghp_abcdefghijklmnopqrstuvwxyz0123456789"\nx = 5\n'
        result = construct_remediation_patch("server.py", code, "Hardcoded Secret", 2)
        assert result["patch_diff"]
        patched = _apply(code, result["patch_diff"], "server.py")
        assert "os.getenv(\"API_KEY\")" in patched
        assert "ghp_" not in patched
        # The fix must actually clear the original finding, not just look plausible.
        assert not any(f["anomaly_type"] == "Hardcoded Secret" for f in analyze_entropy_and_secrets(patched))
        ast.parse(patched)  # still valid Python

    def test_high_entropy_credential_also_handled(self):
        code = 'value = "aB3kZ9mQ7xR2tY8wL5nP1cV6hJ4sK0dF"\n'
        result = construct_remediation_patch("app.py", code, "High Entropy Credential", 1)
        assert result["patch_diff"]
        patched = _apply(code, result["patch_diff"])
        assert not any(
            f["anomaly_type"] in ("Hardcoded Secret", "High Entropy Credential")
            for f in analyze_entropy_and_secrets(patched)
        )

    def test_declines_when_line_is_not_a_clean_assignment(self):
        # The literal is buried in a dict entry, not `NAME = "literal"` —
        # ksword should decline rather than guess at a risky rewrite.
        code = 'config = {"api_key": "ghp_abcdefghijklmnopqrstuvwxyz0123456789"}\n'
        result = construct_remediation_patch("server.py", code, "Hardcoded Secret", 1)
        assert result["patch_diff"] == ""
        assert result["explanation"]  # still explains, just doesn't fabricate a patch

    def test_non_python_file_declines(self):
        code = 'const apiKey = "ghp_abcdefghijklmnopqrstuvwxyz0123456789";\n'
        result = construct_remediation_patch("server.js", code, "Hardcoded Secret", 1)
        assert result["patch_diff"] == ""


class TestBrokenAccessControl:
    def test_reuses_existing_guard_from_same_file(self):
        code = (
            "from fastapi import APIRouter, Depends\n"
            "router = APIRouter()\n\n"
            "@router.get('/profile')\n"
            "async def profile(user=Depends(get_current_user)):\n"
            "    return user\n\n"
            "@router.post('/admin/delete-user')\n"
            "async def delete_user(user_id: int):\n"
            "    return {'deleted': user_id}\n"
        )
        line_target = code.splitlines().index("@router.post('/admin/delete-user')") + 2  # def line
        result = construct_remediation_patch("routes.py", code, "Broken Access Control", line_target)
        assert result["patch_diff"], "expected a real patch since a working guard exists in this file"
        patched = _apply(code, result["patch_diff"], "routes.py")
        ast.parse(patched)
        remaining = run_ast_structural_scan(patched, "routes.py")
        assert not any(f["anomaly_type"] == "Broken Access Control" and "delete_user" in f["code_snippet"] for f in remaining)
        assert "get_current_user" in patched

    def test_declines_when_no_guard_exists_anywhere_in_file(self):
        # Nothing to safely reuse — must NOT invent a name like the old
        # remediation.py did (that was the original bug: AuthenticationGuard
        # and Depends referenced but never defined or imported).
        code = "@router.post('/admin/delete-user')\nasync def delete_user(user_id: int):\n    return {'deleted': user_id}\n"
        result = construct_remediation_patch("routes.py", code, "Broken Access Control", 1)
        assert result["patch_diff"] == ""
        assert "AuthenticationGuard" not in result["explanation"]

    def test_non_auth_dependency_elsewhere_is_not_treated_as_a_guard(self):
        # Real bug found dogfooding this on kshield's own repo: the only
        # Depends() call elsewhere in the file was get_db_session — a real
        # dependency, just not an auth one. The old version of this strategy
        # grabbed it anyway (any Depends() call, no auth-relevance check),
        # producing a patch that applied cleanly and even "verified" as
        # fixed, while adding no actual authentication whatsoever.
        code = (
            "from fastapi import APIRouter, Depends\n"
            "router = APIRouter()\n\n"
            "@router.get('/scan')\n"
            "async def scan(db=Depends(get_db_session)):\n"
            "    pass\n\n"
            "@router.post('/admin/delete-user')\n"
            "async def delete_user(user_id: int):\n"
            "    return {'deleted': user_id}\n"
        )
        line_target = code.splitlines().index("@router.post('/admin/delete-user')") + 2
        result = construct_remediation_patch("routes.py", code, "Broken Access Control", line_target)
        assert result["patch_diff"] == ""
        assert "get_db_session" not in result["explanation"]

    def test_declines_on_multiline_decorator(self):
        code = (
            "from fastapi import Depends\n\n"
            "@router.get('/x')\n"
            "async def x(user=Depends(get_current_user)):\n"
            "    pass\n\n"
            "@router.post(\n"
            "    '/admin/delete-user'\n"
            ")\n"
            "async def delete_user(user_id: int):\n"
            "    return {'deleted': user_id}\n"
        )
        line_target = code.splitlines().index("async def delete_user(user_id: int):") + 1
        result = construct_remediation_patch("routes.py", code, "Broken Access Control", line_target)
        assert result["patch_diff"] == ""


class TestPossibleTyposquat:
    def test_corrects_typo_import(self):
        code = "import reqeusts\n\nreqeusts.get('https://x')\n"
        description = "Import 'reqeusts' is not declared as a dependency and is very close (edit distance 1) to the well-known package 'requests'. This may be a typo or a typosquatted package."
        result = construct_remediation_patch("app.py", code, "Possible Typosquat", 1, description)
        assert result["patch_diff"]
        patched = _apply(code, result["patch_diff"])
        assert "import requests" in patched
        ast.parse(patched)


class TestNoSafePatchAvailable:
    def test_dependency_hallucination_is_explanation_only(self):
        code = "import quantum_blockchain_ai_toolkit_xyz\n"
        description = "Package 'quantum_blockchain_ai_toolkit_xyz' not found on PyPI. Hallucinated or mistyped packages are a supply-chain risk."
        result = construct_remediation_patch("app.py", code, "Dependency Hallucination", 1, description)
        assert result["patch_diff"] == ""
        assert result["explanation"]

    def test_syntax_violation_is_explanation_only(self):
        result = construct_remediation_patch("app.py", "def f(:\n", "Syntax Violation", 1)
        assert result["patch_diff"] == ""
        assert result["explanation"]

    def test_ai_hallucination_is_explanation_only(self):
        code = "# TODO: verify before prod\npassword = 'hunter2'\n"
        result = construct_remediation_patch("app.py", code, "AI Structural Hallucination", 1)
        assert result["patch_diff"] == ""
        assert result["explanation"]

    def test_unknown_issue_type_declines_gracefully(self):
        result = construct_remediation_patch("app.py", "x = 1\n", "Some Future Finding Type", 1)
        assert result["patch_diff"] == ""
        assert result["explanation"]
