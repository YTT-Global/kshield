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


# Real bug found in the Project-TEC and adk-python pilots: `import cv2` and
# `import yaml` are genuinely real, widely-used packages — just published on
# PyPI under a different name than the module you import. Checking the
# import name itself against the registry always 404s for these, reading as
# a hallucinated package when it's actually a well-known naming mismatch.
_PYPI_NAME_ALIASES: dict[str, str] = {
    "yaml": "PyYAML",
    "dateutil": "python-dateutil",
    "googleapiclient": "google-api-python-client",
    "cv2": "opencv-python",
    "sklearn": "scikit-learn",
    "pil": "Pillow",
    "jwt": "PyJWT",
    "dotenv": "python-dotenv",
    "attr": "attrs",
}


def _find_import_line(lines: list[str], token: str) -> int:
    """Return the 1-based line number of the first line containing `token`."""
    for i, line in enumerate(lines, 1):
        if token in line:
            return i
    return 1


# Real bug found in the ytt-chrome-extensions pilot: the JS/TS import regex
# below treats a bare "from" as enough to start a match, so English prose in
# a JSDoc comment — "The response type from 'proxy.settings.get'" — reads as
# an import statement. Comments never contain real imports, so strip them
# before extracting; string literals are preserved (a "//" inside a URL
# string like "https://x" must survive). Not a full JS parser — good enough
# for this regex-based extraction, not used anywhere line numbers matter.
#
# This is a hand-rolled scanner rather than one regex: the regex form
# (`/\*.*?\*/` plus quote-with-escapes alternations) is polynomial on hostile
# input, because every unterminated "/*" or quote re-scans to the end of the
# file. This repo scans untrusted code (org-audit.sh clones other people's
# repos), so it has to stay linear. Same output as the regex it replaced.
_JS_SPECIAL_RE = re.compile(r"""[/"'`]""")


def _string_end(code: str, start: int) -> int:
    """Index just past the string literal opening at `start`, or -1 if it is
    never terminated. A backslash escapes the next character, newlines
    included."""
    quote = code[start]
    i, n = start + 1, len(code)
    while i < n:
        c = code[i]
        if c == "\\":
            i += 2
        elif c == quote:
            return i + 1
        else:
            i += 1
    return -1


def _strip_js_comments(code: str) -> str:
    out: list[str] = []
    i, n = 0, len(code)
    # Once a "/*" or a given quote has no terminator, no later one can have
    # one either (a later quote is only reachable as an escaped character
    # inside the failed scan, which pairs up identically from there on), so
    # remember that instead of re-scanning to the end of the file each time.
    block_dead = False
    dead_quotes: set[str] = set()

    while i < n:
        m = _JS_SPECIAL_RE.search(code, i)
        if m is None:
            out.append(code[i:])
            break
        j = m.start()
        out.append(code[i:j])
        c = code[j]

        if c == "/" and code.startswith("//", j):
            eol = code.find("\n", j)
            out.append(" ")
            i = n if eol == -1 else eol
            continue
        if c == "/" and code.startswith("/*", j) and not block_dead:
            end = code.find("*/", j + 2)
            if end != -1:
                out.append(" ")
                i = end + 2
                continue
            block_dead = True
        elif c != "/" and c not in dead_quotes:
            end = _string_end(code, j)
            if end != -1:
                out.append(code[j:end])
                i = end
                continue
            dead_quotes.add(c)

        out.append(c)
        i = j + 1

    return "".join(out)


async def _check_registry(url: str, package: str) -> bool:
    async with httpx.AsyncClient(timeout=2.5) as client:
        try:
            resp = await client.get(url)
            return resp.status_code != 404
        except httpx.RequestError:
            logger.warning("Registry timeout verifying %s", package)
            return True  # network unavailable — don't block commit


async def evaluate_dependency_hallucinations(
    code_data: str,
    filename: str,
    first_party: frozenset = frozenset(),
    registry_cache: dict | None = None,
    collect_only: set | None = None,
) -> list:
    """first_party: names of local packages/modules that exist elsewhere in
    the same repo (e.g. a "deals/" directory with its own __init__.py) — used
    only by the repo-wide /audit path, which has that context. The single-file
    /scan path has no repo to derive this from, so it defaults to empty and
    behaves exactly as before.

    registry_cache: shared across every file in one /audit run, so a package
    imported in 50 files gets checked against the registry once, not 50
    times. Real bug found in the webstudio pilot — without this, a repo-wide
    audit of a large monorepo timed out entirely, re-checking the same
    handful of popular packages hundreds of times over.

    collect_only: real bug found in the y-n8n pilot (13,000+ files) — even
    with the cache above, a repo with hundreds of genuinely unique packages
    still checks them one at a time, sequentially, which alone can take
    minutes and blocks the whole server. When this is a set (not None), no
    network call happens at all — every candidate (package, url) is just
    recorded here instead. The caller runs one bulk pass over everything
    collected across all files (see orchestrator.py), concurrently, then
    calls this function again for real with registry_cache pre-populated —
    so the second pass is pure cache lookups, no sequential waiting."""
    findings: list = []
    lines = code_data.splitlines()

    async def _check_cached(url: str, package: str) -> bool:
        if collect_only is not None:
            collect_only.add((package, url))
            return True  # placeholder — this pass's findings are discarded
        if registry_cache is not None and package in registry_cache:
            return registry_cache[package]
        result = await _check_registry(url, package)
        if registry_cache is not None:
            registry_cache[package] = result
        return result

    # ── Python ────────────────────────────────────────────────────────────────
    if filename.endswith(".py"):
        imports = re.findall(r"^(?:import|from)\s+([a-zA-Z0-9_]+)", code_data, re.MULTILINE)
        seen: set[str] = set()
        for pkg in imports:
            if pkg in seen or pkg in _STDLIB_MODULES or pkg in first_party:
                continue
            seen.add(pkg)
            registry_name = _PYPI_NAME_ALIASES.get(pkg.lower(), pkg)
            if not await _check_cached(PYPI_URL_PATTERN.format(pkg=registry_name), pkg):
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
            _strip_js_comments(code_data),
        )
        seen = set()
        for raw_pkg in raw:
            pkg = (
                "/".join(raw_pkg.split("/")[:2])
                if raw_pkg.startswith("@")
                else raw_pkg.split("/")[0]
            )
            if pkg in seen or pkg.startswith((".", "/", "@/")) or pkg in first_party:
                continue
            seen.add(pkg)
            if not await _check_cached(NPM_URL_PATTERN.format(pkg=pkg), pkg):
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
            if module in seen or _go_is_stdlib(module) or module in first_party:
                continue
            seen.add(module)
            encoded = module.replace("/", "%2F")
            if not await _check_cached(GO_PROXY_URL_PATTERN.format(module=encoded), module):
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
            if gem in seen or gem in _RUBY_STDLIB or gem in first_party:
                continue
            seen.add(gem)
            if not await _check_cached(RUBYGEMS_URL_PATTERN.format(gem=gem), gem):
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
