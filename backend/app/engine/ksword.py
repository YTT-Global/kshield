"""ksword — kshield's local-first remediation agent.

Not a template engine: remediation.py's old failure mode was returning a
fabricated patch that referenced names ('AuthenticationGuard', 'app') that
didn't exist in the target file, corrupting it on `git apply`. Every
strategy here instead proposes a fix, applies it in-memory, then re-runs the
*same check* that raised the original finding against the patched result —
a patch is only ever returned if that re-check confirms the finding is
actually gone. If a strategy can't produce something it can prove works, it
declines and falls back to an honest explanation-only response. No network
calls, no model inference — every decision is made from the file's own AST
or text, which is what keeps this local-first.
"""

import ast
import difflib
import re

from app.engine.entropy import analyze_entropy_and_secrets
from app.engine.dependency_audit import _closest_popular, _POPULAR_PYTHON, _POPULAR_NPM
from app.engine.graph_builder import build_repo_graph
from app.engine.access_control import check_access_control, _AUTH_KEYWORDS, _looks_like_auth

_ALL_POPULAR = _POPULAR_PYTHON | _POPULAR_NPM


# ── shared helpers ───────────────────────────────────────────────────────────

def _unified_diff(filename: str, original: str, patched: str) -> str:
    # actions.py's apply-patch runs `git apply` with cwd set to the target
    # file's own directory, expecting the default -p1 strip to land on the
    # bare filename relative to that cwd. filename is frequently an absolute
    # path (the CLI always sends one — see scanner.rs/cmd_scan) — using it
    # verbatim here would produce "a//abs/path", which git apply rejects
    # outright ("invalid path") since the -p1-stripped remainder is still
    # absolute. The basename is what -p1 needs to resolve correctly either way.
    display_name = filename.rsplit("/", 1)[-1]
    diff = "\n".join(difflib.unified_diff(
        original.splitlines(), patched.splitlines(),
        fromfile=f"a/{display_name}", tofile=f"b/{display_name}", lineterm="",
    ))
    # `"\n".join` never terminates the final line. `git apply` (actions.py's
    # apply-patch writes this string to a file verbatim, with no newline of
    # its own added) treats a hunk's last line without a trailing newline as
    # "corrupt patch at line N" and refuses the whole file — every strategy
    # in this module goes through this one function, so fixing it here once
    # is what keeps every caller (API response, CLI/dashboard/VSCode display,
    # and the actual `git apply` step) consistent.
    return diff + "\n" if diff else diff


def _parses(code: str) -> bool:
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False


def _rebuild(lines: list[str], original_code: str) -> str:
    code = "\n".join(lines)
    return code + "\n" if original_code.endswith("\n") else code


def _no_patch(explanation: str) -> dict:
    return {"explanation": explanation, "patch_diff": ""}


def _fallback(issue_type: str, reason: str) -> dict:
    return _no_patch(f"ELI5: Found a '{issue_type}' issue, but {reason}. Review the line manually.")


# ── secrets — extract to an environment variable ────────────────────────────

_ASSIGNMENT_RE = re.compile(
    r'^(?P<indent>\s*)(?P<name>[A-Za-z_][A-Za-z0-9_]*)'
    r'(?P<annotation>\s*:\s*[A-Za-z_][A-Za-z0-9_.\[\], ]*)?'
    r'\s*=\s*(?P<quote>[\'"])(?P<literal>.*?)(?P=quote)\s*$'
)


def _env_var_name(identifier: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "_", identifier).upper()


def _ensure_import(lines: list[str], module: str) -> list[str]:
    if any(re.match(rf"^\s*import\s+{module}\b", ln) for ln in lines):
        return lines
    insert_at = 1 if lines and lines[0].startswith("#!") else 0
    return [*lines[:insert_at], f"import {module}", *lines[insert_at:]]


def _fix_secret(filename: str, original_code: str, line_target: int) -> tuple[str, str] | None:
    if not filename.endswith(".py"):
        return None
    lines = original_code.splitlines()
    if not (1 <= line_target <= len(lines)):
        return None

    match = _ASSIGNMENT_RE.match(lines[line_target - 1])
    if not match:
        return None

    env_name = _env_var_name(match.group("name"))
    annotation = match.group("annotation") or ""
    new_line = f'{match.group("indent")}{match.group("name")}{annotation} = os.getenv("{env_name}")'

    patched_lines = lines.copy()
    patched_lines[line_target - 1] = new_line
    patched_lines = _ensure_import(patched_lines, "os")

    explanation = (
        f"ELI5: Moved the hardcoded value on line {line_target} into an environment "
        f"variable — set {env_name} in your environment (or a .env file loaded at "
        f"startup) instead of committing the real value."
    )
    return _rebuild(patched_lines, original_code), explanation


def _verify_secret_fixed(patched_code: str) -> bool:
    if not _parses(patched_code):
        return False
    findings = analyze_entropy_and_secrets(patched_code)
    return not any(f["anomaly_type"] in ("Hardcoded Secret", "High Entropy Credential") for f in findings)


