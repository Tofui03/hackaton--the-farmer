from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import JSONResponse

from src.hitl.review_service import ReviewService
from src.models.audit import AuditRecord, DynamicVerifyRequest, ErrorResponse
from src.models.ingestion import AttachmentReference, EmailRecord
from src.models.review import ReviewUpdate
from src.pipeline.orchestrator import PipelineOrchestrator
from src.pipeline.stage3_compare import rule_based_compare_audit
from src.run_pipeline import audit_record_to_competition_dict
from src.store.audit_store import AuditStore, RevisionConflictError

logger = logging.getLogger(__name__)

router = APIRouter()

# Global singletons for API runtime (can be swapped or injected in tests)
_audit_store: AuditStore = AuditStore()
_review_service: ReviewService = ReviewService()
_orchestrator: PipelineOrchestrator = PipelineOrchestrator(audit_store=_audit_store)


def get_audit_store() -> AuditStore:
    return _audit_store


def set_audit_store(store: AuditStore) -> None:
    global _audit_store, _orchestrator
    _audit_store = store
    _orchestrator = PipelineOrchestrator(audit_store=store)


def get_review_service() -> ReviewService:
    return _review_service


def get_orchestrator() -> PipelineOrchestrator:
    return _orchestrator


@router.get("/")
def get_root(store: AuditStore = Depends(get_audit_store)):
    """Dynamic root status endpoint reporting live audit store metrics (REG-003)."""
    summary = store.get_summary()
    return {
        "service": "SDOC Shipping Document Verification Engine",
        "status": "operational",
        "architecture": "FastAPI + Pluggable Parsers + LLM Normalization",
        "total_audited_emails": summary["total_records"],
        "discrepancies_detected": summary["discrepant_records"],
        "summary": summary,
        "docs_url": "/docs",
        "endpoints": {
            "all_audits": "/audit",
            "single_audit": "/audit/{email_id}",
            "review": "/audit/{email_id}/review",
            "dynamic_verify": "/verify",
            "health": "/health",
            "submission": "/submission",
        },
    }


@router.get("/health")
def get_health():
    """Fast liveness check probe returning HTTP 200 (API-HLT-001)."""
    return {"status": "healthy"}


@router.get("/audit", response_model=List[AuditRecord])
def list_audits(
    state: Optional[str] = Query(None, description="Filter by state (COMPLETE, NEEDS_REVIEW)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    outcome: Optional[str] = Query(None, description="Filter by outcome (MATCH, MISMATCH, NOT_APPLICABLE)"),
    has_discrepancy: Optional[bool] = Query(None, description="Filter by presence of discrepancies"),
    mismatch_only: bool = Query(False, description="Filter only records with confirmed discrepancies"),
    hitl_only: bool = Query(False, description="Filter only records needing human review"),
    store: AuditStore = Depends(get_audit_store),
):
    """Query audit records with optional filters (API-AUD-001)."""
    target_state = "NEEDS_REVIEW" if hitl_only else state
    target_has_disc = True if mismatch_only else has_discrepancy

    records = store.list(
        state=target_state,
        category=category,
        outcome=outcome,
        has_discrepancy=target_has_disc,
    )
    return records


_legacy_cache: Optional[Dict[str, Any]] = None


def _get_legacy_record(email_id: str) -> Optional[Dict[str, Any]]:
    global _legacy_cache
    if _legacy_cache is None:
        p = Path("audit_report.json")
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                _legacy_cache = {r.get("email_id"): r for r in data if isinstance(r, dict)}
            except Exception:
                _legacy_cache = {}
        else:
            _legacy_cache = {}
    return _legacy_cache.get(email_id)


@router.get("/audit/{email_id}")
def get_single_audit(email_id: str, store: AuditStore = Depends(get_audit_store)):
    """Retrieve full detail for a single AuditRecord (API-AUD-002, API-AUD-003)."""
    rec = store.get(email_id)
    if rec is not None:
        return rec

    legacy_rec = _get_legacy_record(email_id)
    if legacy_rec is not None:
        return legacy_rec

    return JSONResponse(
        status_code=404,
        content=ErrorResponse(
            code="RECORD_NOT_FOUND",
            message=f"Audit record for email '{email_id}' not found",
            details=[f"Email ID '{email_id}' does not exist in store"],
            retryable=False,
        ).model_dump(),
    )


@router.post("/audit/{email_id}/review", response_model=AuditRecord)
def submit_human_review(
    email_id: str,
    update: ReviewUpdate,
    store: AuditStore = Depends(get_audit_store),
    service: ReviewService = Depends(get_review_service),
):
    """Submit human review update with optimistic concurrency control (API-REV-001/002/003, DC-07)."""
    rec = store.get(email_id)
    if rec is None:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                code="RECORD_NOT_FOUND",
                message=f"Audit record for email '{email_id}' not found",
                details=[f"Email ID '{email_id}' does not exist in store"],
                retryable=False,
            ).model_dump(),
        )

    try:
        updated_rec = service.apply_review(rec, update)
        store.save(updated_rec)
        return updated_rec
    except RevisionConflictError as e:
        return JSONResponse(
            status_code=409,
            content=ErrorResponse(
                code="REVISION_CONFLICT",
                message=f"Revision conflict: current revision is {e.current_revision}, but expected {e.expected_revision}",
                details=[f"current_revision={e.current_revision}", f"expected_revision={e.expected_revision}"],
                retryable=False,
            ).model_dump(),
        )
    except ValueError as e:
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                code="UNPROCESSABLE_REVIEW",
                message=str(e),
                details=[str(e)],
                retryable=False,
            ).model_dump(),
        )


@router.post("/verify", deprecated=True)
def verify_dynamic_text(
    req: DynamicVerifyRequest,
    response: Response,
):
    """Dynamically audit an SI vs draft BL in real-time (deprecated compatibility shim for T12-04)."""
    response.headers["Warning"] = '299 - "POST /verify is deprecated. Use GET /audit or human review endpoints instead."'
    response.headers["Deprecated"] = "true"
    return rule_based_compare_audit(
        email_id=req.email_id,
        si_text=req.si_text,
        bl_text=req.bl_text,
    )


@router.get("/submission")
def get_submission(store: AuditStore = Depends(get_audit_store)):
    """Export competition submission format or block if cases require review (T12 HTTP delegation shell).
    
    Delegation architecture:
    GET /submission -> (delegates to EvaluationAdapter / ExportService in T13).
    Pending T13-01/02, serves as the HTTP shell delegating to legacy exporter.
    """
    records = store.list()
    if not records:
        raise HTTPException(status_code=404, detail="No audit records found. Run pipeline first.")

    unresolved = [r.email_id for r in records if r.state == "NEEDS_REVIEW"]
    if unresolved:
        return JSONResponse(
            status_code=409,
            content=ErrorResponse(
                code="EXPORT_BLOCKED",
                message="Export blocked: one or more cases require human review",
                details=[f"Unresolved email: {eid}" for eid in unresolved],
                retryable=False,
                blocking_emails=unresolved,
            ).model_dump(),
        )

    submission = {r.email_id: audit_record_to_competition_dict(r) for r in records}
    return submission
