from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal, Self
from pydantic import Field, model_validator
from src.models.base import Contract, Text, require
from src.models.comparison import (
    ComparisonOutcome,
    Discrepancy,
    FieldComparison,
    OutcomeType,
    PartialResult,
)
from src.models.document import DocumentReference, ParserResult
from src.models.evidence import FieldEvidence
from src.models.extraction import DocumentExtraction, FIELD_NAMES, FieldName
from src.models.ingestion import ClassificationResult, EmailRecord
from src.models.review import ReviewCase, Stage, StageType


class AuditState(str, Enum):
    """Authoritative audit record workflow states."""

    COMPLETE = "COMPLETE"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class WorkflowState(str, Enum):
    """Extended pipeline workflow states for tracking."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETE = "COMPLETE"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    FAILED = "FAILED"


class AttemptRecord(Contract):
    """Monotonically increasing execution attempt within an operation (DC-06)."""

    attempt_id: Text
    operation_id: Text
    stage: Stage | StageType
    kind: Literal["primary", "technical_retry", "semantic_repair", "fallback", "ocr"]
    attempt_number: Annotated[int, Field(ge=1)]
    outcome: Literal["SUCCEEDED", "FAILED", "INVALID"]
    error_code: str | None = None
    provider_adapter: str | None = None
    model_identifier: str | None = None
    prompt_version: str | None = None
    token_usage: dict[str, Annotated[int, Field(ge=0)]] | None = None
    latency_ms: Annotated[int, Field(ge=0)] | None = None


class ProcessingMetadata(Contract):
    """Operational attempt tracking and bounded retry limits (DC-06).

    Authoritative semantics (03_DATA_CONTRACTS.md §6 & 02_AI_PIPELINE_SPEC.md):
    - technical_attempt_limit default: 3
    - semantic_attempt_limit default: 2
    - Both include the initial attempt.
    - Maximum nested provider invocation budget cap: 6 (technical_limit * semantic_limit <= 6).
    """

    technical_attempt_limit: Annotated[int, Field(ge=1)] = 3
    semantic_attempt_limit: Annotated[int, Field(ge=1)] = 2
    attempts: list[AttemptRecord]

    @property
    def total_provider_calls(self) -> int:
        return len(self.attempts)

    @property
    def total_budget(self) -> int:
        return self.technical_attempt_limit * self.semantic_attempt_limit

    @model_validator(mode="after")
    def validate_budget_cap(self) -> Self:
        require(
            self.technical_attempt_limit * self.semantic_attempt_limit <= 6,
            "nested provider invocation budget (technical_attempt_limit * semantic_attempt_limit) cannot exceed 6",
        )
        return self


class AttemptTracker(Contract):
    """Diagnostic tracking model for stage retries and budgets."""

    technical_attempt_limit: Annotated[int, Field(ge=1)] = 3
    semantic_attempt_limit: Annotated[int, Field(ge=1)] = 2
    attempts: list[AttemptRecord] = Field(default_factory=list)
    total_provider_calls: Annotated[int, Field(ge=0)] = 0

    @property
    def total_budget(self) -> int:
        return self.technical_attempt_limit * self.semantic_attempt_limit

    @model_validator(mode="after")
    def validate_budget_cap(self) -> Self:
        require(
            self.technical_attempt_limit * self.semantic_attempt_limit <= 6,
            "nested provider invocation budget (technical_attempt_limit * semantic_attempt_limit) cannot exceed 6",
        )
        require(
            self.total_provider_calls <= 6,
            "total_provider_calls cannot exceed the cap of 6",
        )
        return self


class DynamicVerifyRequest(Contract):
    """On-demand verification payload for ad-hoc SI and BL text.

    Authoritative contract citation: 03_DATA_CONTRACTS.md §3.1, line 437.
    """

    email_id: Text = "example-on-demand"
    si_text: str
    bl_text: str


class ErrorResponse(Contract):
    """Structured error payload for failed requests or blocked exports (DC-08)."""

    code: Text
    message: Text
    details: list[str]
    retryable: bool
    blocking_emails: list[str] | None = None

    @property
    def email_ids(self) -> list[str]:
        if self.blocking_emails:
            return self.blocking_emails
        emails = []
        for d in self.details:
            if ":" in d:
                emails.append(d.split(":", 1)[0].strip())
        return emails


class SubmissionRecord(Contract):
    """External evaluation format strictly matching official schema (DC-08)."""

    category: Literal["BL_COMPARISON", "SI_REQUEST", "INVOICE_QUERY", "GENERAL", "SPAM"]
    status: Literal["OK", "MISMATCH", "NEEDS_REVIEW"]
    review_reason: str | None = None
    has_defect: bool
    defect_fields: list[FieldName]

    @model_validator(mode="after")
    def evaluation_invariants(self) -> Self:
        require(len(self.defect_fields) == len(set(self.defect_fields)), "duplicate defect fields")
        if self.category != "BL_COMPARISON":
            require(self.status == "OK", "non-comparison evaluation record uses OK sentinel")
        if self.status == "MISMATCH":
            require(
                self.category == "BL_COMPARISON"
                and self.has_defect
                and bool(self.defect_fields)
                and self.review_reason is None,
                "invalid mismatch submission",
            )
        else:
            require(
                not self.has_defect and not self.defect_fields,
                "non-mismatch submission cannot claim definitive defects",
            )
            require(
                (self.review_reason is not None) == (self.status == "NEEDS_REVIEW"),
                "review reason/status mismatch",
            )
        return self


class AuditRecord(Contract):
    """Comprehensive, verifiable audit report for a processed email."""

    schema_version: Literal["1.0-draft"] = "1.0-draft"
    email_id: Text
    revision: Annotated[int, Field(ge=1)]
    previous_revision: Annotated[int, Field(ge=1)] | None = None
    email: EmailRecord
    classification: ClassificationResult
    state: Literal["COMPLETE", "NEEDS_REVIEW"]
    outcome: OutcomeType | None
    mismatch_detected: bool | None
    result_summary: Text
    documents: list[DocumentReference]
    parsers: list[ParserResult]
    extractions: list[DocumentExtraction]
    evidence: list[FieldEvidence]
    partial_result: PartialResult | None
    discrepancies: list[Discrepancy]
    review: ReviewCase | None
    processing: ProcessingMetadata

    @model_validator(mode="after")
    def audit_invariants(self) -> Self:
        require(self.email_id == self.email.email_id, "email identity mismatch")
        require(
            self.previous_revision is None or self.previous_revision < self.revision,
            "invalid revision lineage",
        )
        evidence = {e.evidence_id: e for e in self.evidence}
        require(len(evidence) == len(self.evidence), "duplicate evidence ID")
        attachments = {a.document_id for a in self.email.attachments}
        require(len(attachments) == len(self.email.attachments), "duplicate attachment ID")
        documents = {d.document_id: d for d in self.documents}
        require(len(documents) == len(self.documents), "duplicate document reference")
        require(set(documents) <= attachments, "document reference must identify an attachment")
        attempts = {a.attempt_id for a in self.processing.attempts}
        require(len(attempts) == len(self.processing.attempts), "duplicate attempt ID")

        def refs(ids: list[str]) -> None:
            require(set(ids) <= set(evidence), "dangling evidence reference")

        refs(self.classification.evidence_ids)
        for d in self.documents:
            refs(d.identification_evidence_ids)
        for p in self.parsers:
            require(p.document_id in documents, "parser source missing")
            refs(p.diagnostic_evidence_ids)
            require(set(p.attempt_ids) <= attempts, "parser attempt missing")

        by_role: dict[str, DocumentExtraction] = {}
        for extraction in self.extractions:
            require(
                extraction.document_id in documents
                and documents[extraction.document_id].role == extraction.role,
                "extraction document/role mismatch",
            )
            require(extraction.role not in by_role, "ambiguous roles cannot enter trusted extraction")
            by_role[extraction.role] = extraction
            for f in extraction.fields.values():
                for candidate in f.candidates:
                    refs(candidate.evidence_ids)
                if f.reliability == "RELIABLE":
                    require(f.selected_candidate is not None, "reliable field requires selection")
                    selected = f.candidates[f.selected_candidate]
                    require(
                        any(
                            evidence[e].source_type == "document"
                            and evidence[e].source_id == extraction.document_id
                            and evidence[e].kind != "processing_error"
                            for e in selected.evidence_ids
                        ),
                        "reliable value lacks evidence from its document",
                    )

        for item in self.evidence:
            if item.source_type == "document":
                require(item.source_id in attachments, "evidence document missing")
            if item.source_type == "email":
                require(item.source_id == self.email_id, "evidence email mismatch")

        if self.review is not None:
            for issue in self.review.issues:
                refs(issue.evidence_ids)
                require(set(issue.document_ids) <= attachments, "review document missing")
                require(set(issue.attempt_ids) <= attempts, "review attempt missing")

        category = self.classification.category
        if category != "document_comparison":
            require(
                not self.documents
                and not self.parsers
                and not self.extractions
                and self.partial_result is None
                and not self.discrepancies,
                "non-comparison/unresolved intent must not process attachments",
            )
        else:
            require(self.partial_result is not None, "comparison request requires explicit partial state")
            eligible: dict[str, tuple[object, object]] = {}
            if "SI" in by_role and "BL" in by_role:
                for field in FIELD_NAMES:
                    si, bl = by_role["SI"].fields[field], by_role["BL"].fields[field]
                    if (
                        si.reliability == "RELIABLE"
                        and bl.reliability == "RELIABLE"
                        and si.normalized is not None
                        and bl.normalized is not None
                    ):
                        eligible[field] = (si.normalized.value, bl.normalized.value)
            comparisons = {c.field: c for c in self.partial_result.comparisons}
            require(
                set(comparisons) == set(eligible),
                "all and only reliable pairs must retain comparisons",
            )
            for field, comparison in comparisons.items():
                require(
                    (comparison.si_value, comparison.bl_value) == eligible[field],
                    "comparison differs from normalized source values",
                )
            expected = [
                (c.field, c.si_value, c.bl_value)
                for c in self.partial_result.comparisons
                if c.outcome == "MISMATCH"
            ]
            require(
                [(d.field, d.si_value, d.bl_value) for d in self.discrepancies] == expected,
                "discrepancies must exactly preserve confirmed inequalities",
            )

        if self.state == "NEEDS_REVIEW":
            require(
                self.outcome is None and self.mismatch_detected is None,
                "review is not a final outcome",
            )
            require(
                self.review is not None and self.review.state == "OPEN",
                "review state requires an open case",
            )
            require(
                self.result_summary != "No mismatch detected",
                "unresolved case cannot receive a clean pass",
            )
        else:
            require(self.classification.state == "RESOLVED", "complete audit needs resolved category")
            require(
                self.review is None or self.review.state == "RESOLVED",
                "complete audit has open review",
            )
            if category == "document_comparison":
                require(
                    not self.partial_result.unresolved_fields,
                    "complete comparison requires all seven pairs",
                )
                expected_outcome = "MISMATCH" if self.discrepancies else "MATCH"
                require(
                    self.outcome == expected_outcome
                    and self.mismatch_detected == bool(self.discrepancies),
                    "incorrect final outcome",
                )
                if expected_outcome == "MATCH":
                    require(
                        self.result_summary == "No mismatch detected",
                        "match summary must be exact",
                    )
            else:
                require(
                    self.outcome == "NOT_APPLICABLE" and self.mismatch_detected is None,
                    "non-comparison is not a clean comparison",
                )
                require(
                    self.result_summary != "No mismatch detected",
                    "non-comparison summary implies checking occurred",
                )
        return self
