import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.pipeline.schema import AuditOutputRecord, Discrepancy, HITLEscalation
from src.pipeline.stage3_compare import rule_based_compare_audit

app = FastAPI(
    title="Shipping Document Verification & Audit API",
    description="Production-grade AI Shipping Document Verification Engine featuring Zero False Alarms, Strict Golden SI Anchoring, and HITL Fallback.",
    version="1.0.0",
)

# Enable CORS for GitHub Pages frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = Path(__file__).resolve().parent
AUDIT_FILE = DATA_DIR / "audit_report.json"
SUBMISSION_FILE = DATA_DIR / "submission.json"


def get_cached_audits() -> List[Dict[str, Any]]:
    if AUDIT_FILE.exists():
        return json.loads(AUDIT_FILE.read_text(encoding="utf-8"))
    return []


def get_cached_submission() -> Dict[str, Any]:
    if SUBMISSION_FILE.exists():
        return json.loads(SUBMISSION_FILE.read_text(encoding="utf-8"))
    return {}


class DynamicVerifyRequest(BaseModel):
    email_id: str = "test_request"
    si_text: str = Field(..., description="Raw text of the Shipping Instruction (SI)")
    bl_text: str = Field(..., description="Raw text of the draft Bill of Lading (BL)")


@app.get("/")
def root():
    audits = get_cached_audits()
    categories = {}
    mismatches = 0
    hitl_count = 0
    for a in audits:
        cat = a.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1
        if a.get("mismatch_detected"):
            mismatches += 1
        if a.get("hitl_escalation", {}).get("needed"):
            hitl_count += 1

    return {
        "service": "SDOC Shipping Document Verification Engine",
        "status": "operational",
        "architecture": "LLM-First & Semantic Normalization Engine",
        "total_audited_emails": len(audits),
        "discrepancies_detected": mismatches,
        "hitl_escalations": hitl_count,
        "categories_breakdown": categories,
        "docs_url": "/docs",
        "endpoints": {
            "all_audits": "/audit",
            "single_audit": "/audit/{email_id}",
            "competition_submission": "/submission",
            "dynamic_verify": "/verify",
            "health": "/health",
        },
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/audit", response_model=List[AuditOutputRecord])
def get_all_audits(
    category: Optional[str] = Query(None, description="Filter by category"),
    mismatch_only: bool = Query(False, description="Filter only records with discrepancies"),
    hitl_only: bool = Query(False, description="Filter only records needing human review"),
):
    audits = get_cached_audits()
    results = []
    for a in audits:
        if category and a.get("category") != category:
            continue
        if mismatch_only and not a.get("mismatch_detected"):
            continue
        if hitl_only and not a.get("hitl_escalation", {}).get("needed"):
            continue
        results.append(a)
    return results


@app.get("/audit/{email_id}", response_model=AuditOutputRecord)
def get_single_audit(email_id: str):
    audits = get_cached_audits()
    for a in audits:
        if a.get("email_id") == email_id:
            return a
    raise HTTPException(status_code=404, detail=f"Email ID '{email_id}' not found.")


@app.get("/submission")
def get_competition_submission():
    sub = get_cached_submission()
    if not sub:
        raise HTTPException(status_code=404, detail="submission.json not found. Run pipeline first.")
    return sub


@app.post("/verify", response_model=AuditOutputRecord)
def verify_documents(req: DynamicVerifyRequest):
    """Dynamically audit an SI vs draft BL in real time using the 4 Golden Secrets."""
    return rule_based_compare_audit(
        email_id=req.email_id,
        si_text=req.si_text,
        bl_text=req.bl_text,
    )
