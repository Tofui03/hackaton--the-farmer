from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import app
from src.api.routes import get_audit_store, get_orchestrator, set_audit_store
from src.hitl.escalation_engine import EscalationEngine
from src.models.audit import AuditRecord
from src.models.evidence import FieldEvidence
from src.models.extraction import ExtractedField
from src.models.ingestion import AttachmentReference, EmailRecord
from src.models.review import (
    FieldCorrection,
    ReviewAction,
    ReviewUpdate,
    RoleCorrection,
)
from src.pipeline.orchestrator import PipelineOrchestrator
from src.store.audit_store import AuditStore


DOC_SAMPLE_SI = """
Shipper: ACME EXPORTS LTD 123 INDUSTRIAL WAY SINGAPORE 068896
Consignee: GLOBAL IMPORTERS LLC 456 HARBOR ROAD ROTTERDAM NETHERLANDS
Notify Party: SAME AS CONSIGNEE
Port of Loading: SHANGHAI (CNSHA)
Port of Discharge: ROTTERDAM (NLRTM)
Container Count: 2
Gross Weight: 22,000 KGS
Description: ELECTRONIC GOODS
"""

DOC_SAMPLE_BL = """
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


def test_e2e_009_human_corrects_conflicting_field_candidate(e2e_env):
    """E2E-009: Operator corrects conflicting gross weight -> re-normalizes -> re-matches -> revision=2 -> COMPLETE."""
    client, store, orchestrator = e2e_env

    # 1. Create case where gross weight in SI is missing/conflicting
    email = EmailRecord(
        email_id="e2e_009_corr",
        sender="shipper@example.com",
        subject="Booking verification",
        body="Please compare attached SI and Draft BL.",
        attachments=[
            AttachmentReference(document_id="e2e_009_SI.txt", path="e2e_009_SI.txt"),
            AttachmentReference(document_id="e2e_009_BL.txt", path="e2e_009_BL.txt"),
        ],
    )
    si_missing_wt = DOC_SAMPLE_SI.replace("Gross Weight: 22,000 KGS", "")
    rec = orchestrator.process_email(
        email,
        document_texts={
            "e2e_009_SI.txt": si_missing_wt,
            "e2e_009_BL.txt": DOC_SAMPLE_BL,
        },
    )

    assert rec.state == "NEEDS_REVIEW"
    assert rec.revision == 1
    assert rec.review is not None

    # 2. Operator submits correction via review endpoint
    ev_id = f"ev_corr_e2e_009"
    update_payload = {
        "review_id": rec.review.review_id,
        "expected_revision": 1,
        "actor_id": "reviewer_sarah",
        "action": "CORRECT",
        "rationale": "Verified correct weight on scale ticket",
        "corrections": [
            {
                "document_id": "e2e_009_SI.txt",
                "field": "gross_weight_kg",
                "raw_value": "22,000 KGS",
                "evidence_ids": [ev_id],
                "rationale": "Verified correct weight on scale ticket",
            }
        ],
        "added_evidence": [
            {
                "evidence_id": ev_id,
                "source_type": "document",
                "source_id": "e2e_009_SI.txt",
                "kind": "text_span",
                "quote": "22,000 KGS",
            }
        ],
    }

    resp = client.post("/audit/e2e_009_corr/review", json=update_payload)
    assert resp.status_code == 200
    updated = AuditRecord.model_validate(resp.json())

    # 3. Assert recomputed to revision 2, COMPLETE, MATCH
    assert updated.revision == 2
    assert updated.previous_revision == 1
    assert updated.state == "COMPLETE"
    assert updated.outcome == "MATCH"
    assert updated.mismatch_detected is False
    assert len(updated.discrepancies) == 0


def test_e2e_010_human_resolves_ambiguous_classification(e2e_env):
    """E2E-010: Case in HITL with category = null -> operator resolves category -> case updates cleanly."""
    client, store, orchestrator = e2e_env

    # 1. Create email with ambiguous intent
    email = EmailRecord(
        email_id="e2e_010_ambig_cls",
        sender="partner@sea.com",
        subject="Booking inquiry and paperwork update",
        body="Attaching some paperwork for reference.",
        attachments=[
            AttachmentReference(document_id="e2e_010_SI.txt", path="e2e_010_SI.txt"),
            AttachmentReference(document_id="e2e_010_BL.txt", path="e2e_010_BL.txt"),
        ],
    )
    rec = orchestrator.process_email(
        email,
        document_texts={
            "e2e_010_SI.txt": DOC_SAMPLE_SI,
            "e2e_010_BL.txt": DOC_SAMPLE_BL,
        },
    )

    assert rec.state == "NEEDS_REVIEW"
    assert rec.classification.category is None
    assert rec.review is not None
    assert rec.revision == 1

    # 2. Operator reviews and sets category to new_shipping_instruction
    ev_cls_corr = "ev_cls_resolved"
    update_payload = {
        "review_id": rec.review.review_id,
        "expected_revision": 1,
        "actor_id": "reviewer_bob",
        "action": "CORRECT",
        "rationale": "Customer submitted new shipping instruction",
        "category": "new_shipping_instruction",
        "classification_evidence_ids": [ev_cls_corr],
        "added_evidence": [
            {
                "evidence_id": ev_cls_corr,
                "source_type": "email",
                "source_id": "e2e_010_ambig_cls",
                "kind": "text_span",
                "quote": "paperwork for reference",
            }
        ],
    }

    resp = client.post("/audit/e2e_010_ambig_cls/review", json=update_payload)
    assert resp.status_code == 200
    updated = AuditRecord.model_validate(resp.json())

    assert updated.revision == 2
    assert updated.state == "COMPLETE"
    assert updated.outcome == "NOT_APPLICABLE"
    assert updated.classification.category == "new_shipping_instruction"


def test_e2e_011_human_resolves_ambiguous_document_roles(e2e_env):
    """E2E-011: Operator resolves ambiguous document roles -> assigns roles to documents."""
    client, store, orchestrator = e2e_env

    # 1. Create a case where attachments have ambiguous names (e.g. doc_a.txt, doc_b.txt)
    email = EmailRecord(
        email_id="e2e_011_roles",
        sender="shipper@cargo.com",
        subject="Compare SI and Draft BL",
        body="Please compare attached draft BL and SI.",
        attachments=[
            AttachmentReference(document_id="doc_a.txt", path="doc_a.txt"),
            AttachmentReference(document_id="doc_b.txt", path="doc_b.txt"),
        ],
    )
    rec = orchestrator.process_email(
        email,
        document_texts={
            "doc_a.txt": DOC_SAMPLE_SI,
            "doc_b.txt": DOC_SAMPLE_BL,
        },
    )

    assert rec.state == "NEEDS_REVIEW"
    assert rec.review is not None
    assert rec.revision == 1

    # 2. Operator assigns roles: doc_a.txt -> SI, doc_b.txt -> BL
    ev_a = "ev_role_a"
    ev_b = "ev_role_b"
    update_payload = {
        "review_id": rec.review.review_id,
        "expected_revision": 1,
        "actor_id": "reviewer_roles",
        "action": "CORRECT",
        "rationale": "Identified doc_a as SI and doc_b as Draft BL based on layout",
        "role_corrections": [
            {
                "document_id": "doc_a.txt",
                "assigned_role": "SI",
                "evidence_ids": [ev_a],
                "rationale": "Header matches Shipping Instruction format",
            },
            {
                "document_id": "doc_b.txt",
                "assigned_role": "BL",
                "evidence_ids": [ev_b],
                "rationale": "Header matches Bill of Lading format",
            },
        ],
        "added_evidence": [
            {
                "evidence_id": ev_a,
                "source_type": "document",
                "source_id": "doc_a.txt",
                "kind": "text_span",
                "quote": "Shipper: ACME EXPORTS LTD",
            },
            {
                "evidence_id": ev_b,
                "source_type": "document",
                "source_id": "doc_b.txt",
                "kind": "text_span",
                "quote": "Shipper: ACME EXPORTS LTD",
            },
        ],
    }

    resp = client.post("/audit/e2e_011_roles/review", json=update_payload)
    assert resp.status_code == 200
    updated = AuditRecord.model_validate(resp.json())

    assert updated.revision == 2
    assert updated.previous_revision == 1
    # Document roles are now assigned
    doc_roles = {d.document_id: d.role for d in updated.documents}
    assert doc_roles.get("doc_a.txt") == "SI"
    assert doc_roles.get("doc_b.txt") == "BL"


def test_e2e_012_concurrency_collision_rejection_modal_flow(e2e_env):
    """E2E-012: Concurrency collision -> Operator A submits on stale revision -> HTTP 409 Conflict."""
    client, store, orchestrator = e2e_env

    # 1. Create a case in review state at revision 1
    email = EmailRecord(
        email_id="e2e_012_col",
        sender="shipper@example.com",
        subject="Review required case",
        body="Please verify documents.",
        attachments=[
            AttachmentReference(document_id="e2e_012_SI.txt", path="e2e_012_SI.txt"),
            AttachmentReference(document_id="e2e_012_BL.txt", path="e2e_012_BL.txt"),
        ],
    )
    rec = orchestrator.process_email(
        email,
        document_texts={
            "e2e_012_SI.txt": DOC_SAMPLE_SI.replace("Gross Weight: 22,000 KGS", ""),
            "e2e_012_BL.txt": DOC_SAMPLE_BL,
        },
    )
    assert rec.revision == 1
    review_id = rec.review.review_id

    # 2. Operator B submits an update first, advancing revision to 2
    ev_b = "ev_op_b"
    update_b = {
        "review_id": review_id,
        "expected_revision": 1,
        "actor_id": "operator_b",
        "action": "CORRECT",
        "rationale": "Operator B resolved weight",
        "corrections": [
            {
                "document_id": "e2e_012_SI.txt",
                "field": "gross_weight_kg",
                "raw_value": "22,000 KGS",
                "evidence_ids": [ev_b],
                "rationale": "Resolved by B",
            }
        ],
        "added_evidence": [
            {
                "evidence_id": ev_b,
                "source_type": "document",
                "source_id": "e2e_012_SI.txt",
                "kind": "text_span",
                "quote": "22,000 KGS",
            }
        ],
    }
    resp_b = client.post("/audit/e2e_012_col/review", json=update_b)
    assert resp_b.status_code == 200
    assert resp_b.json()["revision"] == 2

    # 3. Operator A attempts to submit using stale expected_revision=1
    ev_a = "ev_op_a"
    update_a = {
        "review_id": review_id,
        "expected_revision": 1,  # Stale revision!
        "actor_id": "operator_a",
        "action": "CORRECT",
        "rationale": "Operator A attempt on stale data",
        "corrections": [
            {
                "document_id": "e2e_012_SI.txt",
                "field": "gross_weight_kg",
                "raw_value": "22,500 KGS",
                "evidence_ids": [ev_a],
                "rationale": "Resolved by A",
            }
        ],
        "added_evidence": [
            {
                "evidence_id": ev_a,
                "source_type": "document",
                "source_id": "e2e_012_SI.txt",
                "kind": "text_span",
                "quote": "22,500 KGS",
            }
        ],
    }
    resp_a = client.post("/audit/e2e_012_col/review", json=update_a)

    # 4. HTTP 409 Conflict returned
    assert resp_a.status_code == 409
    err = resp_a.json()
    assert err["code"] == "REVISION_CONFLICT"
    assert "current revision is 2" in err["message"]
    assert "expected 1" in err["message"]
