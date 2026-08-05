import json
import re
import tomllib

from app.engine.sandbox import _STDLIB_MODULES

# A deliberately small, high-confidence list of well-known packages per ecosystem.
# This is what typosquat detection measures distance against — not exhaustive,
# just the names an attacker (or a hallucinating AI) is most likely to imitate.
_POPULAR_PYTHON = frozenset([
    "requests", "numpy", "pandas", "flask", "django", "fastapi", "boto3",
    "click", "pytest", "sqlalchemy", "pydantic", "httpx", "uvicorn", "jinja2",
    "cryptography", "pillow", "scipy", "matplotlib", "tensorflow", "torch",
    "celery", "redis", "psycopg2", "pymongo", "beautifulsoup4", "selenium",
    "pyyaml", "aiohttp", "starlette", "alembic", "gunicorn", "black", "flake8",
    "mypy", "setuptools", "wheel", "virtualenv", "poetry", "typer",
])

_POPULAR_NPM = frozenset([
    "react", "react-dom", "lodash", "axios", "express", "webpack", "typescript",
    "eslint", "vue", "angular", "jquery", "moment", "chalk", "commander",
    "dotenv", "jest", "babel", "next", "vite", "tailwindcss", "prettier",
    "redux", "rxjs", "socket.io", "mongoose", "passport", "cors", "uuid",
])

_MANIFEST_BASENAMES = {"requirements.txt", "pyproject.toml", "package.json"}

# Node core modules — JS's equivalent of Python's stdlib, not installed dependencies.
_NODE_BUILTINS = frozenset([
    "fs", "path", "http", "https", "os", "child_process", "crypto", "events",
    "stream", "util", "url", "querystring", "buffer", "net", "tls", "dns",
    "cluster", "assert", "readline", "zlib", "vm", "worker_threads", "process",
    "module", "timers", "string_decoder", "punycode", "perf_hooks",
])

# Provided by a host runtime at execution time rather than installed as a
# package — e.g. "vscode" is injected by the VS Code extension host.
_AMBIENT_MODULES = frozenset(["vscode"])


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curr = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            curr[j] = min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + cost)
        prev = curr
    return prev[-1]


def _normalize(name: str) -> str:
    return name.lower().replace("_", "-")


def _closest_popular(name: str, popular: frozenset[str]) -> tuple[str, int] | None:
    normalized = _normalize(name)
    if normalized in popular:
        return None
    best: tuple[str, int] | None = None
    for candidate in popular:
        # Skip names too different in length to plausibly be a typo
        if abs(len(candidate) - len(normalized)) > 2:
            continue
        dist = _levenshtein(normalized, candidate)
        if dist == 0 or dist > 2:
            continue
        if best is None or dist < best[1]:
            best = (candidate, dist)
    return best


def _parse_requirements_txt(content: str) -> set[str]:
    names = set()
    for line in content.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        pkg = re.split(r"[<>=!~;\[]", line, 1)[0].strip()
        if pkg:
            names.add(_normalize(pkg))
    return names


def _dep_spec_name(spec: str) -> str:
    """Extract the bare package name from a PEP 508 dependency string like
    "requests>=2.0" or "some-pkg[extra]<2.0,>=1.0"."""
    return re.split(r"[<>=!~;\[\s]", spec, 1)[0].strip()


def _parse_pyproject_toml(content: str) -> set[str]:
    # Real bug found in the adk-python pilot: this was previously skipped
    # entirely ("better to under-report than misparse"), so a repo declaring
    # dependencies only via pyproject.toml (no requirements.txt) had every
    # single non-stdlib import read as "undeclared" — 255 false positives in
    # one repo. tomllib (stdlib since Python 3.11) makes real parsing safe.
    try:
        data = tomllib.loads(content)
    except tomllib.TOMLDecodeError:
        return set()

    names: set[str] = set()

    project = data.get("project")
    if isinstance(project, dict):
        for dep in project.get("dependencies") or []:
            if isinstance(dep, str):
                pkg = _dep_spec_name(dep)
                if pkg:
                    names.add(_normalize(pkg))
        optional = project.get("optional-dependencies")
        if isinstance(optional, dict):
            for group in optional.values():
                if isinstance(group, list):
                    for dep in group:
                        if isinstance(dep, str):
                            pkg = _dep_spec_name(dep)
                            if pkg:
                                names.add(_normalize(pkg))

    tool = data.get("tool")
    poetry = tool.get("poetry") if isinstance(tool, dict) else None
    if isinstance(poetry, dict):
        for section in ("dependencies", "dev-dependencies"):
            deps = poetry.get(section)
            if isinstance(deps, dict):
                names.update(_normalize(n) for n in deps if n.lower() != "python")
        group = poetry.get("group")
        if isinstance(group, dict):
            for group_data in group.values():
                if not isinstance(group_data, dict):
                    continue
                group_deps = group_data.get("dependencies")
                if isinstance(group_deps, dict):
                    names.update(_normalize(n) for n in group_deps if n.lower() != "python")

    return names


