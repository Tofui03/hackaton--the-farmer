from __future__ import annotations

from decimal import Decimal
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app import app
from src.api.routes import get_audit_store, get_orchestrator, set_audit_store
from src.models.audit import AuditRecord, ErrorResponse
from src.models.evidence import FieldEvidence
from src.models.ingestion import AttachmentReference, EmailRecord
from src.models.review import (
    FieldCorrection,
    ReviewAction,
    ReviewUpdate,
    RoleCorrection,
)
from src.pipeline.orchestrator import PipelineOrchestrator
from src.store.audit_store import AuditStore

DOC_MATCHING_SI = """
Shipper: ACME EXPORTS LTD 123 INDUSTRIAL WAY SINGAPORE 068896
Consignee: GLOBAL IMPORTERS LLC 456 HARBOR ROAD ROTTERDAM NETHERLANDS
Notify Party: SAME AS CONSIGNEE
Port of Loading: SHANGHAI (CNSHA)
Port of Discharge: ROTTERDAM (NLRTM)
Container Count: 2
Gross Weight: 22,000 KGS
Description: ELECTRONIC GOODS
"""

DOC_MATCHING_BL = """
Shipper: ACME EXPORTS LTD 123 INDUSTRIAL WAY SINGAPORE 068896
Consignee: GLOBAL IMPORTERS LLC 456 HARBOR ROAD ROTTERDAM NETHERLANDS
Notify Party: SAME AS CONSIGNEE
Port of Loading: SHANGHAI (CNSHA)
Port of Discharge: ROTTERDAM (NLRTM)
Container Count: 2
Gross Weight: 22,000 KGS
Description: ELECTRONIC GOODS
"""


def _make_comparison_email(email_id: str) -> EmailRecord:
    return EmailRecord(
        email_id=email_id,
        sender="shipping@example.com",
        subject="Please compare SI vs Draft BL for Container Booking",
        body="Dear team, kindly verify draft BL against shipping instructions attached.",
        attachments=[
            AttachmentReference(document_id=f"{email_id}_SI.txt", path=f"{email_id}_SI.txt"),
            AttachmentReference(document_id=f"{email_id}_BL.txt", path=f"{email_id}_BL.txt"),
        ],
    )


@pytest.fixture
def test_env():
    """Isolated test environment with dedicated AuditStore and FastAPI TestClient."""
    store = AuditStore()
    orch = PipelineOrchestrator(audit_store=store)

    app.dependency_overrides[get_audit_store] = lambda: store
    app.dependency_overrides[get_orchestrator] = lambda: orch
    set_audit_store(store)

    client = TestClient(app)
    yield client, store, orch

    app.dependency_overrides.clear()
    store.clear()


# =====================================================================
# T12-01: FastAPI Router Modernization & Schema Migration (API-AUD, API-HLT)
# =====================================================================


def test_api_hlt_001_health_check(test_env):
    """API-HLT-001: GET /health returns HTTP 200 with healthy status."""
    client, _, _ = test_env
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "healthy"}


def test_api_root_dynamic_metrics_reg_003(test_env):
    """REG-003: GET / reports dynamic aggregated metrics matching AuditStore (zero hardcoding)."""
    client, store, orch = test_env

    # Empty store
    resp0 = client.get("/")
    assert resp0.status_code == 200
    data0 = resp0.json()
    assert data0["total_audited_emails"] == 0
    assert data0["discrepancies_detected"] == 0

    # Populate 1 matching record
    email1 = _make_comparison_email("email_reg003_1")
    doc_texts1 = {
        f"{email1.email_id}_SI.txt": DOC_MATCHING_SI,
        f"{email1.email_id}_BL.txt": DOC_MATCHING_BL,
    }
    orch.process_email(email1, document_texts=doc_texts1)

    resp1 = client.get("/")
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["total_audited_emails"] == 1
    assert data1["discrepancies_detected"] == 0

    # Populate 1 discrepant record
    email2 = _make_comparison_email("email_reg003_2")
    bl_disc = DOC_MATCHING_BL.replace("Gross Weight: 22,000 KGS", "Gross Weight: 25,000 KGS")
    doc_texts2 = {
        f"{email2.email_id}_SI.txt": DOC_MATCHING_SI,
        f"{email2.email_id}_BL.txt": bl_disc,
    }
    orch.process_email(email2, document_texts=doc_texts2)

    resp2 = client.get("/")
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["total_audited_emails"] == 2
    assert data2["discrepancies_detected"] == 1


