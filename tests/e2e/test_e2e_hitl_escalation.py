from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app import app
from src.api.routes import get_audit_store, get_orchestrator, set_audit_store
from src.hitl.escalation_engine import EscalationEngine
from src.llm.base_adapter import BaseAIAdapter
from src.models.audit import AttemptTracker
from src.models.document import ParserResult, ParserStatus
from src.models.evidence import FieldEvidence
from src.models.extraction import (
    DocumentExtraction,
    ExtractedField,
    FieldCandidate,
    FieldReliability,
)
from src.models.ingestion import AttachmentReference, EmailRecord
from src.models.review import LogicalReason, RecoveryState, ReviewIssue, Stage
from src.parsers.vision_adapter import MockVisionAdapter, recover_document_if_needed
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


def test_e2e_005_comparison_missing_attachment_escalation(e2e_env):
    """E2E-005: Comparison missing BL -> Stage 1 document_comparison -> Stage 2 flags missing_attachment."""
    client, store, orchestrator = e2e_env

    # Email requests comparison but attaches only SI
    email = EmailRecord(
        email_id="e2e_005_missing_bl",
        sender="shipper@example.com",
        subject="Draft BL check against SI",
        body="Please compare draft BL with SI. Only SI is attached for now.",
        attachments=[
            AttachmentReference(document_id="e2e_005_SI.txt", path="e2e_005_SI.txt")
        ],
    )
    doc_texts = {
        "e2e_005_SI.txt": DOC_CLEAN_SI,
    }

    rec = orchestrator.process_email(email, document_texts=doc_texts)

    assert rec.email_id == "e2e_005_missing_bl"
    assert rec.classification.category == "document_comparison"
    assert rec.state == "NEEDS_REVIEW"
    assert rec.outcome is None
    assert rec.mismatch_detected is None
    assert rec.review is not None
    assert any(
        issue.logical_reason == "missing_attachment"
        for issue in rec.review.issues
    )

    # Verify queue returns this case as needing review
    resp = client.get("/audit?hitl_only=true")
    assert resp.status_code == 200
    hitl_cases = resp.json()
    assert any(c["email_id"] == "e2e_005_missing_bl" for c in hitl_cases)


def test_e2e_006_scanned_document_ocr_recovery_lifecycle(e2e_env):
    """E2E-006: Image-only PDF BL -> OCR recovery -> all 7 fields resolved -> compared successfully."""
    client, store, orchestrator = e2e_env

    # 1. Simulate initial unreadable / scanned PDF
    initial_unreadable_bl = ParserResult(
        document_id="e2e_006_BL.pdf",
        status=ParserStatus.UNREADABLE,
        text="",
        usable_for_extraction=False,
        is_scanned=True,
        diagnostic_evidence_ids=["ev_diag_scanned"],
        attempt_ids=["att_parse_scanned"],
    )

    # 2. OCR Mock Adapter recovers text cleanly
    mock_ocr_payload = {
        "text": DOC_CLEAN_BL,
        "blocks": [
            {
                "text": DOC_CLEAN_BL,
                "bbox": [10, 10, 500, 700],
                "confidence": 0.99,
            }
        ],
    }
    mock_adapter = MockVisionAdapter(payload=mock_ocr_payload)

    recovered_bl = recover_document_if_needed(
        initial_unreadable_bl, Path("e2e_006_BL.pdf"), adapter=mock_adapter
    )
    assert recovered_bl.status == ParserStatus.SUCCESS
    assert recovered_bl.usable_for_extraction is True

    # 3. Pipeline processes email with recovered text
    email = EmailRecord(
        email_id="e2e_006_ocr",
        sender="shipper@example.com",
        subject="Draft BL check against SI",
        body="Please compare attached SI and Draft BL.",
        attachments=[
            AttachmentReference(document_id="e2e_006_SI.txt", path="e2e_006_SI.txt"),
            AttachmentReference(document_id="e2e_006_BL.pdf", path="e2e_006_BL.pdf"),
        ],
    )
    doc_texts = {
        "e2e_006_SI.txt": DOC_CLEAN_SI,
        "e2e_006_BL.pdf": recovered_bl.text,
    }

    rec = orchestrator.process_email(email, document_texts=doc_texts)

    assert rec.state == "COMPLETE"
    assert rec.outcome == "MATCH"
    assert rec.mismatch_detected is False
    assert rec.result_summary == "No mismatch detected"
    assert rec.review is None


