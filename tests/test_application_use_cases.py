from __future__ import annotations

from unittest.mock import MagicMock
import pytest

from src.application.assembler import AuditRecordAssembler
from src.application.use_cases.verify_email import EmailVerificationUseCase, to_email_record
from src.hitl.escalation_engine import EscalationEngine
from src.models.audit import AttemptRecord, AttemptTracker, AuditRecord
from src.models.comparison import ComparisonOutcome, PartialResult
from src.models.evidence import FieldEvidence
from src.models.ingestion import AttachmentReference, ClassificationResult, EmailRecord
from src.models.review import LogicalReason, ReviewCase, ReviewIssue, Stage


def make_dummy_email() -> EmailRecord:
    return EmailRecord(
        email_id="email_test_001",
        sender="sender@example.com",
        subject="SI and Draft BL Comparison",
        body="Please compare the attached shipping documents.",
        attachments=[],
    )


class TestAuditRecordAssembler:
    """Unit tests for AuditRecordAssembler."""

    def test_build_ambiguous_review_record(self) -> None:
        email = make_dummy_email()
        ev = FieldEvidence(
            evidence_id="ev_cls",
            source_type="email",
            source_id=email.email_id,
            kind="text_span",
            quote="Ambiguous text",
        )
        cls_result = ClassificationResult(
            category=None,
            state="NEEDS_REVIEW",
            reason="Ambiguous email body",
            evidence_ids=["ev_cls"],
        )
        engine = EscalationEngine()
        issue = engine.create_uncertain_result_issue(
            document_ids=[],
            evidence_ids=["ev_cls"],
            suggested_action="Review intent",
            recovery_detail="Inconclusive",
            attempt_ids=["att_1"],
            stage=Stage.CLASSIFICATION,
        )
        review_case = engine.build_review_case(
            review_id="rev_1",
            issues=[issue],
        )
        tracker = AttemptTracker()
        tracker.attempts.append(
            AttemptRecord(
                attempt_id="att_1",
                operation_id=email.email_id,
                stage=Stage.CLASSIFICATION,
                kind="primary",
                attempt_number=1,
                outcome="FAILED",
            )
        )

        record = AuditRecordAssembler.build_ambiguous_review_record(
            email=email,
            classification=cls_result,
            review_case=review_case,
            tracker=tracker,
            evidence=[ev, ev],  # test deduplication
        )

        assert record.email_id == "email_test_001"
        assert record.state == "NEEDS_REVIEW"
        assert record.outcome is None
        assert record.mismatch_detected is None
        assert record.result_summary == "Review required: Ambiguous email intent"
        assert len(record.evidence) == 1
        assert record.review is review_case

    def test_build_non_comparison_record(self) -> None:
        email = make_dummy_email()
        ev = FieldEvidence(
            evidence_id="ev_inquiry",
            source_type="email",
            source_id=email.email_id,
            kind="text_span",
            quote="Inquiry text",
        )
        cls_result = ClassificationResult(
            category="general",
            state="RESOLVED",
            reason="General inquiry email",
            evidence_ids=["ev_inquiry"],
        )
        tracker = AttemptTracker()

        record = AuditRecordAssembler.build_non_comparison_record(
            email=email,
            classification=cls_result,
            tracker=tracker,
            evidence=[ev],
        )

        assert record.email_id == "email_test_001"
        assert record.state == "COMPLETE"
        assert record.outcome == "NOT_APPLICABLE"
        assert "Non-comparison category: general" in record.result_summary
        assert record.review is None

    def test_build_complete_comparison_record(self) -> None:
        # For full comparison, using real models to satisfy strict contract invariants
        email = EmailRecord(
            email_id="email_cmp_1",
            sender="shipper@example.com",
            subject="Compare docs",
            body="Compare docs",
            attachments=[
                AttachmentReference(document_id="doc_si", path="doc_si"),
                AttachmentReference(document_id="doc_bl", path="doc_bl"),
            ],
        )
        from src.comparator.field_comparator import compare_seven_fields
        from src.models.document import DocumentReference, Role
        from src.models.extraction import DocumentExtraction, ExtractedField, FieldCandidate, NormalizedField
        from tests.test_comparator import make_matching_canonical_fields

        def make_field_for_doc(doc_id: str, field_name: str, val: object) -> ExtractedField:
            candidate = FieldCandidate(
                raw_value=str(val),
                source_unit=None,
                evidence_ids=[f"ev_{doc_id}_{field_name}"],
            )
            return ExtractedField(
                field=field_name,  # type: ignore[arg-type]
                reliability="RELIABLE",
                candidates=[candidate],
                selected_candidate=0,
                normalized=NormalizedField(
                    field=field_name,  # type: ignore[arg-type]
                    state="VALID",
                    value=val,  # type: ignore[arg-type]
                    rule_version="v1.0",
                ),
                explanation=f"Reliably extracted {field_name}",
            )

        si_canon = make_matching_canonical_fields()
        si_fields = {f: make_field_for_doc("doc_si", f, v) for f, v in si_canon.items()}
        bl_fields = {f: make_field_for_doc("doc_bl", f, v) for f, v in si_canon.items()}

        si_doc = DocumentExtraction(document_id="doc_si", role="SI", fields=si_fields)
        bl_doc = DocumentExtraction(document_id="doc_bl", role="BL", fields=bl_fields)
        comp_res = compare_seven_fields(si_doc, bl_doc)

        ev_list: list[FieldEvidence] = [
            FieldEvidence(
                evidence_id="ev_cls",
                source_type="email",
                source_id=email.email_id,
                kind="text_span",
                quote="comp",
            )
        ]
        for f in si_canon:
            ev_list.append(
                FieldEvidence(
                    evidence_id=f"ev_doc_si_{f}",
                    source_type="document",
                    source_id="doc_si",
                    kind="text_span",
                    quote="text",
                )
            )
            ev_list.append(
                FieldEvidence(
                    evidence_id=f"ev_doc_bl_{f}",
                    source_type="document",
                    source_id="doc_bl",
                    kind="text_span",
                    quote="text",
                )
            )

        cls_result = ClassificationResult(
            category="document_comparison",
            state="RESOLVED",
            reason="Comparison",
            evidence_ids=["ev_cls"],
        )
        tracker = AttemptTracker()
        docs = [
            DocumentReference(document_id="doc_si", role="SI", identification_evidence_ids=["ev_cls"]),
            DocumentReference(document_id="doc_bl", role="BL", identification_evidence_ids=["ev_cls"]),
        ]

        record = AuditRecordAssembler.build_complete_comparison_record(
            email=email,
            classification=cls_result,
            outcome=comp_res.outcome,
            mismatch_detected=comp_res.mismatch_detected,
            result_summary=comp_res.result_summary,
            documents=docs,
            parsers=[],
            extractions=[si_doc, bl_doc],
            partial_result=comp_res.partial_result,
            discrepancies=comp_res.discrepancies,
            tracker=tracker,
            evidence=ev_list,
        )

        assert record.email_id == "email_cmp_1"
        assert record.state == "COMPLETE"
        assert record.outcome == "MATCH"
        assert record.mismatch_detected is False
        assert record.result_summary == "No mismatch detected"