# ── broken access control — reuse a guard already proven in this file ───────

_ROUTE_DECORATOR_METHODS = {"get", "post", "put", "delete", "patch", "options", "head", "route"}
_GUARD_CALL_NAMES = {"Depends", "Security"}


def _decorator_call(dec: ast.expr) -> ast.Call | None:
    return dec if isinstance(dec, ast.Call) else None


def _decorator_method(dec: ast.expr) -> str:
    call = _decorator_call(dec)
    func = call.func if call else dec
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return ""


def _guard_name_from_call(call: ast.Call) -> str | None:
    if call.args and isinstance(call.args[0], ast.Name):
        return call.args[0].id
    return None


def _existing_guard_in_file(tree: ast.Module, skip_lineno: int) -> tuple[str, str] | None:
    """A Depends()/Security() call already used successfully by some *other*
    route in this file — (call_name, guard_target) reused as-is instead of
    inventing a name that might not exist, since fabricating one is exactly
    what made the old remediation engine unsafe.

    Real bug found dogfooding this on kshield's own repo: without the
    _looks_like_auth filter below, this returned get_db_session — a real
    Depends() call, just not an auth one — as the "existing guard" to reuse.
    The patch applied cleanly and even passed verification (see below), but
    added no actual authentication. access_control.py's own test suite
    already locks in that get_db_session must never count as a guard
    (test_db_session_only_dependency_still_flagged); reusing its exact
    keyword filter here is what makes ksword's notion of "a real guard"
    match the checker that actually re-verifies the fix."""
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or node.lineno == skip_lineno:
            continue

        defaults = [*node.args.defaults, *(d for d in node.args.kw_defaults if d is not None)]
        for d in defaults:
            if isinstance(d, ast.Call) and isinstance(d.func, ast.Name) and d.func.id in _GUARD_CALL_NAMES:
                name = _guard_name_from_call(d)
                if name and _looks_like_auth(name, _AUTH_KEYWORDS):
                    return d.func.id, name

        for dec in node.decorator_list:
            call = _decorator_call(dec)
            if not call:
                continue
            for kw in call.keywords:
                if kw.arg != "dependencies" or not isinstance(kw.value, ast.List):
                    continue
                for elt in kw.value.elts:
                    if isinstance(elt, ast.Call) and isinstance(elt.func, ast.Name) and elt.func.id in _GUARD_CALL_NAMES:
                        name = _guard_name_from_call(elt)
                        if name and _looks_like_auth(name, _AUTH_KEYWORDS):
                            return elt.func.id, name
    return None


def _route_decorator_for(node: ast.FunctionDef | ast.AsyncFunctionDef) -> ast.Call | None:
    for dec in node.decorator_list:
        if _decorator_method(dec) in _ROUTE_DECORATOR_METHODS:
            call = _decorator_call(dec)
            if call is not None:
                return call
    return None


def _fix_access_control(filename: str, original_code: str, line_target: int) -> tuple[str, str, str] | None:
    if not filename.endswith(".py"):
        return None
    try:
        tree = ast.parse(original_code)
    except SyntaxError:
        return None

    target = next(
        (n for n in ast.walk(tree)
         if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.lineno == line_target),
        None,
    )
    if target is None:
        return None

    decorator = _route_decorator_for(target)
    if decorator is None or decorator.lineno != decorator.end_lineno:
        # Multi-line decorator, or no route decorator found at this exact
        # line — text-splicing a single line is unsafe here, decline.
        return None

    guard = _existing_guard_in_file(tree, target.lineno)
    if guard is None:
        return None  # nothing proven-real in this file to reuse — don't invent a name
    call_name, guard_target = guard

    lines = original_code.splitlines()
    dec_line = lines[decorator.lineno - 1]
    close_paren = dec_line.rfind(")")
    if close_paren == -1:
        return None

    insertion = f", dependencies=[{call_name}({guard_target})]"
    patched_lines = lines.copy()
    patched_lines[decorator.lineno - 1] = dec_line[:close_paren] + insertion + dec_line[close_paren:]

    explanation = (
        f"ELI5: This route had no auth guard, but {call_name}({guard_target}) is "
        f"already used to guard other routes in this file — reused it here instead "
        f"of inventing a new one."
    )
    return _rebuild(patched_lines, original_code), explanation, target.name


def _verify_access_control_fixed(filename: str, patched_code: str, handler_name: str) -> bool:
    # Verifies against access_control.py's graph-aware checker, not
    # ast_rules.py's simpler one — ast_rules.py treats any Depends() call as
    # a guard (that's the exact bug M2 fixes for the audit path; see
    # access_control.py's own test suite), so it would happily "confirm" a
    # patch that reuses a non-auth dependency like get_db_session. Since
    # _existing_guard_in_file above only ever proposes a name that already
    # passes the same auth-keyword filter, this can only make verification
    # stricter than the old ast_rules.py check, never looser.
    if not _parses(patched_code):
        return False
    graph = build_repo_graph([(filename, patched_code)])
    findings = check_access_control(graph.routes)
    return not any(
        f["anomaly_type"] == "Broken Access Control" and handler_name in f.get("code_snippet", "")
        for f in findings
    )


