from __future__ import annotations

import pytest

from src.hitl.escalation_engine import EscalationEngine
from src.models.evidence import FieldEvidence
from src.models.review import (
    LogicalReason,
    ReviewCase,
    ReviewIssue,
    Stage,
)


@pytest.fixture
def engine() -> EscalationEngine:
    return EscalationEngine(default_attempt_id="att_test_1")


def test_hitl_rsn_001_missing_attachment(engine: EscalationEngine):
    """HITL-RSN-001 / FR-014: Email comparison request missing draft BL."""
    issue = engine.create_missing_attachment_issue(
        issue_id="issue_missing_bl",
        expected_role="BL",
        document_ids=["doc_si.pdf"],
        evidence_ids=["ev_email_body_no_bl"],
        suggested_action="Request draft BL attachment from sender",
        recovery_detail="Email requested comparison but only SI was attached",
    )

    assert issue.logical_reason == LogicalReason.MISSING_ATTACHMENT
    assert issue.expected_role == "BL"
    assert issue.stage == Stage.IDENTIFICATION
    assert issue.document_ids == ["doc_si.pdf"]
    assert issue.fields == []
    assert issue.evidence_ids == ["ev_email_body_no_bl"]
    assert issue.recovery_state == "NOT_APPLICABLE"
    assert "draft BL" in issue.suggested_action


def test_hitl_rsn_002_unreadable_document(engine: EscalationEngine):
    """HITL-RSN-002 / FR-014 / NFR-003: Corrupted PDF attachment."""
    issue = engine.create_unreadable_document_issue(
        document_id="corrupted_scan.pdf",
        diagnostic="pypdf stream EOF before end of file marker; image unrenderable",
        evidence_ids=["ev_diag_parser_err"],
        recovery_state="EXHAUSTED",
    )

    assert issue.logical_reason == LogicalReason.UNREADABLE_DOCUMENT
    assert issue.stage == Stage.PARSING
    assert issue.document_ids == ["corrupted_scan.pdf"]
    assert issue.expected_role is None
    assert issue.fields == []
    assert issue.evidence_ids == ["ev_diag_parser_err"]
    assert issue.recovery_state == "EXHAUSTED"
    assert "pypdf stream EOF" in issue.recovery_detail


def test_hitl_rsn_003_wrong_or_uncertain_document_type(engine: EscalationEngine):
    """HITL-RSN-003 / FR-014: Attachment roles ambiguous or unverified."""
    issue = engine.create_wrong_or_uncertain_document_type_issue(
        document_ids=["invoice_123.pdf", "packing_slip.pdf"],
        evidence_ids=["ev_header_classifier_fail"],
        suggested_action="Manually check documents; neither appears to be a valid Draft BL",
        recovery_detail="Header heuristic and AI role binder failed to identify Draft BL",
    )

    assert issue.logical_reason == LogicalReason.WRONG_OR_UNCERTAIN_DOCUMENT_TYPE
    assert issue.stage == Stage.IDENTIFICATION
    assert issue.document_ids == ["invoice_123.pdf", "packing_slip.pdf"]
    assert issue.expected_role is None
    assert issue.fields == []
    assert issue.evidence_ids == ["ev_header_classifier_fail"]
    assert issue.recovery_state == "NOT_APPLICABLE"


def test_hitl_rsn_004_missing_required_value(engine: EscalationEngine):
    """HITL-RSN-004 / FR-014: Mandatory port_of_discharge missing from SI."""
    issue = engine.create_missing_required_value_issue(
        document_id="doc_si_001.txt",
        field="port_of_discharge",
        evidence_ids=["ev_si_text_parsed"],
        suggested_action="Inspect doc_si_001.txt to verify if port of discharge is specified",
        recovery_detail="Port of discharge field absent from document text",
    )

    assert issue.logical_reason == LogicalReason.MISSING_REQUIRED_VALUE
    assert issue.stage == Stage.EXTRACTION
    assert issue.document_ids == ["doc_si_001.txt"]
    assert issue.fields == ["port_of_discharge"]
    assert issue.expected_role is None
    assert issue.evidence_ids == ["ev_si_text_parsed"]
    assert issue.recovery_state == "NOT_APPLICABLE"