class TestEmailVerificationUseCase:
    """Unit tests for EmailVerificationUseCase orchestration with mock dependencies."""

    def test_stage1_ambiguous_classification_escalates(self) -> None:
        classifier = MagicMock()
        role_binder = MagicMock()
        extractor = MagicMock()
        escalation_engine = EscalationEngine()
        audit_store = MagicMock()

        cls_res = ClassificationResult(
            category=None,
            state="NEEDS_REVIEW",
            reason="Uncertain",
            evidence_ids=[],
        )
        classifier.classify.return_value = (cls_res, [])

        use_case = EmailVerificationUseCase(
            classifier=classifier,
            role_binder=role_binder,
            extractor=extractor,
            escalation_engine=escalation_engine,
            audit_store=audit_store,
        )

        email = make_dummy_email()
        result = use_case.execute(email)

        assert result.state == "NEEDS_REVIEW"
        assert result.result_summary == "Review required: Ambiguous email intent"
        audit_store.save.assert_called_once_with(result)
        role_binder.bind_roles.assert_not_called()
        extractor.extract_comparison_pair_fields.assert_not_called()

    def test_stage1_non_comparison_terminates_complete(self) -> None:
        classifier = MagicMock()
        role_binder = MagicMock()
        extractor = MagicMock()
        escalation_engine = MagicMock()
        audit_store = MagicMock()

        email = make_dummy_email()
        ev_spam = FieldEvidence(
            evidence_id="ev_spam",
            source_type="email",
            source_id=email.email_id,
            kind="text_span",
            quote="Spam content",
        )
        cls_res = ClassificationResult(
            category="spam",
            state="RESOLVED",
            reason="Spam notification",
            evidence_ids=["ev_spam"],
        )
        classifier.classify.return_value = (cls_res, [ev_spam])

        use_case = EmailVerificationUseCase(
            classifier=classifier,
            role_binder=role_binder,
            extractor=extractor,
            escalation_engine=escalation_engine,
            audit_store=audit_store,
        )

        result = use_case.execute(email)

        assert result.state == "COMPLETE"
        assert result.outcome == "NOT_APPLICABLE"
        assert "Non-comparison category: spam" in result.result_summary
        audit_store.save.assert_called_once_with(result)
        role_binder.bind_roles.assert_not_called()
