from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db_session
from app.models.scans import Scan
from app.models.vulnerabilities import Vulnerability

router = APIRouter(tags=["History"])


@router.get("/scans")
async def list_scans(limit: int = 50, db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(
        select(Scan).order_by(Scan.created_at.desc()).limit(limit)
    )
    scans = result.scalars().all()

    scan_ids = [s.id for s in scans]
    vuln_result = await db.execute(
        select(Vulnerability).where(Vulnerability.scan_id.in_(scan_ids))
    )
    vulns_by_scan: dict[str, list[Vulnerability]] = defaultdict(list)
    for v in vuln_result.scalars().all():
        vulns_by_scan[v.scan_id].append(v)

    rows = []
    for scan in scans:
        vulns = vulns_by_scan[scan.id]
        rows.append({
            "scan_id": scan.id,
            "filename": scan.filename,
            "safe": scan.is_safe,
            "vulnerabilities_discovered": scan.issues_count,
            "suppressed_count": sum(1 for v in vulns if v.suppressed),
            "created_at": scan.created_at.isoformat(),
            "anomalies": [
                {
                    "id": v.id,
                    "line": v.line_number,
                    "type": v.anomaly_type,
                    "severity": v.severity,
                    "description": v.description,
                    "suppressed": v.suppressed,
                    "remediation": {"explanation": "", "patch_diff": ""},
                }
                for v in vulns
                if not v.suppressed
            ],
        })
    return rows


@router.get("/telemetry")
async def get_telemetry(db: AsyncSession = Depends(get_db_session)):
    total_scans = (await db.execute(select(func.count()).select_from(Scan))).scalar_one()
    clean_files = (
        await db.execute(select(func.count()).select_from(Scan).where(Scan.is_safe == True))
    ).scalar_one()
    open_vulns = (
        await db.execute(select(func.count()).select_from(Vulnerability))
    ).scalar_one()

    breakdown_rows = await db.execute(
        select(Vulnerability.severity, func.count()).group_by(Vulnerability.severity)
    )
    breakdown: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for severity, count in breakdown_rows:
        key = severity.lower()
        if key in breakdown:
            breakdown[key] = count

    return {
        "totalScans": total_scans,
        "cleanFiles": clean_files,
        "openVulnerabilities": open_vulns,
        "breakdown": breakdown,
    }
