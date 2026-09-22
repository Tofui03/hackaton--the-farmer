from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import app
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


def test_e2e_002_clean_sibl_match_lifecycle(e2e_env):
    """E2E-002: Clean SI/BL match across all 7 fields -> COMPLETE / MATCH -> clean scorecard."""
    client, store, orchestrator = e2e_env

    email = EmailRecord(
        email_id="e2e_002_match",
        sender="shipper@example.com",
        subject="Booking SI vs Draft BL cross check",
        body="Please compare attached SI and Draft BL.",
        attachments=[
            AttachmentReference(document_id="e2e_002_SI.txt", path="e2e_002_SI.txt"),
            AttachmentReference(document_id="e2e_002_BL.txt", path="e2e_002_BL.txt"),
        ],
    )
    doc_texts = {
        "e2e_002_SI.txt": DOC_CLEAN_SI,
        "e2e_002_BL.txt": DOC_CLEAN_BL,
    }

    rec = orchestrator.process_email(email, document_texts=doc_texts)

    assert rec.email_id == "e2e_002_match"
    assert rec.state == "COMPLETE"
    assert rec.outcome == "MATCH"
    assert rec.mismatch_detected is False
    assert rec.result_summary == "No mismatch detected"
    assert len(rec.discrepancies) == 0
    assert rec.review is None

    # Check via REST API
    resp = client.get("/audit/e2e_002_match")
    assert resp.status_code == 200
    data = resp.json()
    assert data["outcome"] == "MATCH"
    assert data["mismatch_detected"] is False
    assert len(data["discrepancies"]) == 0

    # Check via Submission Export
    sub_resp = client.get("/submission")
    assert sub_resp.status_code == 200
    sub_data = sub_resp.json()
    assert sub_data["e2e_002_match"]["status"] == "OK"
    assert sub_data["e2e_002_match"]["has_defect"] is False
    assert sub_data["e2e_002_match"]["defect_fields"] == []


def test_e2e_003_single_field_mismatch_lifecycle(e2e_env):
    """E2E-003: Single mismatch (container_count: 2 vs 3) -> COMPLETE / MISMATCH -> defect_fields = ['container_count']."""
    client, store, orchestrator = e2e_env

    bl_diff_count = DOC_CLEAN_BL.replace("Container Count: 2", "Container Count: 3")
    email = EmailRecord(
        email_id="e2e_003_disc",
        sender="shipper@example.com",
        subject="Booking SI vs Draft BL cross check",
        body="Please compare attached SI and Draft BL.",
        attachments=[
            AttachmentReference(document_id="e2e_003_SI.txt", path="e2e_003_SI.txt"),
            AttachmentReference(document_id="e2e_003_BL.txt", path="e2e_003_BL.txt"),
        ],
    )
    doc_texts = {
        "e2e_003_SI.txt": DOC_CLEAN_SI,
        "e2e_003_BL.txt": bl_diff_count,
    }

    rec = orchestrator.process_email(email, document_texts=doc_texts)

    assert rec.email_id == "e2e_003_disc"
    assert rec.state == "COMPLETE"
    assert rec.outcome == "MISMATCH"
    assert rec.mismatch_detected is True
    assert len(rec.discrepancies) == 1
    assert rec.discrepancies[0].field == "container_count"
    assert rec.discrepancies[0].si_value == 2
    assert rec.discrepancies[0].bl_value == 3

    # Check via REST API
    resp = client.get("/audit/e2e_003_disc")
    assert resp.status_code == 200
    data = resp.json()
    assert data["outcome"] == "MISMATCH"
    assert data["mismatch_detected"] is True
    assert len(data["discrepancies"]) == 1
    assert data["discrepancies"][0]["field"] == "container_count"

    # Check via Submission Export
    sub_resp = client.get("/submission")
    assert sub_resp.status_code == 200
    sub_data = sub_resp.json()
    assert sub_data["e2e_003_disc"]["status"] == "MISMATCH"
    assert sub_data["e2e_003_disc"]["has_defect"] is True
    assert sub_data["e2e_003_disc"]["defect_fields"] == ["container_count"]


def test_e2e_004_multiple_field_mismatches_lifecycle(e2e_env):
    """E2E-004: Multiple mismatches (shipper and gross_weight_kg) -> side-by-side diffs with evidence links intact."""
    client, store, orchestrator = e2e_env

    bl_multi_diff = DOC_CLEAN_BL.replace(
        "Shipper: ACME EXPORTS LTD 123 INDUSTRIAL WAY SINGAPORE 068896",
        "Shipper: DIFFERENT SHIPPER PTE LTD 99 OCEAN AVE SINGAPORE",
    ).replace(
        "Gross Weight: 22,000 KGS",
        "Gross Weight: 25,500 KGS",
    )

    email = EmailRecord(
        email_id="e2e_004_multi",
        sender="shipper@example.com",
        subject="Booking SI vs Draft BL cross check",
        body="Please compare attached SI and Draft BL.",
        attachments=[
            AttachmentReference(document_id="e2e_004_SI.txt", path="e2e_004_SI.txt"),
            AttachmentReference(document_id="e2e_004_BL.txt", path="e2e_004_BL.txt"),
        ],
    )
    doc_texts = {
        "e2e_004_SI.txt": DOC_CLEAN_SI,
        "e2e_004_BL.txt": bl_multi_diff,
    }

    rec = orchestrator.process_email(email, document_texts=doc_texts)

    assert rec.email_id == "e2e_004_multi"
    assert rec.state == "COMPLETE"
    assert rec.outcome == "MISMATCH"
    assert rec.mismatch_detected is True
    assert len(rec.discrepancies) == 2

    diff_fields = {d.field for d in rec.discrepancies}
    assert diff_fields == {"shipper", "gross_weight_kg"}

    # Evidence provenance intact
    evidence_ids = {e.evidence_id for e in rec.evidence}
    for extraction in rec.extractions:
        for field_name in ("shipper", "gross_weight_kg"):
            field_data = extraction.fields[field_name]
            cand = field_data.candidates[field_data.selected_candidate]
            for ev_id in cand.evidence_ids:
                assert ev_id in evidence_ids

    # Check via REST API
    resp = client.get("/audit/e2e_004_multi")
    assert resp.status_code == 200
    data = resp.json()
    assert data["outcome"] == "MISMATCH"
    assert len(data["discrepancies"]) == 2

    # Check via Submission Export
    sub_resp = client.get("/submission")
    assert sub_resp.status_code == 200
    sub_data = sub_resp.json()
    assert sub_data["e2e_004_multi"]["status"] == "MISMATCH"
    assert sub_data["e2e_004_multi"]["has_defect"] is True
    assert sorted(sub_data["e2e_004_multi"]["defect_fields"]) == ["gross_weight_kg", "shipper"]