def _parse_package_json(content: str) -> set[str]:
    try:
        data = json.loads(content)
    except (json.JSONDecodeError, ValueError):
        return set()
    names = set()
    for key in ("dependencies", "devDependencies"):
        names.update(_normalize(n) for n in data.get(key, {}).keys())
    return names


def workspace_package_names(files: list[tuple[str, str]]) -> set[str]:
    """Package names declared via a package.json's own "name" field. In a
    monorepo, a workspace package like "@webstudio-is/template" is imported
    with an npm-scoped-looking specifier even though it's this codebase's own
    code, not a real external dependency — raw_first_party_names alone can't
    catch this since it only matches bare directory/file-stem names, not a
    package's self-declared scoped identity. Unnormalized, matching
    raw_first_party_names' contract for sandbox.py's raw token comparison."""
    names: set[str] = set()
    for filename, content in files:
        if filename.rsplit("/", 1)[-1] != "package.json":
            continue
        try:
            data = json.loads(content)
        except (json.JSONDecodeError, ValueError):
            continue
        name = data.get("name")
        if isinstance(name, str) and name:
            names.add(name)
    return names


def parse_declared_dependencies(files: list[tuple[str, str]]) -> set[str]:
    declared: set[str] = set()
    for filename, content in files:
        basename = filename.rsplit("/", 1)[-1]
        if basename == "requirements.txt":
            declared |= _parse_requirements_txt(content)
        elif basename == "package.json":
            declared |= _parse_package_json(content)
        elif basename == "pyproject.toml":
            declared |= _parse_pyproject_toml(content)
    return declared


def raw_first_party_names(imports_by_file: dict[str, list[str]]) -> set[str]:
    """Directory names and file stems that exist in this batch, unmodified —
    an import matching one of these is this codebase's own code, not a
    dependency. Unnormalized so sandbox.py can compare its raw import tokens
    directly; _first_party_names below normalizes on top of this for this
    module's own (case/dash-insensitive) matching."""
    names: set[str] = set()
    for filename in imports_by_file:
        parts = filename.split("/")
        names.update(parts[:-1])
        names.add(parts[-1].rsplit(".", 1)[0])
    return names


def _first_party_names(imports_by_file: dict[str, list[str]]) -> set[str]:
    return {_normalize(n) for n in raw_first_party_names(imports_by_file)}


def check_dependency_hygiene(
    imports_by_file: dict[str, list[str]],
    declared: set[str],
    registry_verified: dict[str, bool] | None = None,
) -> list[dict]:
    """No network call of its own — registry_verified is sandbox.py's already-
    resolved cache (package name -> exists on the registry), passed in so an
    independently real package isn't also flagged as a typosquat of some
    other, unrelated well-known name. Real bug found in the adk-python
    pilot: 'retry' (a real PyPI package) is edit-distance 2 from 'poetry',
    and 'mcp' (Anthropic's real Model Context Protocol SDK) is edit-distance
    2 from 'mypy' — both genuinely published packages, neither squatting on
    the other, just short names close together in edit-distance space."""
    findings: list[dict] = []
    first_party = _first_party_names(imports_by_file)
    verified = registry_verified or {}

    for filename, imports in imports_by_file.items():
        if not filename.endswith((".py", ".js", ".jsx", ".ts", ".tsx")):
            continue

        popular = _POPULAR_PYTHON if filename.endswith(".py") else _POPULAR_NPM

        for imp in imports:
            if imp.startswith((".", "/", "@/")):
                continue  # relative/local import (or a TS/Vite path alias like
                # "@/hooks") — not a package at all, even though it starts
                # with "@" the same way a real scoped npm package would
            # Modern Node code increasingly uses the "node:" protocol prefix
            # for built-ins (e.g. "node:crypto") — same module, different spelling.
            bare = imp[5:] if imp.lower().startswith("node:") else imp
            if bare.lower() in _STDLIB_MODULES or bare.lower() in _NODE_BUILTINS:
                continue
            normalized = _normalize(imp)
            if (
                normalized in declared
                or normalized in popular
                or normalized in first_party
                or normalized in _AMBIENT_MODULES
            ):
                continue

            match = None if verified.get(imp) is True else _closest_popular(imp, popular)
            if match:
                candidate, dist = match
                severity = "CRITICAL" if dist == 1 else "HIGH"
                findings.append({
                    "line_number": 1,
                    "anomaly_type": "Possible Typosquat",
                    "severity": severity,
                    "description": (
                        f"Import '{imp}' is not declared as a dependency and is very close "
                        f"(edit distance {dist}) to the well-known package '{candidate}'. "
                        f"This may be a typo or a typosquatted package."
                    ),
                    "code_snippet": f"import {imp}",
                    "filename": filename,
                })
            else:
                findings.append({
                    "line_number": 1,
                    "anomaly_type": "Undeclared Dependency",
                    "severity": "LOW",
                    "description": (
                        f"Import '{imp}' is used in {filename} but not declared in "
                        f"requirements.txt or package.json found in this audit."
                    ),
                    "code_snippet": f"import {imp}",
                    "filename": filename,
                })

    return findings
