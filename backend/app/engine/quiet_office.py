import re
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.false_positives import FalsePositive

# Findings are template-generated strings, not free-form prose — the only
# parts that vary between two "same kind of problem" findings are quoted
# identifiers (import names, handler names, paths) and bare file paths.
# Stripping those out collapses "Import 'foo' is used in a.py..." and
# "Import 'bar' is used in b.py..." to the same signature, so a dismissal
# recognizes the pattern, not just the one exact string.
_QUOTED_RE = re.compile(r"'[^']*'|\"[^\"]*\"")
_PATH_RE = re.compile(r"\b[\w./-]+\.(?:py|js|ts|tsx|jsx|json|go|rb|txt|yaml|yml)\b")


def _signature(description: str) -> str:
    text = _QUOTED_RE.sub("<X>", description)
    text = _PATH_RE.sub("<FILE>", text)
    return text.strip().lower()


async def suppress_similar_findings(findings: list[dict], db: AsyncSession) -> list[dict]:
    """Tags each finding suppressed=True if its normalized signature matches
    a previously dismissed false positive of the same anomaly type."""
    if not findings:
        return findings

    result = await db.execute(select(FalsePositive).where(FalsePositive.signature.is_not(None)))
    known = result.scalars().all()

    by_rule: dict[str, list[FalsePositive]] = {}
    for fp in known:
        by_rule.setdefault(fp.rule_id, []).append(fp)

    output = []
    for finding in findings:
        candidates = by_rule.get(finding.get("anomaly_type", ""), [])
        # Sticky — a prior pass (e.g. suppress.py's .kshield.yml/global-rule
        # check) may have already suppressed this finding for an unrelated
        # reason; never flip that back to False just because it doesn't also
        # match a dismissed signature.
        suppressed = finding.get("suppressed", False)
        reason = None
        if candidates:
            sig = _signature(finding.get("description", ""))
            for fp in candidates:
                if fp.signature == sig:
                    suppressed = True
                    reason = fp.justification or "matches a previously dismissed finding"
                    break

        entry = {**finding, "suppressed": suppressed}
        if reason:
            entry["suppressed_reason"] = reason
        output.append(entry)

    return output


async def record_dismissal(description: str, anomaly_type: str, justification: str, db: AsyncSession) -> None:
    db.add(FalsePositive(
        id=str(uuid.uuid4()),
        file_signature="*",
        rule_id=anomaly_type,
        justification=justification,
        signature=_signature(description),
    ))
