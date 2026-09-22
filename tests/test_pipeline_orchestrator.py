from __future__ import annotations

from decimal import Decimal
import pytest

from src.models.audit import AuditRecord
from src.models.extraction import FieldReliability
from src.models.ingestion import AttachmentReference, EmailRecord
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


@pytest.fixture
def store() -> AuditStore:
    return AuditStore()


@pytest.fixture
def orchestrator(store: AuditStore) -> PipelineOrchestrator:
    return PipelineOrchestrator(audit_store=store)


def _make_comparison_email(email_id: str = "email_test_01") -> EmailRecord:
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


def test_pipe_cmp_001_all_seven_fields_match(orchestrator: PipelineOrchestrator, store: AuditStore):
    """PIPE-CMP-001 / FR-011 / DEC-01: All 7 fields identical between SI and BL."""
    email = _make_comparison_email("email_cmp_001")
    doc_texts = {
        "email_cmp_001_SI.txt": DOC_MATCHING_SI,
        "email_cmp_001_BL.txt": DOC_MATCHING_BL,
    }

    rec = orchestrator.process_email(email, document_texts=doc_texts)

    assert isinstance(rec, AuditRecord)
    assert rec.state == "COMPLETE"
    assert rec.outcome == "MATCH"
    assert rec.mismatch_detected is False
    assert rec.result_summary == "No mismatch detected"
    assert len(rec.discrepancies) == 0
    assert rec.review is None
    assert rec.revision == 1
    assert rec.partial_result is not None
    assert len(rec.partial_result.comparisons) == 7
    assert len(rec.partial_result.unresolved_fields) == 0

    # Ensure saved in store
    assert store.get("email_cmp_001") is not None


def test_pipe_cmp_002_container_count_mismatch(orchestrator: PipelineOrchestrator):
    """PIPE-CMP-002 / FR-012 / DEC-01: Only container_count differs (2 vs 3)."""
    email = _make_comparison_email("email_cmp_002")
    bl_diff_container = DOC_MATCHING_BL.replace("Container Count: 2", "Container Count: 3")

    doc_texts = {
        "email_cmp_002_SI.txt": DOC_MATCHING_SI,
        "email_cmp_002_BL.txt": bl_diff_container,
    }

    rec = orchestrator.process_email(email, document_texts=doc_texts)

    assert rec.state == "COMPLETE"
    assert rec.outcome == "MISMATCH"
    assert rec.mismatch_detected is True
    assert rec.result_summary != "No mismatch detected"
    assert len(rec.discrepancies) == 1
    disc = rec.discrepancies[0]
    assert disc.field == "container_count"
    assert disc.si_value == 2
    assert disc.bl_value == 3
    assert rec.review is None


def test_pipe_cmp_003_multiple_field_mismatches(orchestrator: PipelineOrchestrator):
    """PIPE-CMP-003 / FR-012: shipper and gross_weight_kg differ."""
    email = _make_comparison_email("email_cmp_003")
    bl_diff = (
        DOC_MATCHING_BL.replace("ACME EXPORTS LTD", "ZENITH LOGISTICS LTD")
        .replace("22,000 KGS", "24,500.00 KGS")
    )

    doc_texts = {
        "email_cmp_003_SI.txt": DOC_MATCHING_SI,
        "email_cmp_003_BL.txt": bl_diff,
    }

    rec = orchestrator.process_email(email, document_texts=doc_texts)

    assert rec.state == "COMPLETE"
    assert rec.outcome == "MISMATCH"
    assert rec.mismatch_detected is True
    assert len(rec.discrepancies) == 2
    disc_fields = {d.field for d in rec.discrepancies}
    assert disc_fields == {"shipper", "gross_weight_kg"}


def test_pipe_cmp_004_and_dc_003_partial_results_when_field_unextracted(
    orchestrator: PipelineOrchestrator,
):
    """PIPE-CMP-004 / FR-011 / DC-03 / REG-010: 6 fields match, 1 field unextracted in BL."""
    email = _make_comparison_email("email_cmp_004")
    # BL lacks container_count line
    bl_lacks_container = DOC_MATCHING_BL.replace("Container Count: 2\n", "")

    doc_texts = {
        "email_cmp_004_SI.txt": DOC_MATCHING_SI,
        "email_cmp_004_BL.txt": bl_lacks_container,
    }

    rec = orchestrator.process_email(email, document_texts=doc_texts)

    # Tri-State Model: Mismatch detected and outcome MUST be None when review is required
    assert rec.state == "NEEDS_REVIEW"
    assert rec.outcome is None
    assert rec.mismatch_detected is None
    assert "No mismatch detected" not in rec.result_summary

    # 6 passing matches preserved under partial results (HITL-PART-001, REG-009)
    assert rec.partial_result is not None
    assert len(rec.partial_result.comparisons) == 6
    assert rec.partial_result.unresolved_fields == ["container_count"]

    # Review case opened
    assert rec.review is not None
    assert rec.review.state == "OPEN"
    assert any(i.logical_reason == "missing_required_value" for i in rec.review.issues)