def test_api_aud_001_list_with_query_filters(test_env):
    """API-AUD-001: GET /audit supports filtering by state, category, outcome, discrepancy."""
    client, store, orch = test_env

    # 1. Matching case (COMPLETE, MATCH, document_comparison, no discrepancy)
    email1 = _make_comparison_email("email_list_1")
    orch.process_email(
        email1,
        document_texts={
            f"{email1.email_id}_SI.txt": DOC_MATCHING_SI,
            f"{email1.email_id}_BL.txt": DOC_MATCHING_BL,
        },
    )

    # 2. Discrepant case (COMPLETE, MISMATCH, document_comparison, has discrepancy)
    email2 = _make_comparison_email("email_list_2")
    orch.process_email(
        email2,
        document_texts={
            f"{email2.email_id}_SI.txt": DOC_MATCHING_SI,
            f"{email2.email_id}_BL.txt": DOC_MATCHING_BL.replace("Container Count: 2", "Container Count: 5"),
        },
    )

    # 3. Inconclusive / review case (NEEDS_REVIEW)
    email3 = _make_comparison_email("email_list_3")
    orch.process_email(
        email3,
        document_texts={
            f"{email3.email_id}_SI.txt": DOC_MATCHING_SI.replace("Gross Weight: 22,000 KGS", ""),
            f"{email3.email_id}_BL.txt": DOC_MATCHING_BL,
        },
    )

    # All records
    res_all = client.get("/audit")
    assert res_all.status_code == 200
    assert len(res_all.json()) == 3

    # Filter by state=NEEDS_REVIEW
    res_nr = client.get("/audit?state=NEEDS_REVIEW")
    assert res_nr.status_code == 200
    assert len(res_nr.json()) == 1
    assert res_nr.json()[0]["email_id"] == "email_list_3"

    # Filter by hitl_only=true
    res_hitl = client.get("/audit?hitl_only=true")
    assert res_hitl.status_code == 200
    assert len(res_hitl.json()) == 1
    assert res_hitl.json()[0]["email_id"] == "email_list_3"

    # Filter by outcome=MATCH
    res_match = client.get("/audit?outcome=MATCH")
    assert res_match.status_code == 200
    assert len(res_match.json()) == 1
    assert res_match.json()[0]["email_id"] == "email_list_1"

    # Filter by mismatch_only=true
    res_mismatch = client.get("/audit?mismatch_only=true")
    assert res_mismatch.status_code == 200
    assert len(res_mismatch.json()) == 1
    assert res_mismatch.json()[0]["email_id"] == "email_list_2"


def test_api_aud_002_get_single_audit_success(test_env):
    """API-AUD-002: GET /audit/{email_id} returns full validated AuditRecord."""
    client, store, orch = test_env

    email = _make_comparison_email("email_aud002")
    orch.process_email(
        email,
        document_texts={
            f"{email.email_id}_SI.txt": DOC_MATCHING_SI,
            f"{email.email_id}_BL.txt": DOC_MATCHING_BL,
        },
    )

    resp = client.get(f"/audit/{email.email_id}")
    assert resp.status_code == 200
    data = resp.json()

    # Validate against strict Pydantic contract
    parsed = AuditRecord.model_validate(data)
    assert parsed.email_id == email.email_id
    assert parsed.state == "COMPLETE"
    assert parsed.outcome == "MATCH"
    assert parsed.mismatch_detected is False
    assert parsed.revision == 1