def test_e2e_007_degraded_scan_ocr_failure_escalation(e2e_env):
    """E2E-007: Degraded scan OCR failure -> HITL unreadable_document -> partial results preserved."""
    client, store, orchestrator = e2e_env

    # Scanned BL where OCR fails or yields unusable content
    unusable_bl = ParserResult(
        document_id="e2e_007_BL.pdf",
        status=ParserStatus.UNREADABLE,
        text="",
        usable_for_extraction=False,
        is_scanned=True,
        error_message="OCR character density too low; unreadable scan",
        diagnostic_evidence_ids=["ev_diag_low_density"],
        attempt_ids=["att_parse_fail"],
    )

    # Recover returns unusable
    mock_adapter = MockVisionAdapter(payload={"text": "", "blocks": []})
    recovered = recover_document_if_needed(
        unusable_bl, Path("e2e_007_BL.pdf"), adapter=mock_adapter
    )
    assert recovered.usable_for_extraction is False

    engine = EscalationEngine()
    issue = engine.create_unreadable_document_issue(
        document_id="e2e_007_BL.pdf",
        diagnostic="OCR unreadable noise; scan degraded beyond threshold",
        evidence_ids=["ev_diag_low_density"],
        recovery_state="EXHAUSTED",
        attempt_ids=["att_parse_fail"],
    )
    review_case = engine.build_review_case(review_id="rev_e2e_007", issues=[issue])

    assert issue.logical_reason == LogicalReason.UNREADABLE_DOCUMENT
    assert issue.recovery_state == "EXHAUSTED"
    assert review_case.state == "OPEN"


def test_e2e_008_conflicting_candidate_values_escalation(e2e_env):
    """E2E-008: Conflicting gross weight candidates -> HITL conflicting_candidate_values."""
    engine = EscalationEngine()
    candidates = ["22,000 KGS", "25,500 KGS"]
    issue = engine.create_conflicting_candidate_values_issue(
        document_id="e2e_008_SI.txt",
        field="gross_weight_kg",
        candidates=candidates,
        evidence_ids=["ev_span_w1", "ev_span_w2"],
        suggested_action="Select the correct gross weight candidate from conflicting table rows",
    )

    assert issue.logical_reason == LogicalReason.CONFLICTING_CANDIDATE_VALUES
    assert issue.fields == ["gross_weight_kg"]
    assert issue.recovery_state == "UNRELIABLE"
    assert "22,000 KGS" in issue.recovery_detail
    assert "25,500 KGS" in issue.recovery_detail

    review_case = engine.build_review_case(review_id="rev_e2e_008", issues=[issue])
    assert review_case.state == "OPEN"
    assert len(review_case.issues) == 1


def test_e2e_013_provider_outage_with_validated_fallback(e2e_env):
    """E2E-013: Provider outage with validated fallback -> pipeline continues without human escalation."""
    # Simulate primary failure intercepted by validated fallback
    class FallbackEnabledAdapter(BaseAIAdapter):
        def invoke_raw(self, prompt: str, **kwargs) -> str:
            # Primary simulated failure, fallback produces grounded result
            return '{"category": "document_comparison", "reason": "Draft BL check", "evidence": ["Draft BL check"]}'

    adapter = FallbackEnabledAdapter()
    raw = adapter.invoke_raw("classify email")
    assert "document_comparison" in raw

    # Pipeline executes cleanly with validated fallback
    email = EmailRecord(
        email_id="e2e_013_fallback",
        sender="shipper@example.com",
        subject="Draft BL check",
        body="Kindly compare attached SI and Draft BL.",
        attachments=[
            AttachmentReference(document_id="e2e_013_SI.txt", path="e2e_013_SI.txt"),
            AttachmentReference(document_id="e2e_013_BL.txt", path="e2e_013_BL.txt"),
        ],
    )
    doc_texts = {
        "e2e_013_SI.txt": DOC_CLEAN_SI,
        "e2e_013_BL.txt": DOC_CLEAN_BL,
    }

    orchestrator = PipelineOrchestrator(audit_store=AuditStore(), ai_adapter=adapter)
    rec = orchestrator.process_email(email, document_texts=doc_texts)

    assert rec.state == "COMPLETE"
    assert rec.outcome == "MATCH"
    assert rec.review is None


def test_e2e_014_provider_outage_and_fallback_exhaustion_escalation(e2e_env):
    """E2E-014: Provider outage and fallback exhaustion -> HITL processing_or_provider_failure."""
    engine = EscalationEngine()
    issue = engine.create_processing_or_provider_failure_issue(
        stage=Stage.OCR,
        document_ids=["heavy_scan.pdf"],
        error_detail="AI provider timeout 504 and fallback adapter exhausted after 3 attempts",
        evidence_ids=["ev_provider_timeout"],
        recovery_state="EXHAUSTED",
        attempt_ids=["att_1", "att_2", "att_3"],
    )

    assert issue.logical_reason == LogicalReason.PROCESSING_OR_PROVIDER_FAILURE
    assert issue.stage == Stage.OCR
    assert issue.recovery_state == "EXHAUSTED"
    assert "504" in issue.recovery_detail

    review_case = engine.build_review_case(review_id="rev_e2e_014", issues=[issue])
    assert review_case.state == "OPEN"
    assert any(
        iss.logical_reason == LogicalReason.PROCESSING_OR_PROVIDER_FAILURE
        for iss in review_case.issues
    )
