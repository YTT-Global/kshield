import asyncio
import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.graph_builder import build_repo_graph
from app.engine.access_control import check_access_control
from app.engine.entropy import analyze_entropy_and_secrets
from app.engine.model import sequence_classifier_node
import app.engine.sandbox as sandbox
from app.engine.sandbox import evaluate_dependency_hallucinations
from app.engine.dependency_audit import (
    parse_declared_dependencies,
    check_dependency_hygiene,
    raw_first_party_names,
    workspace_package_names,
    _normalize,
)
from app.engine.pattern_archive import load_extra_auth_keywords
from app.engine.quiet_office import suppress_similar_findings
from app.engine.suppress import apply as apply_suppressions
from app.models.false_positives import FalsePositive

from sqlalchemy import select

# How many registry lookups run at once during the bulk pre-check. Real bug
# found in the y-n8n pilot (13,000+ files, hundreds of genuinely unique
# packages): checking them one at a time sequentially took minutes and
# blocked the whole server, even with per-package caching already in place.
_REGISTRY_CONCURRENCY = 20

# ast_rules.py's own "Broken Access Control" detection is intentionally not called
# here — check_access_control (graph-aware) supersedes it. Its "Syntax Violation"
# detection is also not re-run here; graph_builder already attempted to parse every
# file, so its parse_errors are reused directly instead of parsing each file twice.

# Lockfiles are full of long base64 integrity hashes that read as high-entropy
# "secrets" to entropy.py but never appear one-at-a-time in a commit diff (which is
# the only place these engines have run until now). A repo-wide audit sees them
# for the first time, so they need an explicit exclusion here.
_GENERATED_FILENAMES = frozenset([
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "Cargo.lock", "poetry.lock", "Pipfile.lock",
    "composer.lock", "Gemfile.lock", "go.sum",
])


def _is_generated_file(filename: str) -> bool:
    return filename.rsplit("/", 1)[-1] in _GENERATED_FILENAMES


# Real bug found in the adk-python pilot: 261 of 326 "Broken Access Control"
# findings (80%) were routes defined inside test files or contributing/samples
# — a pytest test calling a route function directly to unit-test it doesn't
# need Depends(get_current_user), and never runs as a reachable production
# endpoint in the first place. Same shape model.py already uses for its own
# test-file skip.
_TEST_FILE_RE = re.compile(r"(^|/)test[_-]|[_-]test\.py$|/tests?/", re.I)


def _is_test_file(filename: str) -> bool:
    return bool(_TEST_FILE_RE.search(filename))


def _syntax_violation_findings(parse_errors: dict[str, str]) -> list[dict]:
    return [
        {
            "line_number": 1,
            "anomaly_type": "Syntax Violation",
            "severity": "MEDIUM",
            "description": f"Python syntax error: {err}. This often indicates truncated AI-generated code.",
            "code_snippet": "",
            "filename": filename,
        }
        for filename, err in parse_errors.items()
    ]


async def run_audit(files: list[tuple[str, str]], db: AsyncSession, suppress: dict | None = None) -> dict:  # type: ignore[type-arg]
    graph = build_repo_graph(files)

    extra_auth_keywords = await load_extra_auth_keywords(db)
    production_routes = [r for r in graph.routes if not _is_test_file(r.filename)]
    findings = list(check_access_control(production_routes, tuple(extra_auth_keywords)))
    findings.extend(_syntax_violation_findings(graph.parse_errors))

    workspace_names = workspace_package_names(files)
    declared = parse_declared_dependencies(files) | {_normalize(n) for n in workspace_names}

    first_party = frozenset(raw_first_party_names(graph.imports) | workspace_names)
    registry_cache: dict = {}

    # Pass 1 — collect every (package, url) that would need a registry check,
    # across the whole repo, with zero network calls (collect_only short-circuits
    # each check to a no-op placeholder). Then check them all at once, bounded,
    # concurrently — not one at a time, once per file.
    pending: set[tuple[str, str]] = set()
    for filename, content in files:
        if _is_generated_file(filename):
            continue
        await evaluate_dependency_hallucinations(content, filename, first_party, collect_only=pending)

    if pending:
        sem = asyncio.Semaphore(_REGISTRY_CONCURRENCY)

        async def _bounded_check(package: str, url: str) -> tuple[str, bool]:
            async with sem:
                return package, await sandbox._check_registry(url, package)

        for package, exists in await asyncio.gather(*[_bounded_check(pkg, url) for pkg, url in pending]):
            registry_cache[package] = exists

    # Runs after the registry pass above (not before it, like M5 originally
    # had it) so a package that independently resolves on the registry isn't
    # also flagged as typosquatting some other, unrelated well-known name.
    findings.extend(check_dependency_hygiene(graph.imports, declared, registry_cache))

    # Pass 2 — the real pass. Every registry_cache lookup is now a cache hit,
    # so this no longer waits on the network at all.
    for filename, content in files:
        if _is_generated_file(filename):
            continue

        per_file_findings = (
            analyze_entropy_and_secrets(content)
            + sequence_classifier_node.process_inference_eval(content, filename)
            + await evaluate_dependency_hallucinations(content, filename, first_party, registry_cache)
        )

        for finding in per_file_findings:
            findings.append({**finding, "filename": filename})

    # Real gap found in review: this repo-wide path used to ignore both
    # .kshield.yml's rules/severities/paths config and the dashboard's global
    # "Suppress Rule" action entirely — only quiet_office's dismissed-finding
    # memory applied here, unlike the single-file /api/v1/scan path (scan.py),
    # which already merges both. A rule suppressed via the dashboard, or a
    # severity/path ignored via .kshield.yml, would silently reappear the
    # moment you ran `kshield agent` instead of `kshield hook` — same config,
    # two different outcomes. Mirrors scan.py's merge exactly.
    fp_result = await db.execute(select(FalsePositive).where(FalsePositive.file_signature == "*"))
    global_suppressed_rules = [fp.rule_id for fp in fp_result.scalars().all()]

    merged_suppress = dict(suppress or {})
    merged_suppress["rules"] = list(set(merged_suppress.get("rules", []) + global_suppressed_rules))

    content_by_file = dict(files)
    findings = [
        apply_suppressions([finding], finding.get("filename", ""), content_by_file.get(finding.get("filename", ""), ""), merged_suppress)[0]
        for finding in findings
    ]

    # quiet_office runs last and is order-safe (sticky) — it never un-suppresses
    # a finding the pass above already suppressed for an unrelated reason.
    findings = await suppress_similar_findings(findings, db)

    return {"graph": graph, "findings": findings}  # type: ignore[return-value]