def test_api_aud_003_get_single_audit_not_found(test_env):
    """API-AUD-003: GET /audit/{email_id} returns HTTP 404 with structured ErrorResponse."""
    client, store, _ = test_env

    resp = client.get("/audit/email_completely_nonexistent")
    assert resp.status_code == 404
    err = resp.json()
    assert err["code"] == "RECORD_NOT_FOUND"
    assert "not found" in err["message"].lower()
    assert err["retryable"] is False


# =====================================================================
# T12-02: Human Review Endpoint (POST /audit/{email_id}/review, FR-016)
# =====================================================================


def test_api_rev_001_submit_valid_review_increment_revision(test_env):
    """API-REV-001: Submitting review increments revision to N+1 and persists to store."""
    client, store, orch = test_env

    # Create review case with missing weight
    email = _make_comparison_email("email_rev001")
    si_missing_wt = DOC_MATCHING_SI.replace("Gross Weight: 22,000 KGS", "")
    rec = orch.process_email(
        email,
        document_texts={
            f"{email.email_id}_SI.txt": si_missing_wt,
            f"{email.email_id}_BL.txt": DOC_MATCHING_BL,
        },
    )
    assert rec.state == "NEEDS_REVIEW"
    assert rec.revision == 1

    ev_id = f"ev_op_wt_{email.email_id}"
    update_payload = {
        "review_id": rec.review.review_id,
        "actor_id": "operator_42",
        "action": "CORRECT",
        "rationale": "Operator verified weight on physical manifest",
        "expected_revision": 1,
        "corrections": [
            {
                "document_id": f"{email.email_id}_SI.txt",
                "field": "gross_weight_kg",
                "raw_value": "22,000 KGS",
                "evidence_ids": [ev_id],
                "rationale": "Operator verified weight on physical manifest",
            }
        ],
        "added_evidence": [
            {
                "evidence_id": ev_id,
                "source_type": "document",
                "source_id": f"{email.email_id}_SI.txt",
                "kind": "text_span",
                "quote": "22,000 KGS",
            }
        ],
    }

    resp = client.post(f"/audit/{email.email_id}/review", json=update_payload)
    assert resp.status_code == 200
    updated = AuditRecord.model_validate(resp.json())

    assert updated.revision == 2
    assert updated.previous_revision == 1
    assert updated.state == "COMPLETE"
    assert updated.outcome == "MATCH"
    assert updated.mismatch_detected is False

    # Store verification
    stored = store.get(email.email_id)
    assert stored.revision == 2
    assert stored.state == "COMPLETE"


def test_api_rev_003_and_hitl_rev_001_rejects_malformed_and_boolean_overrides(test_env):
    """API-REV-003 & HITL-REV-001: Rejects unknown fields and direct mismatch_detected overrides with HTTP 422."""
    client, store, orch = test_env

    email = _make_comparison_email("email_rev003")
    rec = orch.process_email(
        email,
        document_texts={
            f"{email.email_id}_SI.txt": DOC_MATCHING_SI,
            f"{email.email_id}_BL.txt": DOC_MATCHING_BL,
        },
    )

    # 1. Attempt direct boolean override (REG-012 / HITL-REV-001)
    forbidden_payload = {
        "review_id": "rev_test",
        "actor_id": "operator_42",
        "action": "CONFIRM",
        "rationale": "Attempting direct boolean override",
        "expected_revision": 1,
        "mismatch_detected": False,  # Forbidden!
    }
    resp1 = client.post(f"/audit/{email.email_id}/review", json=forbidden_payload)
    assert resp1.status_code == 422

    # 2. Unknown field injection (extra = "forbid")
    unknown_field_payload = {
        "review_id": "rev_test",
        "actor_id": "operator_42",
        "action": "CONFIRM",
        "rationale": "Attempting unknown field injection",
        "expected_revision": 1,
        "hallucinated_property": "not_allowed",
    }
    resp2 = client.post(f"/audit/{email.email_id}/review", json=unknown_field_payload)
    assert resp2.status_code == 422


