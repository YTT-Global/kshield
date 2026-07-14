import os
import uuid
import subprocess
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.false_positives import FalsePositive
from app.models.vulnerabilities import Vulnerability
from app.models.scans import Scan

router = APIRouter(tags=["Actions"])


class SuppressRequest(BaseModel):
    rule_type: str
    justification: str = ""


class ApplyPatchRequest(BaseModel):
    vulnerability_id: str


@router.post("/suppress")
async def suppress_rule(body: SuppressRequest, db: AsyncSession = Depends(get_db_session)):
    """Globally suppress a rule type across all future scans."""
    # Idempotent — skip if already suppressed
    existing = await db.execute(
        select(FalsePositive).where(
            FalsePositive.rule_id == body.rule_type,
            FalsePositive.file_signature == "*",
        )
    )
    if existing.scalar_one_or_none():
        return {"status": "already_suppressed", "rule_type": body.rule_type}

    db.add(FalsePositive(
        id=str(uuid.uuid4()),
        file_signature="*",
        rule_id=body.rule_type,
        justification=body.justification or "Suppressed via dashboard",
    ))
    return {"status": "suppressed", "rule_type": body.rule_type}


@router.post("/apply-patch")
async def apply_patch(body: ApplyPatchRequest, db: AsyncSession = Depends(get_db_session)):
    """Apply the remediation patch for a vulnerability directly to the file on disk."""
    vuln_result = await db.execute(
        select(Vulnerability).where(Vulnerability.id == body.vulnerability_id)
    )
    vuln = vuln_result.scalar_one_or_none()
    if not vuln:
        raise HTTPException(status_code=404, detail="Vulnerability not found")

    scan_result = await db.execute(
        select(Scan).where(Scan.id == vuln.scan_id)
    )
    scan = scan_result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan record not found")

    # Re-generate the patch (we don't store the full patch in the DB)
    from app.engine.remediation import construct_remediation_patch

    # Try to find the file relative to common repo roots
    filename = scan.filename
    candidates = [
        Path(filename),
        Path.home() / filename,
        Path.cwd() / filename,
    ]
    file_path = next((p for p in candidates if p.exists()), None)

    if not file_path:
        # Can't find file — return the patch diff for the client to apply manually
        try:
            content = ""
            patch = construct_remediation_patch(filename, content, vuln.anomaly_type, vuln.line_number)
        except Exception:
            patch = {"explanation": "", "patch_diff": ""}
        return {
            "status": "patch_only",
            "message": "File not found on disk — copy the patch and apply manually.",
            "patch_diff": patch["patch_diff"],
        }

    content = file_path.read_text()
    patch = construct_remediation_patch(str(file_path), content, vuln.anomaly_type, vuln.line_number)

    if not patch["patch_diff"]:
        return {"status": "no_patch", "message": "No automated patch available for this finding."}

    # Write patch to a temp file and apply with `patch` or `git apply`
    patch_file = Path("/tmp") / f"kshield_{body.vulnerability_id[:8]}.patch"
    patch_file.write_text(patch["patch_diff"])

    result = subprocess.run(
        ["git", "apply", "--ignore-whitespace", str(patch_file)],
        capture_output=True, text=True,
        cwd=file_path.parent,
    )
    patch_file.unlink(missing_ok=True)

    if result.returncode == 0:
        return {"status": "applied", "file": str(file_path)}
    else:
        return {
            "status": "patch_only",
            "message": "Could not auto-apply — copy the patch and apply manually.",
            "patch_diff": patch["patch_diff"],
        }


@router.get("/suppress")
async def list_suppressed(db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(FalsePositive))
    rules = result.scalars().all()
    return [{"rule_type": r.rule_id, "justification": r.justification, "created_at": r.created_at.isoformat()} for r in rules]


@router.delete("/suppress/{rule_type}")
async def unsuppress_rule(rule_type: str, db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(
        select(FalsePositive).where(
            FalsePositive.rule_id == rule_type,
            FalsePositive.file_signature == "*",
        )
    )
    fp = result.scalar_one_or_none()
    if not fp:
        raise HTTPException(status_code=404, detail="Rule not suppressed")
    await db.delete(fp)
    return {"status": "unsuppressed", "rule_type": rule_type}
