import fnmatch

INLINE_MARKERS = ("# kshield: ignore", "// kshield: ignore", "<!-- kshield: ignore -->")


def apply(findings: list[dict], filename: str, content: str, suppress: dict) -> list[dict]:
    """
    Mark each finding as suppressed=True/False according to suppression rules.
    All findings are returned — callers decide whether to persist or surface them.

    suppress dict keys (all optional):
      severities: list[str]   — e.g. ["LOW", "MEDIUM"]
      rules:      list[str]   — e.g. ["AI Hallucination", "Syntax Violation"]
      paths:      list[str]   — glob patterns, e.g. ["tests/**", "migrations/**"]
    """
    if not findings:
        return findings

    blocked_severities = {s.upper() for s in suppress.get("severities", [])}
    blocked_rules      = {r.lower() for r in suppress.get("rules", [])}
    path_globs         = suppress.get("paths", [])

    file_suppressed = any(fnmatch.fnmatch(filename, pat) for pat in path_globs)

    ignored_lines: set[int] = set()
    for i, line in enumerate(content.splitlines(), start=1):
        if any(marker in line for marker in INLINE_MARKERS):
            ignored_lines.add(i)

    result = []
    for finding in findings:
        suppressed = (
            file_suppressed
            or finding.get("severity", "").upper() in blocked_severities
            or finding.get("anomaly_type", "").lower() in blocked_rules
            or finding.get("line_number", 0) in ignored_lines
        )
        result.append({**finding, "suppressed": suppressed})

    return result
