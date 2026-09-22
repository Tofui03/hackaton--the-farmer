from __future__ import annotations

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app import app
from src.adapters.evaluation_adapter import EvaluationAdapter
from src.api.routes import get_audit_store, get_orchestrator, set_audit_store
from src.models.ingestion import AttachmentReference, EmailRecord
from src.pipeline.orchestrator import PipelineOrchestrator
from src.store.audit_store import AuditStore


DOC_CLEAN_SI = """
Shipper: ACME EXPORTS LTD 123 INDUSTRIAL WAY SINGAPORE 068896
Consignee: GLOBAL IMPORTERS LLC 456 HARBOR ROAD ROTTERDAM NETHERLANDS
Notify Party: SAME AS CONSIGNEE
Port of Loading: SHANGHAI (CNSHA)
Port of Discharge: ROTTERDAM (NLRTM)
Container Count: 2
Gross Weight: 22,000 KGS
Description: ELECTRONIC GOODS
"""

DOC_CLEAN_BL = """
Shipper: ACME EXPORTS LTD 123 INDUSTRIAL WAY SINGAPORE 068896
Consignee: GLOBAL IMPORTERS LLC 456 HARBOR ROAD ROTTERDAM NETHERLANDS
Notify Party: SAME AS CONSIGNEE
Port of Loading: SHANGHAI (CNSHA)
Port of Discharge: ROTTERDAM (NLRTM)
Container Count: 2
Gross Weight: 22,000 KGS
Description: ELECTRONIC GOODS
"""


@pytest.fixture
def e2e_env():
    store = AuditStore()
    orchestrator = PipelineOrchestrator(audit_store=store)

    app.dependency_overrides[get_audit_store] = lambda: store
    app.dependency_overrides[get_orchestrator] = lambda: orchestrator
    set_audit_store(store)

    client = TestClient(app)
    yield client, store, orchestrator

    app.dependency_overrides.clear()
    store.clear()


def test_e2e_015_valid_official_evaluation_export_lifecycle(e2e_env):
    """E2E-015: All batch cases COMPLETE -> GET /submission -> generates valid submission matching official schema."""
    client, store, orchestrator = e2e_env

    # 1. Ingest Case 1: Clean Match
    email1 = EmailRecord(
        email_id="e2e_015_case1",
        sender="shipper@example.com",
        subject="Booking SI vs Draft BL check",
        body="Please compare attached SI and Draft BL.",
        attachments=[
            AttachmentReference(document_id="e2e_015_1_SI.txt", path="e2e_015_1_SI.txt"),
            AttachmentReference(document_id="e2e_015_1_BL.txt", path="e2e_015_1_BL.txt"),
        ],
    )
    rec1 = orchestrator.process_email(
        email1,
        document_texts={
            "e2e_015_1_SI.txt": DOC_CLEAN_SI,
            "e2e_015_1_BL.txt": DOC_CLEAN_BL,
        },
    )
    assert rec1.state == "COMPLETE"

    # 2. Ingest Case 2: Non-comparison (invoice query)
    email2 = EmailRecord(
        email_id="e2e_015_case2",
        sender="billing@example.com",
        subject="Invoice Query #10293",
        body="Clarification needed for invoice #10293 charges.",
        attachments=[],
    )
    rec2 = orchestrator.process_email(email2)
    assert rec2.state == "COMPLETE"

    # 3. Both cases in store are COMPLETE -> GET /submission succeeds with HTTP 200
    resp = client.get("/submission")
    assert resp.status_code == 200
    submission = resp.json()

    assert "e2e_015_case1" in submission
    assert "e2e_015_case2" in submission

    # Validate schema shape using EvaluationAdapter
    is_valid, errors = EvaluationAdapter.validate_submission_dict(
        submission, expected_email_ids=["e2e_015_case1", "e2e_015_case2"]
    )
    assert is_valid, f"Submission schema validation failed: {errors}"
    assert len(errors) == 0

    assert submission["e2e_015_case1"]["category"] == "BL_COMPARISON"
    assert submission["e2e_015_case1"]["status"] == "OK"
    assert submission["e2e_015_case1"]["has_defect"] is False
    assert submission["e2e_015_case1"]["defect_fields"] == []

    assert submission["e2e_015_case2"]["category"] == "INVOICE_QUERY"
    assert submission["e2e_015_case2"]["status"] == "OK"
    assert submission["e2e_015_case2"]["has_defect"] is False
    assert submission["e2e_015_case2"]["defect_fields"] == []


def test_e2e_016_export_blocked_by_unresolved_case(e2e_env):
    """E2E-016 / DC-08: Batch has 1 case in NEEDS_REVIEW -> GET /submission blocked with HTTP 409 EXPORT_BLOCKED."""
    client, store, orchestrator = e2e_env

    # 1. Ingest Case 1: Complete match
    email1 = EmailRecord(
        email_id="e2e_016_ok",
        sender="shipper@example.com",
        subject="Booking SI vs Draft BL check",
        body="Please compare attached SI and Draft BL.",
        attachments=[
            AttachmentReference(document_id="e2e_016_1_SI.txt", path="e2e_016_1_SI.txt"),
            AttachmentReference(document_id="e2e_016_1_BL.txt", path="e2e_016_1_BL.txt"),
        ],
    )
    orchestrator.process_email(
        email1,
        document_texts={
            "e2e_016_1_SI.txt": DOC_CLEAN_SI,
            "e2e_016_1_BL.txt": DOC_CLEAN_BL,
        },
    )

    # 2. Ingest Case 2: Incomplete / missing attachment -> NEEDS_REVIEW
    email2 = EmailRecord(
        email_id="e2e_016_blocked",
        sender="shipper@example.com",
        subject="Draft BL check against SI",
        body="Please compare draft BL with SI. Only SI attached.",
        attachments=[
            AttachmentReference(document_id="e2e_016_2_SI.txt", path="e2e_016_2_SI.txt")
        ],
    )
    rec2 = orchestrator.process_email(
        email2,
        document_texts={
            "e2e_016_2_SI.txt": DOC_CLEAN_SI,
        },
    )
    assert rec2.state == "NEEDS_REVIEW"

    # 3. Attempting GET /submission must be blocked with HTTP 409 EXPORT_BLOCKED (DC-08)
    resp = client.get("/submission")
    assert resp.status_code == 409
    err = resp.json()

    assert err["code"] == "EXPORT_BLOCKED"
    assert "e2e_016_blocked" in err["blocking_emails"]
    assert any("e2e_016_blocked" in detail for detail in err["details"])