def test_pipe_cmp_005_known_mismatch_with_unreadable_field(
    orchestrator: PipelineOrchestrator,
):
    """PIPE-CMP-005 / DC-03: container_count differs, but port_of_discharge missing in BL."""
    email = _make_comparison_email("email_cmp_005")
    # BL has container 3 (differs from 2) and lacks port_of_discharge
    bl_diff_and_missing = (
        DOC_MATCHING_BL.replace("Container Count: 2", "Container Count: 3")
        .replace("Port of Discharge: ROTTERDAM (NLRTM)\n", "")
    )

    doc_texts = {
        "email_cmp_005_SI.txt": DOC_MATCHING_SI,
        "email_cmp_005_BL.txt": bl_diff_and_missing,
    }

    rec = orchestrator.process_email(email, document_texts=doc_texts)

    assert rec.state == "NEEDS_REVIEW"
    assert rec.outcome is None
    assert rec.mismatch_detected is None

    # Partial result preserves the known container mismatch
    assert rec.partial_result is not None
    assert "port_of_discharge" in rec.partial_result.unresolved_fields
    assert len(rec.discrepancies) == 1
    assert rec.discrepancies[0].field == "container_count"


def test_pipe_cmp_006_conflicting_candidates_in_si(
    orchestrator: PipelineOrchestrator,
):
    """PIPE-CMP-006 / FR-014: Conflicting gross weight values in SI."""
    email = _make_comparison_email("email_cmp_006")
    si_conflicting_weight = DOC_MATCHING_SI.replace(
        "Gross Weight: 22,000 KGS", "Gross Weight: 22000 or 23000 kg"
    )
    doc_texts = {
        "email_cmp_006_SI.txt": si_conflicting_weight,
        "email_cmp_006_BL.txt": DOC_MATCHING_BL,
    }

    rec = orchestrator.process_email(email, document_texts=doc_texts)

    assert rec.state == "NEEDS_REVIEW"
    assert rec.outcome is None
    assert rec.mismatch_detected is None
    assert rec.partial_result is not None
    assert "gross_weight_kg" in rec.partial_result.unresolved_fields
    assert rec.review is not None
    assert rec.review.state == "OPEN"


def test_non_comparison_email_stops_immediately_fr_004(
    orchestrator: PipelineOrchestrator, store: AuditStore
):
    """FR-004: Non-comparison emails terminate immediately and emit COMPLETE / NOT_APPLICABLE."""
    email = EmailRecord(
        email_id="email_invoice_01",
        sender="billing@partner.com",
        subject="Invoice #99403 Overdue Notice",
        body="Attached please find the outstanding invoice for last month services.",
        attachments=[
            AttachmentReference(document_id="inv_99403.pdf", path="inv_99403.pdf"),
        ],
    )

    rec = orchestrator.process_email(email)

    assert rec.state == "COMPLETE"
    assert rec.outcome == "NOT_APPLICABLE"
    assert rec.mismatch_detected is None
    assert rec.classification.category == "invoice_query"
    assert rec.documents == []
    assert rec.parsers == []
    assert rec.extractions == []
    assert rec.partial_result is None
    assert rec.discrepancies == []
    assert rec.review is None

    # Saved in store
    saved = store.get("email_invoice_01")
    assert saved is not None
    assert saved.outcome == "NOT_APPLICABLE"


def test_audit_store_queries_and_dynamic_metrics(
    orchestrator: PipelineOrchestrator, store: AuditStore
):
    """Verify AuditStore queries, filtering, and dynamic live metrics (zero hardcoded strings, REG-003)."""
    # 1. Matching comparison
    email1 = _make_comparison_email("email_store_1")
    orchestrator.process_email(
        email1,
        document_texts={
            "email_store_1_SI.txt": DOC_MATCHING_SI,
            "email_store_1_BL.txt": DOC_MATCHING_BL,
        },
    )

    # 2. Mismatched comparison
    email2 = _make_comparison_email("email_store_2")
    orchestrator.process_email(
        email2,
        document_texts={
            "email_store_2_SI.txt": DOC_MATCHING_SI,
            "email_store_2_BL.txt": DOC_MATCHING_BL.replace("Container Count: 2", "Container Count: 5"),
        },
    )

    # 3. Non-comparison email
    email3 = EmailRecord(
        email_id="email_store_3",
        sender="spam@offers.com",
        subject="Special discounts for casino slots",
        body="Click here for free spins and bonuses!",
        attachments=[],
    )
    orchestrator.process_email(email3)

    assert store.count() == 3

    # Query tests
    complete_recs = store.list(state="COMPLETE")
    assert len(complete_recs) == 3

    mismatch_recs = store.list(outcome="MISMATCH")
    assert len(mismatch_recs) == 1
    assert mismatch_recs[0].email_id == "email_store_2"

    discrepant_recs = store.list(has_discrepancy=True)
    assert len(discrepant_recs) == 1

    # Dynamic summary metrics
    summary = store.get_summary()
    assert summary["total_records"] == 3
    assert summary["states"]["COMPLETE"] == 3
    assert summary["categories"]["document_comparison"] == 2
    assert summary["categories"]["spam"] == 1
    assert summary["outcomes"]["MATCH"] == 1
    assert summary["outcomes"]["MISMATCH"] == 1
    assert summary["outcomes"]["NOT_APPLICABLE"] == 1
    assert summary["discrepant_records"] == 1
