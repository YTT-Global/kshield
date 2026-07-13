import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db_session
from app.engine.entropy import analyze_entropy_and_secrets
from app.engine.ast_rules import run_ast_structural_scan
from app.engine.model import sequence_classifier_node
from app.engine.sandbox import evaluate_dependency_hallucinations
from app.engine.remediation import construct_remediation_patch
from app.models.scans import Scan
from app.models.vulnerabilities import Vulnerability

router = APIRouter(prefix="/scan", tags=["Scanning Diagnostics"])

class ScanRequest(BaseModel):
    filename: str = Field(...)
    content: str = Field(...)
    commit_sha: Optional[str] = Field(None)

@router.post("", response_model=dict)
async def process_code_pipeline_evaluation(payload: CodeExecutionPayload, db: AsyncSession = Depends(get_db_session)):
    try:
        scan_uid = str(uuid.uuid4())
        
        # 1. Trigger concurrent core execution scanning loops
        entropy_alerts = analyze_entropy_and_secrets(payload.content)
        structural_alerts = run_ast_structural_scan(payload.content, payload.filename)
        ml_alerts = sequence_classifier_node.process_inference_eval(payload.content, payload.filename)
        sandbox_alerts = await evaluate_dependency_hallucinations(payload.content, payload.filename)
        
        aggregated_findings = entropy_alerts + structural_alerts + ml_alerts + sandbox_alerts
        is_clear = len(aggregated_findings) == 0
        
        # 2. Persist execution metadata record
        scan_transaction = Scan(
            id=scan_uid,
            filename=payload.filename,
            commit_sha=payload.commit_sha,
            is_safe=is_clear,
            issues_count=len(aggregated_findings)
        )
        db.add(scan_transaction)
        
        computed_vulnerabilities = []
        for issue in aggregated_findings:
            vulnerability_uid = str(uuid.uuid4())
            remediation_package = construct_remediation_patch(
                payload.filename, 
                payload.content, 
                issue["anomaly_type"], 
                issue["line_number"]
            )
            
            # Form vector dimensions matching layout profile maps
            embedding_matrix = sequence_classifier_node.generate_embedding_vector(issue["description"])
            
            vuln_record = Vulnerability(
                id=vulnerability_uid,
                scan_id=scan_uid,
                line_number=issue["line_number"],
                anomaly_type=issue["anomaly_type"],
                severity=issue["severity"],
                description=issue["description"],
                code_snippet=issue["code_snippet"],
                embedding=embedding_matrix
            )
            db.add(vuln_record)
            
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
