from __future__ import annotations

from typing import List, Optional, Sequence
from src.models.audit import (
    AttemptTracker,
    AuditRecord,
    ProcessingMetadata,
)
from src.models.comparison import Discrepancy, PartialResult
from src.models.document import DocumentReference, ParserResult
from src.models.evidence import FieldEvidence
from src.models.extraction import (
    FIELD_NAMES,
    DocumentExtraction,
)
from src.models.ingestion import (
    ClassificationResult,
    EmailRecord,
)
from src.models.review import ReviewCase, ReviewIssue


def dedup_evidence(evidence_list: Sequence[FieldEvidence]) -> List[FieldEvidence]:
    """Deduplicate evidence items by evidence_id while preserving order."""
    seen = set()
    deduped = []
    for ev in evidence_list:
        if ev.evidence_id not in seen:
            seen.add(ev.evidence_id)
            deduped.append(ev)
    return deduped


class AuditRecordAssembler:
    """DDD Assembler translating multi-stage verification outputs into rich AuditRecord aggregates."""

    @staticmethod
    def build_ambiguous_review_record(
        email: EmailRecord,
        classification: ClassificationResult,
        review_case: ReviewCase,
        tracker: AttemptTracker,
        evidence: Sequence[FieldEvidence],
        technical_attempt_limit: int = 3,
        semantic_attempt_limit: int = 2,
    ) -> AuditRecord:
        """Assemble an AuditRecord for ambiguous inbound email classification requiring HITL review."""
        return AuditRecord(
            email_id=email.email_id,
            revision=1,
            previous_revision=None,
            email=email,
            classification=classification,
            state="NEEDS_REVIEW",
            outcome=None,
            mismatch_detected=None,
            result_summary="Review required: Ambiguous email intent",
            documents=[],
            parsers=[],
            extractions=[],
            evidence=dedup_evidence(evidence),
            partial_result=None,
            discrepancies=[],
            review=review_case,
            processing=ProcessingMetadata(
                technical_attempt_limit=technical_attempt_limit,
                semantic_attempt_limit=semantic_attempt_limit,
                attempts=tracker.attempts,
            ),
        )

    @staticmethod
    def build_non_comparison_record(
        email: EmailRecord,
        classification: ClassificationResult,
        tracker: AttemptTracker,
        evidence: Sequence[FieldEvidence],
        technical_attempt_limit: int = 3,
        semantic_attempt_limit: int = 2,
    ) -> AuditRecord:
        """Assemble a terminal COMPLETE record for non-comparison email categories."""
        return AuditRecord(
            email_id=email.email_id,
            revision=1,
            previous_revision=None,
            email=email,
            classification=classification,
            state="COMPLETE",
            outcome="NOT_APPLICABLE",
            mismatch_detected=None,
            result_summary=f"Non-comparison category: {classification.category}",
            documents=[],
            parsers=[],
            extractions=[],
            evidence=dedup_evidence(evidence),
            partial_result=None,
            discrepancies=[],
            review=None,
            processing=ProcessingMetadata(
                technical_attempt_limit=technical_attempt_limit,
                semantic_attempt_limit=semantic_attempt_limit,
                attempts=tracker.attempts,
            ),
        )

    @staticmethod
    def build_escalation_review_record(
        email: EmailRecord,
        classification: ClassificationResult,
        review_case: ReviewCase,
        result_summary: str,
        tracker: AttemptTracker,
        evidence: Sequence[FieldEvidence],
        documents: Sequence[DocumentReference] = (),
        parsers: Sequence[ParserResult] = (),
        extractions: Sequence[DocumentExtraction] = (),
        partial_result: Optional[PartialResult] = None,
        discrepancies: Sequence[Discrepancy] = (),
        technical_attempt_limit: int = 3,
        semantic_attempt_limit: int = 2,
    ) -> AuditRecord:
        """Assemble a general NEEDS_REVIEW AuditRecord for role-binding, unreadable, or missing field escalations."""
        pr = partial_result or PartialResult(
            comparisons=[],
            unresolved_fields=list(FIELD_NAMES),
        )
        return AuditRecord(
            email_id=email.email_id,
            revision=1,
            previous_revision=None,
            email=email,
            classification=classification,
            state="NEEDS_REVIEW",
            outcome=None,
            mismatch_detected=None,
            result_summary=result_summary,
            documents=list(documents),
            parsers=list(parsers),
            extractions=list(extractions),
            evidence=dedup_evidence(evidence),
            partial_result=pr,
            discrepancies=list(discrepancies),
            review=review_case,
            processing=ProcessingMetadata(
                technical_attempt_limit=technical_attempt_limit,
                semantic_attempt_limit=semantic_attempt_limit,
                attempts=tracker.attempts,
            ),
        )

    @staticmethod
    def build_complete_comparison_record(
        email: EmailRecord,
        classification: ClassificationResult,
        outcome: Optional[str],
        mismatch_detected: Optional[bool],
        result_summary: str,
        documents: Sequence[DocumentReference],
        parsers: Sequence[ParserResult],
        extractions: Sequence[DocumentExtraction],
        partial_result: Optional[PartialResult],
        discrepancies: Sequence[Discrepancy],
        tracker: AttemptTracker,
        evidence: Sequence[FieldEvidence],
        technical_attempt_limit: int = 3,
        semantic_attempt_limit: int = 2,
    ) -> AuditRecord:
        """Assemble a terminal COMPLETE AuditRecord following deterministic 7-field comparison."""
        return AuditRecord(
            email_id=email.email_id,
            revision=1,
            previous_revision=None,
            email=email,
            classification=classification,
            state="COMPLETE",
            outcome=outcome,
            mismatch_detected=mismatch_detected,
            result_summary=result_summary,
            documents=list(documents),
            parsers=list(parsers),
            extractions=list(extractions),
            evidence=dedup_evidence(evidence),
            partial_result=partial_result,
            discrepancies=list(discrepancies),
            review=None,
            processing=ProcessingMetadata(
                technical_attempt_limit=technical_attempt_limit,
                semantic_attempt_limit=semantic_attempt_limit,
                attempts=tracker.attempts,
            ),
        )
