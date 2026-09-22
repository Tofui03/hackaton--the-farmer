from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import app
from src.adapters.evaluation_adapter import ExportService
from src.api.routes import get_audit_store, get_orchestrator, set_audit_store
from src.models.ingestion import AttachmentReference, EmailRecord
from src.pipeline.orchestrator import PipelineOrchestrator
from src.store.audit_store import AuditStore


@pytest.fixture
def e2e_env():
    """Isolated test environment with dedicated AuditStore, PipelineOrchestrator, and TestClient."""
    store = AuditStore()
    orchestrator = PipelineOrchestrator(audit_store=store)

    app.dependency_overrides[get_audit_store] = lambda: store
    app.dependency_overrides[get_orchestrator] = lambda: orchestrator
    set_audit_store(store)

    client = TestClient(app)
    yield client, store, orchestrator

    app.dependency_overrides.clear()
    store.clear()


def test_e2e_001_non_comparison_email_lifecycle(e2e_env):
    """E2E-001 (Non-Comparison Email Lifecycle / FR-004):
    Ingest email -> Stage 1 classifies as invoice_query -> Pipeline halts verification ->
    Case marked COMPLETE / NOT_APPLICABLE -> Viewable in queue -> Export maps to INVOICE_QUERY.
    """
    client, store, orchestrator = e2e_env

    # 1. Ingest email representing an invoice query
    email = EmailRecord(
        email_id="e2e_001_inv",
        sender="accounting@client.com",
        subject="Invoice Query - Discrepancy in THC fees for Inv #99281",
        body="Dear Finance, please provide clarification on terminal handling charge on invoice 99281.",
        attachments=[
            AttachmentReference(document_id="invoice_99281.pdf", path="invoice_99281.pdf")
        ],
    )

    # 2. Pipeline processing halts verification and marks NOT_APPLICABLE
    audit_rec = orchestrator.process_email(email)

    assert audit_rec.email_id == "e2e_001_inv"
    assert audit_rec.classification.category == "invoice_query"
    assert audit_rec.state == "COMPLETE"
    assert audit_rec.outcome == "NOT_APPLICABLE"
    assert audit_rec.mismatch_detected is None
    assert "Non-comparison category" in audit_rec.result_summary
    assert audit_rec.review is None
    assert len(audit_rec.extractions) == 0
    assert len(audit_rec.discrepancies) == 0

    # 3. Verify record visibility in API queue
    queue_resp = client.get("/audit?outcome=NOT_APPLICABLE")
    assert queue_resp.status_code == 200
    queue_records = queue_resp.json()
    assert any(r["email_id"] == "e2e_001_inv" for r in queue_records)

    detail_resp = client.get("/audit/e2e_001_inv")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["classification"]["category"] == "invoice_query"
    assert detail["outcome"] == "NOT_APPLICABLE"

    # 4. Evaluation export maps to official INVOICE_QUERY enum
    export_resp = client.get("/submission")
    assert export_resp.status_code == 200
    submission = export_resp.json()
    assert "e2e_001_inv" in submission
    sub_entry = submission["e2e_001_inv"]
    assert sub_entry["category"] == "INVOICE_QUERY"
    assert sub_entry["status"] == "OK"
    assert sub_entry["has_defect"] is False
    assert sub_entry["defect_fields"] == []
    assert sub_entry["review_reason"] is None
