import httpx
import re
import sys
import logging

logger = logging.getLogger("kshield.sandbox")

PYPI_URL_PATTERN     = "https://pypi.org/pypi/{pkg}/json"
NPM_URL_PATTERN      = "https://registry.npmjs.org/{pkg}"
GO_PROXY_URL_PATTERN = "https://proxy.golang.org/{module}/@latest"
RUBYGEMS_URL_PATTERN = "https://rubygems.org/api/v1/gems/{gem}.json"

# Python stdlib — sys.stdlib_module_names available on 3.10+; fallback for older
_STDLIB_MODULES: frozenset = frozenset(sys.stdlib_module_names) if hasattr(sys, "stdlib_module_names") else frozenset([
    "os", "sys", "re", "math", "ast", "datetime", "logging", "json", "uuid",
    "asyncio", "typing", "collections", "functools", "itertools", "pathlib",
    "hashlib", "hmac", "base64", "struct", "socket", "threading", "io",
    "contextlib", "traceback", "warnings", "copy", "pickle", "subprocess",
    "abc", "time", "random", "string", "enum", "dataclasses", "inspect",
    "importlib", "types", "weakref", "gc", "platform", "tempfile", "shutil",
    "glob", "fnmatch", "stat", "signal", "errno", "binascii", "codecs",
    "urllib", "http", "email", "html", "xml", "csv", "configparser",
    "argparse", "unittest", "pdb", "profile", "timeit", "cProfile",
    "concurrent", "multiprocessing", "queue", "heapq", "bisect", "array",
    "decimal", "fractions", "statistics", "cmath", "operator",
])

# Go standard library top-level path segments (no dot in first element → stdlib)
# A Go import is stdlib if its first path segment has no dot: "fmt", "os", "net/http"
def _go_is_stdlib(module_path: str) -> bool:
    first_segment = module_path.split("/")[0]
    return "." not in first_segment


def _find_import_line(lines: list[str], token: str) -> int:
    """Return the 1-based line number of the first line containing `token`."""
    for i, line in enumerate(lines, 1):
        if token in line:
            return i
    return 1


async def _check_registry(url: str, package: str) -> bool:
    async with httpx.AsyncClient(timeout=2.5) as client:
        try:
            resp = await client.get(url)
            return resp.status_code != 404
        except httpx.RequestError:
            logger.warning("Registry timeout verifying %s", package)
            return True  # network unavailable — don't block commit


async def evaluate_dependency_hallucinations(code_data: str, filename: str) -> list:
    findings: list = []
    lines = code_data.splitlines()

    # ── Python ────────────────────────────────────────────────────────────────
    if filename.endswith(".py"):
        imports = re.findall(r"^(?:import|from)\s+([a-zA-Z0-9_]+)", code_data, re.MULTILINE)
        seen: set[str] = set()
        for pkg in imports:
            if pkg in seen or pkg in _STDLIB_MODULES:
                continue
            seen.add(pkg)
            if not await _check_registry(PYPI_URL_PATTERN.format(pkg=pkg), pkg):
                line_no = _find_import_line(lines, pkg)
                findings.append({
                    "line_number": line_no,
                    "anomaly_type": "Dependency Hallucination",
                    "severity": "CRITICAL",
                    "description": (
                        f"Package '{pkg}' not found on PyPI. "
                        f"Hallucinated or mistyped packages are a supply-chain risk."
                    ),
                    "code_snippet": lines[line_no - 1].strip() if line_no <= len(lines) else f"import {pkg}",
                })

    # ── JavaScript / TypeScript ───────────────────────────────────────────────
    elif filename.endswith((".js", ".ts", ".tsx", ".jsx", ".mjs", ".cjs")):
        raw = re.findall(
            r"""(?:import|from|require\()\s*['"]([a-zA-Z0-9_\-\/@][a-zA-Z0-9_\-\/.]*)['"]""",
            code_data,
        )
        seen = set()
        for raw_pkg in raw:
            pkg = (
                "/".join(raw_pkg.split("/")[:2])
                if raw_pkg.startswith("@")
                else raw_pkg.split("/")[0]
            )
            if pkg in seen or pkg.startswith((".", "/")):
                continue
            seen.add(pkg)
            if not await _check_registry(NPM_URL_PATTERN.format(pkg=pkg), pkg):
                line_no = _find_import_line(lines, raw_pkg)
                findings.append({
                    "line_number": line_no,
                    "anomaly_type": "Dependency Hallucination",
                    "severity": "CRITICAL",
                    "description": (
                        f"npm package '{pkg}' not found on the registry. "
                        f"Hallucinated or mistyped packages are a supply-chain risk."
                    ),
                    "code_snippet": lines[line_no - 1].strip() if line_no <= len(lines) else f"import '{pkg}'",
                })

    # ── Go ────────────────────────────────────────────────────────────────────
    elif filename.endswith(".go"):
        # Handles both single-line and import-block forms
        go_imports = re.findall(r'"([a-zA-Z0-9_.\-/]+)"', code_data)
        seen = set()
        for module in go_imports:
            if module in seen or _go_is_stdlib(module):
                continue
            seen.add(module)
            encoded = module.replace("/", "%2F")
            if not await _check_registry(GO_PROXY_URL_PATTERN.format(module=encoded), module):
                line_no = _find_import_line(lines, module)
                findings.append({
                    "line_number": line_no,
                    "anomaly_type": "Dependency Hallucination",
                    "severity": "CRITICAL",
                    "description": (
                        f"Go module '{module}' not found on proxy.golang.org. "
                        f"Hallucinated or mistyped modules are a supply-chain risk."
                    ),
                    "code_snippet": lines[line_no - 1].strip() if line_no <= len(lines) else f'"{module}"',
                })

    # ── Ruby ──────────────────────────────────────────────────────────────────
    elif filename.endswith((".rb", "Gemfile")):
        # Match: require 'gem'  /  gem 'name', '~> 1.0'
        ruby_gems = re.findall(r"""(?:require|gem)\s+['"]([a-zA-Z0-9_\-]+)['"]""", code_data)
        # Ruby stdlib names to skip (common subset)
        _RUBY_STDLIB = frozenset([
            "date", "time", "json", "yaml", "csv", "set", "uri", "net/http",
            "fileutils", "pathname", "tempfile", "logger", "optparse",
            "open-uri", "digest", "base64", "securerandom", "stringio",
            "monitor", "observer", "singleton", "forwardable", "benchmark",
        ])
        seen = set()
        for gem in ruby_gems:
            if gem in seen or gem in _RUBY_STDLIB:
                continue
            seen.add(gem)
            if not await _check_registry(RUBYGEMS_URL_PATTERN.format(gem=gem), gem):
                line_no = _find_import_line(lines, gem)
                findings.append({
                    "line_number": line_no,
                    "anomaly_type": "Dependency Hallucination",
                    "severity": "CRITICAL",
                    "description": (
                        f"Ruby gem '{gem}' not found on RubyGems. "
                        f"Hallucinated or mistyped gems are a supply-chain risk."
                    ),
                    "code_snippet": lines[line_no - 1].strip() if line_no <= len(lines) else f"gem '{gem}'",
                })

    return findings