def test_hitl_rsn_005_uncertain_result(engine: EscalationEngine):
    """HITL-RSN-005 / FR-014: Classification or comparison confidence ambiguous."""
    issue = engine.create_uncertain_result_issue(
        document_ids=["doc_bl_002.pdf"],
        fields=["shipper"],
        evidence_ids=["ev_ocr_low_conf"],
        suggested_action="Review shipper text candidate; OCR confidence was 0.35",
        recovery_detail="OCR character corruption density elevated; text ungrounded",
    )

    assert issue.logical_reason == LogicalReason.UNCERTAIN_RESULT
    assert issue.stage == Stage.EXTRACTION
    assert issue.document_ids == ["doc_bl_002.pdf"]
    assert issue.fields == ["shipper"]
    assert issue.recovery_state == "UNRELIABLE"
    assert issue.evidence_ids == ["ev_ocr_low_conf"]


def test_hitl_rsn_006_conflicting_candidate_values(engine: EscalationEngine):
    """HITL-RSN-006 / FR-014: Multiple conflicting candidate weights in document."""
    candidates = ["22,000 KGS", "24,500 KGS"]
    issue = engine.create_conflicting_candidate_values_issue(
        document_id="doc_bl_003.txt",
        field="gross_weight_kg",
        candidates=candidates,
        evidence_ids=["ev_span_weight_1", "ev_span_weight_2"],
        suggested_action="Select correct gross weight candidate from conflicting table rows",
    )

    assert issue.logical_reason == LogicalReason.CONFLICTING_CANDIDATE_VALUES
    assert issue.stage == Stage.EXTRACTION
    assert issue.document_ids == ["doc_bl_003.txt"]
    assert issue.fields == ["gross_weight_kg"]
    assert issue.recovery_state == "UNRELIABLE"
    assert issue.evidence_ids == ["ev_span_weight_1", "ev_span_weight_2"]
    assert "22,000 KGS" in issue.recovery_detail
    assert "24,500 KGS" in issue.recovery_detail


def test_hitl_rsn_007_processing_or_provider_failure(engine: EscalationEngine):
    """HITL-RSN-007 / FR-017: OCR/AI provider timeout after retries exhausted."""
    issue = engine.create_processing_or_provider_failure_issue(
        stage=Stage.OCR,
        document_ids=["doc_heavy_scan.pdf"],
        error_detail="DocumentAI HTTP 503 Service Unavailable after 3 technical retries",
        evidence_ids=["ev_provider_timeout_log"],
        recovery_state="EXHAUSTED",
        attempt_ids=["att_ocr_1", "att_ocr_2", "att_ocr_3"],
    )

    assert issue.logical_reason == LogicalReason.PROCESSING_OR_PROVIDER_FAILURE
    assert issue.stage == Stage.OCR
    assert issue.document_ids == ["doc_heavy_scan.pdf"]
    assert issue.recovery_state == "EXHAUSTED"
    assert len(issue.attempt_ids) == 3
    assert "HTTP 503" in issue.recovery_detail


def test_review_case_assembly_and_invariants(engine: EscalationEngine):
    """Test ReviewCase assembly with multiple issues, state OPEN, and Pydantic validation."""
    issue1 = engine.create_missing_required_value_issue(
        document_id="si.pdf",
        field="container_count",
        evidence_ids=["ev_si_1"],
    )
    issue2 = engine.create_uncertain_result_issue(
        document_ids=["bl.pdf"],
        fields=["shipper"],
        evidence_ids=["ev_bl_1"],
    )

    case = engine.build_review_case(
        review_id="rev_case_123",
        issues=[issue1, issue2],
    )

    assert isinstance(case, ReviewCase)
    assert case.review_id == "rev_case_123"
    assert case.state == "OPEN"
    assert len(case.issues) == 2
    assert case.issues[0].logical_reason == LogicalReason.MISSING_REQUIRED_VALUE
    assert case.issues[1].logical_reason == LogicalReason.UNCERTAIN_RESULT

    # Pydantic invariant: min_length=1 on issues
    with pytest.raises(ValueError):
        engine.build_review_case("rev_case_empty", [])


def test_generic_dispatcher_coverage(engine: EscalationEngine):
    """Verify that dispatch_issue accepts every LogicalReason enum variant."""
    for reason in LogicalReason:
        issue = engine.dispatch_issue(
            reason=reason,
            stage=Stage.REVIEW,
            document_ids=["doc_1.txt"],
            evidence_ids=["ev_1"],
            suggested_action="Operator review",
            recovery_detail="Generic reason dispatch test",
        )
        assert issue.logical_reason == reason
        assert issue.stage == Stage.REVIEW
        assert issue.document_ids == ["doc_1.txt"]
        assert len(issue.evidence_ids) >= 1