# ── possible typosquat — correct the import to the well-known name ─────────

_TYPOSQUAT_RE = re.compile(r"Import '([^']+)'.*well-known package '([^']+)'")


def _fix_typosquat(original_code: str, line_target: int, bad_name: str, good_name: str) -> tuple[str, str] | None:
    lines = original_code.splitlines()
    if not (1 <= line_target <= len(lines)) or bad_name not in lines[line_target - 1]:
        return None

    patched_lines = lines.copy()
    patched_lines[line_target - 1] = lines[line_target - 1].replace(bad_name, good_name)
    explanation = (
        f"ELI5: '{bad_name}' is one edit away from the well-known package '{good_name}' "
        f"and isn't declared as a dependency — corrected the import. Double check this "
        f"is really what you meant before committing."
    )
    return _rebuild(patched_lines, original_code), explanation


def _verify_typosquat_fixed(filename: str, patched_code: str, line_target: int, bad_name: str) -> bool:
    if filename.endswith(".py") and not _parses(patched_code):
        return False
    lines = patched_code.splitlines()
    if not (1 <= line_target <= len(lines)):
        return False
    tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_\-]*", lines[line_target - 1])
    return bad_name not in tokens


# ── dependency hallucination — no safe patch, but a grounded suggestion ────

_DEP_NAME_RE = re.compile(r"[Pp]ackage '([^']+)'|module '([^']+)'|gem '([^']+)'")


def _explain_dependency_hallucination(description: str) -> str:
    match = _DEP_NAME_RE.search(description)
    name = next((g for g in match.groups() if g), None) if match else None
    suggestion = _closest_popular(name, _ALL_POPULAR) if name else None
    if suggestion:
        candidate, _dist = suggestion
        return (
            f"ELI5: This package wasn't found on the registry. Closest well-known "
            f"name: '{candidate}' — check if that's what you meant. If not, verify "
            f"the exact package name and publisher before installing it."
        )
    return (
        "ELI5: This package wasn't found on the registry, and no similar well-known "
        "package name was found either. Double check the exact name and publisher "
        "before installing it — this may be a fully hallucinated dependency."
    )


# ── entry point ──────────────────────────────────────────────────────────────

def construct_remediation_patch(
    filename: str,
    original_code: str,
    issue_type: str,
    line_target: int,
    description: str = "",
) -> dict:
    if issue_type in ("Hardcoded Secret", "High Entropy Credential"):
        proposal = _fix_secret(filename, original_code, line_target)
        if proposal:
            patched_code, explanation = proposal
            if _verify_secret_fixed(patched_code):
                return {"explanation": explanation, "patch_diff": _unified_diff(filename, original_code, patched_code)}
        return _fallback(issue_type, "no assignment of the form NAME = \"literal\" was found on this line to safely rewrite")

    if issue_type == "Broken Access Control":
        proposal = _fix_access_control(filename, original_code, line_target)
        if proposal:
            patched_code, explanation, handler_name = proposal
            if _verify_access_control_fixed(filename, patched_code, handler_name):
                return {"explanation": explanation, "patch_diff": _unified_diff(filename, original_code, patched_code)}
        return _fallback(
            issue_type,
            "no other route in this file has a working auth guard to safely reuse — "
            "add one manually, e.g. dependencies=[Depends(get_current_user)], and make "
            "sure it's imported",
        )

    if issue_type == "Possible Typosquat":
        match = _TYPOSQUAT_RE.search(description)
        if match:
            bad_name, good_name = match.group(1), match.group(2)
            proposal = _fix_typosquat(original_code, line_target, bad_name, good_name)
            if proposal:
                patched_code, explanation = proposal
                if _verify_typosquat_fixed(filename, patched_code, line_target, bad_name):
                    return {"explanation": explanation, "patch_diff": _unified_diff(filename, original_code, patched_code)}
        return _fallback(issue_type, "could not confidently identify the intended package name from this line")

    if issue_type == "Dependency Hallucination":
        return _no_patch(_explain_dependency_hallucination(description))

    if issue_type == "Syntax Violation":
        return _no_patch(
            "ELI5: This file doesn't parse as valid Python — often the tail end of an "
            "AI-generated edit that got cut off mid-statement. Compare against the last "
            "known-good version and complete the truncated block manually; no automated "
            "fix is safe here since the original intent isn't recoverable."
        )

    if issue_type == "AI Structural Hallucination":
        return _no_patch(
            "ELI5: This looks like placeholder or stub content that still needs real "
            "logic — an automated patch can't safely guess the intended implementation, "
            "so this needs a manual pass."
        )

    return _fallback(issue_type, "no remediation strategy is registered for this finding type yet")