def test_hitl_rev_002_gross_weight_correction_recomputes_complete(test_env):
    """HITL-REV-002: Operator corrects gross weight; normalizer & comparator re-run deterministically."""
    client, store, orch = test_env

    email = _make_comparison_email("email_hitl002")
    # BL weight is 22,000 KGS, SI weight initially missing
    rec = orch.process_email(
        email,
        document_texts={
            f"{email.email_id}_SI.txt": DOC_MATCHING_SI.replace("Gross Weight: 22,000 KGS", "Gross Weight: UNREADABLE"),
            f"{email.email_id}_BL.txt": DOC_MATCHING_BL,
        },
    )
    assert rec.state == "NEEDS_REVIEW"

    ev_id = f"ev_hitl002_{email.email_id}"
    update = {
        "review_id": rec.review.review_id,
        "actor_id": "operator_1",
        "action": "CORRECT",
        "rationale": "Manual review found 22 MT in special instructions table",
        "expected_revision": 1,
        "corrections": [
            {
                "document_id": f"{email.email_id}_SI.txt",
                "field": "gross_weight_kg",
                "raw_value": "22 MT",  # 22 MT converts to 22,000 KG
                "evidence_ids": [ev_id],
                "rationale": "Manual review found 22 MT in special instructions table",
            }
        ],
        "added_evidence": [
            {
                "evidence_id": ev_id,
                "source_type": "document",
                "source_id": f"{email.email_id}_SI.txt",
                "kind": "text_span",
                "quote": "22 MT",
            }
        ],
    }

    resp = client.post(f"/audit/{email.email_id}/review", json=update)
    assert resp.status_code == 200
    res = AuditRecord.model_validate(resp.json())

    assert res.state == "COMPLETE"
    assert res.outcome == "MATCH"
    assert res.mismatch_detected is False
    assert res.result_summary == "No mismatch detected"


def test_hitl_rev_003_category_correction(test_env):
    """HITL-REV-003: Category correction from unresolved to document_comparison and non-comparison."""
    client, store, orch = test_env

    # 1. Test correcting unresolved to new_shipping_instruction (non-comparison -> COMPLETE, NOT_APPLICABLE)
    email = EmailRecord(
        email_id="email_hitl003",
        sender="partner@sea.com",
        subject="Booking inquiry and paperwork update",
        body="Attaching some paperwork for reference.",
        attachments=[
            AttachmentReference(document_id="email_hitl003_SI.txt", path="email_hitl003_SI.txt"),
            AttachmentReference(document_id="email_hitl003_BL.txt", path="email_hitl003_BL.txt"),
        ],
    )
    rec = orch.process_email(
        email,
        document_texts={
            "email_hitl003_SI.txt": DOC_MATCHING_SI,
            "email_hitl003_BL.txt": DOC_MATCHING_BL,
        },
    )
    assert rec.state == "NEEDS_REVIEW"
    assert rec.classification.category is None

    ev_id = "ev_email_cat_correct"
    update_non_comp = {
        "review_id": rec.review.review_id,
        "actor_id": "operator_admin",
        "action": "CORRECT",
        "rationale": "Customer is submitting new shipping instructions for an upcoming booking",
        "expected_revision": 1,
        "category": "new_shipping_instruction",
        "classification_evidence_ids": [ev_id],
        "added_evidence": [
            {
                "evidence_id": ev_id,
                "source_type": "email",
                "source_id": "email_hitl003",
                "kind": "text_span",
                "quote": "paperwork for reference",
            }
        ],
    }

    resp = client.post(f"/audit/{email.email_id}/review", json=update_non_comp)
    assert resp.status_code == 200
    res = AuditRecord.model_validate(resp.json())

    assert res.classification.category == "new_shipping_instruction"
    assert res.classification.state == "RESOLVED"
    assert res.state == "COMPLETE"
    assert res.outcome == "NOT_APPLICABLE"


