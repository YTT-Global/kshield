import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db_session
from app.engine.entropy import analyze_entropy_and_secrets
from app.engine.ast_rules import run_ast_structural_scan
from app.engine.model import sequence_classifier_node
from app.engine.sandbox import evaluate_dependency_hallucinations
from app.engine.ksword import construct_remediation_patch
from app.engine.suppress import apply as apply_suppressions
from app.models.scans import Scan
from app.models.vulnerabilities import Vulnerability
from app.models.false_positives import FalsePositive

router = APIRouter(prefix="/scan", tags=["Scanning Diagnostics"])

class SuppressConfig(BaseModel):
    severities: list[str] = Field(default_factory=list)
    rules:      list[str] = Field(default_factory=list)
    paths:      list[str] = Field(default_factory=list)

class ScanRequest(BaseModel):
    filename: str = Field(...)
    content: str = Field(...)
    commit_sha: Optional[str] = Field(None)
    suppress: SuppressConfig = Field(default_factory=SuppressConfig)

@router.post("", response_model=dict)
async def process_code_pipeline_evaluation(payload: ScanRequest, db: AsyncSession = Depends(get_db_session)):
    try:
        scan_uid = str(uuid.uuid4())
        
        # 1. Trigger concurrent core execution scanning loops
        entropy_alerts = analyze_entropy_and_secrets(payload.content)
        structural_alerts = run_ast_structural_scan(payload.content, payload.filename)
        ml_alerts = sequence_classifier_node.process_inference_eval(payload.content, payload.filename)
        sandbox_alerts = await evaluate_dependency_hallucinations(payload.content, payload.filename)
        
        # Load globally suppressed rules from false_positives table
        fp_result = await db.execute(
            select(FalsePositive).where(FalsePositive.file_signature == "*")
        )
        global_suppressed_rules = [fp.rule_id for fp in fp_result.scalars().all()]

        # Merge global suppressed rules with per-repo suppress config
        merged_suppress = payload.suppress.model_dump()
        merged_suppress["rules"] = list(set(
            merged_suppress.get("rules", []) + global_suppressed_rules
        ))

        raw_findings = entropy_alerts + structural_alerts + ml_alerts + sandbox_alerts
        all_findings = apply_suppressions(
            raw_findings,
            payload.filename,
            payload.content,
            merged_suppress,
        )
        active_findings = [f for f in all_findings if not f.get("suppressed")]
        is_clear = len(active_findings) == 0

        # 2. Persist execution metadata record (counts only active findings)
        scan_transaction = Scan(
            id=scan_uid,
            filename=payload.filename,
            commit_sha=payload.commit_sha,
            is_safe=is_clear,
            issues_count=len(active_findings)
        )
        db.add(scan_transaction)

        computed_vulnerabilities = []
        for issue in all_findings:
            vulnerability_uid = str(uuid.uuid4())
            is_suppressed = issue.get("suppressed", False)

            remediation_package = construct_remediation_patch(
                payload.filename,
                payload.content,
                issue["anomaly_type"],
                issue["line_number"],
                issue["description"],
            ) if not is_suppressed else {"explanation": "", "patch_diff": ""}

            embedding_matrix = sequence_classifier_node.generate_embedding_vector(issue["description"])

            vuln_record = Vulnerability(
                id=vulnerability_uid,
                scan_id=scan_uid,
                line_number=issue["line_number"],
                anomaly_type=issue["anomaly_type"],
                severity=issue["severity"],
                description=issue["description"],
                code_snippet=issue["code_snippet"],
                embedding=embedding_matrix,
                suppressed=is_suppressed,
            )
            db.add(vuln_record)

            if not is_suppressed:
                computed_vulnerabilities.append({
                    "id": vulnerability_uid,
                    "line": issue["line_number"],
                    "type": issue["anomaly_type"],
                    "severity": issue["severity"],
                    "description": issue["description"],
                    "remediation": remediation_package
                })
            
        await db.flush()
        
        return {
            "scan_id": scan_uid,
            "filename": payload.filename,
            "safe": is_clear,
            "vulnerabilities_discovered": len(computed_vulnerabilities),
            "anomalies": computed_vulnerabilities
        }
        
    except Exception as server_err:
        # get_db_session handles rollback on exception — no need to double-call here
        raise HTTPException(status_code=500, detail=f"KShield scan engine fault: {str(server_err)}")
