import uuid
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db_session
from app.engine.orchestrator import run_audit
from app.engine.quiet_office import record_dismissal
from app.engine.ksword import construct_remediation_patch
from app.models.audit_runs import AuditRun
from app.api.v1.scan import SuppressConfig

router = APIRouter(prefix="/audit", tags=["Repo-Wide Audit"])


class AuditFile(BaseModel):
    filename: str = Field(...)
    content: str = Field(...)


class AuditRequest(BaseModel):
    name: str = Field(...)
    files: list[AuditFile] = Field(...)
    suppress: SuppressConfig = Field(default_factory=SuppressConfig)


class DismissFindingRequest(BaseModel):
    description: str = Field(...)
    anomaly_type: str = Field(...)
    justification: str = Field(default="")


@router.post("", response_model=dict)
async def process_repo_audit(payload: AuditRequest, db: AsyncSession = Depends(get_db_session)):
    file_tuples = [(f.filename, f.content) for f in payload.files]
    result = await run_audit(file_tuples, db, payload.suppress.model_dump())
    graph = result["graph"]
    all_findings = result["findings"]

    active_findings = [f for f in all_findings if not f.get("suppressed")]
    quieted_findings = [f for f in all_findings if f.get("suppressed")]

    content_by_file = {f.filename: f.content for f in payload.files}
    for finding in active_findings:
        content = content_by_file.get(finding.get("filename"))
        finding["remediation"] = (
            construct_remediation_patch(
                finding["filename"], content, finding["anomaly_type"],
                finding["line_number"], finding.get("description", ""),
            )
            if content is not None
            else {"explanation": "", "patch_diff": ""}
        )

    db.add(AuditRun(
        id=str(uuid.uuid4()),
        name=payload.name,
        file_count=len(graph.files),
        findings_count=len(active_findings),
        critical_count=sum(1 for f in active_findings if f["severity"] == "CRITICAL"),
        high_count=sum(1 for f in active_findings if f["severity"] == "HIGH"),
    ))

    return {
        "name": payload.name,
        "file_count": len(graph.files),
        "route_count": len(graph.routes),
        "symbol_count": sum(len(v) for v in graph.symbols.values()),
        "import_edge_count": sum(len(v) for v in graph.imports.values()),
        "parse_errors": graph.parse_errors,
        "findings_count": len(active_findings),
        "quieted_count": len(quieted_findings),
        "findings": active_findings,
        "quieted": quieted_findings,
        "routes": [
            {
                "path": r.path,
                "method": r.method,
                "handler": r.handler,
                "filename": r.filename,
                "line": r.line,
                "decorators": r.decorators,
            }
            for r in graph.routes
        ],
    }


@router.post("/dismiss-finding", response_model=dict)
async def dismiss_finding(payload: DismissFindingRequest, db: AsyncSession = Depends(get_db_session)):
    """Marks a specific finding as a false positive. Future findings with a
    closely matching description (same anomaly_type) get auto-quieted instead
    of re-flagged — see quiet_office.py."""
    await record_dismissal(payload.description, payload.anomaly_type, payload.justification, db)
    return {"status": "dismissed", "anomaly_type": payload.anomaly_type}


@router.get("/runs", response_model=dict)
async def list_audit_runs(db: AsyncSession = Depends(get_db_session)):
    """Every past run, sorted so the repos that need attention first come
    first — CRITICAL findings weighted above HIGH."""
    result = await db.execute(select(AuditRun))
    runs = result.scalars().all()

    weighted = sorted(
        runs,
        key=lambda r: (r.critical_count * 3 + r.high_count),
        reverse=True,
    )

    return {
        "runs": [
            {
                "name": r.name,
                "file_count": r.file_count,
                "findings_count": r.findings_count,
                "critical_count": r.critical_count,
                "high_count": r.high_count,
                "created_at": r.created_at.isoformat(),
            }
            for r in weighted
        ]
    }