def test_hitl_rev_004_role_correction(test_env):
    """HITL-REV-004: Role correction binds unassigned attachment documents."""
    client, store, orch = test_env

    # Email with ambiguous filenames
    email = EmailRecord(
        email_id="email_hitl004",
        sender="shipper@cargo.com",
        subject="Compare SI and Draft BL",
        body="Please compare attached draft BL and SI.",
        attachments=[
            AttachmentReference(document_id="doc_a.txt", path="doc_a.txt"),
            AttachmentReference(document_id="doc_b.txt", path="doc_b.txt"),
        ],
    )
    rec = orch.process_email(
        email,
        document_texts={
            "doc_a.txt": DOC_MATCHING_SI,
            "doc_b.txt": DOC_MATCHING_BL,
        },
    )
    assert rec.state == "NEEDS_REVIEW"

    ev_a = "ev_role_a"
    ev_b = "ev_role_b"
    update = {
        "review_id": rec.review.review_id,
        "actor_id": "operator_roles",
        "action": "CORRECT",
        "rationale": "Assigned roles based on document header inspection",
        "expected_revision": 1,
        "role_corrections": [
            {
                "document_id": "doc_a.txt",
                "assigned_role": "SI",
                "evidence_ids": [ev_a],
                "rationale": "Doc A contains header Shipping Instruction",
            },
            {
                "document_id": "doc_b.txt",
                "assigned_role": "BL",
                "evidence_ids": [ev_b],
                "rationale": "Doc B contains header Bill of Lading",
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

    resp = client.post(f"/audit/{email.email_id}/review", json=update)
    assert resp.status_code == 200
    res = AuditRecord.model_validate(resp.json())

    assert res.revision == 2
    doc_roles = {d.document_id: d.role for d in res.documents}
    assert doc_roles.get("doc_a.txt") == "SI"
    assert doc_roles.get("doc_b.txt") == "BL"
    assert res.state == "NEEDS_REVIEW"


def test_hitl_rev_005_confirm_on_unextracted_maintains_needs_review(test_env):
    """HITL-REV-005: CONFIRM action on unextracted field does not fabricate match; maintains NEEDS_REVIEW."""
    client, store, orch = test_env

    email = _make_comparison_email("email_hitl005")
    # SI missing container_count
    rec = orch.process_email(
        email,
        document_texts={
            f"{email.email_id}_SI.txt": DOC_MATCHING_SI.replace("Container Count: 2", ""),
            f"{email.email_id}_BL.txt": DOC_MATCHING_BL,
        },
    )
    assert rec.state == "NEEDS_REVIEW"

    # Operator CONFIRMS review without providing corrected value
    update = {
        "review_id": rec.review.review_id,
        "actor_id": "operator_viewer",
        "action": "CONFIRM",
        "rationale": "Acknowledging missing value; operator cannot find container count in source",
        "expected_revision": 1,
    }

    resp = client.post(f"/audit/{email.email_id}/review", json=update)
    assert resp.status_code == 200
    res = AuditRecord.model_validate(resp.json())

    # Case must still be in NEEDS_REVIEW because missing value was not corrected!
    assert res.state == "NEEDS_REVIEW"
    assert res.outcome is None
    assert res.mismatch_detected is None


# =====================================================================
# T12-03: Optimistic Revision Concurrency & HTTP 409 Collision (DC-07)
# =====================================================================


def test_api_rev_002_and_hitl_rev_006_concurrency_conflict_409(test_env):
    """API-REV-002 & HITL-REV-006: Stale expected_revision aborts transaction with HTTP 409 Conflict."""
    client, store, orch = test_env

    email = _make_comparison_email("email_rev002")
    rec = orch.process_email(
        email,
        document_texts={
            f"{email.email_id}_SI.txt": DOC_MATCHING_SI.replace("Gross Weight: 22,000 KGS", ""),
            f"{email.email_id}_BL.txt": DOC_MATCHING_BL,
        },
    )
    assert rec.revision == 1

    # First review update advances revision to 2
    ev_id = f"ev_c1_{email.email_id}"
    update1 = {
        "review_id": rec.review.review_id,
        "actor_id": "operator_1",
        "action": "CORRECT",
        "rationale": "Corrected weight from packing slip",
        "expected_revision": 1,
        "corrections": [
            {
                "document_id": f"{email.email_id}_SI.txt",
                "field": "gross_weight_kg",
                "raw_value": "22,000 KGS",
                "evidence_ids": [ev_id],
                "rationale": "Corrected weight",
            }
        ],
        "added_evidence": [
            {
                "evidence_id": ev_id,
                "source_type": "document",
                "source_id": f"{email.email_id}_SI.txt",
                "kind": "text_span",
                "quote": "22,000 KGS",
            }
        ],
    }
    resp1 = client.post(f"/audit/{email.email_id}/review", json=update1)
    assert resp1.status_code == 200
    assert resp1.json()["revision"] == 2

    # Second concurrent reviewer attempts update using stale expected_revision = 1
    update2 = {
        "review_id": rec.review.review_id,
        "actor_id": "operator_2_stale",
        "action": "CONFIRM",
        "rationale": "Attempting confirm with stale revision",
        "expected_revision": 1,  # Stale! Current is 2
    }
    resp2 = client.post(f"/audit/{email.email_id}/review", json=update2)
    assert resp2.status_code == 409

    err = resp2.json()
    assert err["code"] == "REVISION_CONFLICT"
    assert "Revision conflict" in err["message"]
    assert any("current_revision=2" in d for d in err["details"])
    assert any("expected_revision=1" in d for d in err["details"])


# =====================================================================
# GET /submission HTTP Shell Endpoint Presence (T12 delegation shell)
# Note: Authoritative schema mapping (EVAL-MAP-*) and export adapter
# verification (API-EXP-001/002) are formally owned and tested in T13.
# =====================================================================


def test_submission_shell_endpoint_presence(test_env):
    """T12 HTTP route shell verification for GET /submission.
    Verifies endpoint presence, basic delegation, and HTTP 409 shell response when cases need review.
    Authoritative API-EXP-001/002 and EVAL-MAP-* validation is owned and implemented in T13.
    """
    client, store, orch = test_env

    # 1. Store has 1 case needing review
    email_rev = _make_comparison_email("email_exp_blocked")
    orch.process_email(
        email_rev,
        document_texts={
            f"{email_rev.email_id}_SI.txt": DOC_MATCHING_SI.replace("Gross Weight: 22,000 KGS", ""),
            f"{email_rev.email_id}_BL.txt": DOC_MATCHING_BL,
        },
    )

    resp_blocked = client.get("/submission")
    assert resp_blocked.status_code == 409
    err = resp_blocked.json()
    assert err["code"] == "EXPORT_BLOCKED"
    assert "email_exp_blocked" in err["blocking_emails"]

    # 2. Resolve the review case
    ev_id = f"ev_exp_res_{email_rev.email_id}"
    update = {
        "review_id": f"rev_{email_rev.email_id}_1",
        "actor_id": "operator_exp",
        "action": "CORRECT",
        "rationale": "Correcting weight for submission export",
        "expected_revision": 1,
        "corrections": [
            {
                "document_id": f"{email_rev.email_id}_SI.txt",
                "field": "gross_weight_kg",
                "raw_value": "22,000 KGS",
                "evidence_ids": [ev_id],
                "rationale": "Corrected for export",
            }
        ],
        "added_evidence": [
            {
                "evidence_id": ev_id,
                "source_type": "document",
                "source_id": f"{email_rev.email_id}_SI.txt",
                "kind": "text_span",
                "quote": "22,000 KGS",
            }
        ],
    }
    resp_resolved = client.post(f"/audit/{email_rev.email_id}/review", json=update)
    assert resp_resolved.status_code == 200

    # 3. Export now succeeds with HTTP 200
    resp_success = client.get("/submission")
    assert resp_success.status_code == 200
    sub_data = resp_success.json()
    assert email_rev.email_id in sub_data
    assert sub_data[email_rev.email_id]["status"] == "OK"
