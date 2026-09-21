from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal, Self
from pydantic import Field, model_validator
from src.models.base import Contract, Text
from src.models.document import Role
from src.models.evidence import FieldEvidence
from src.models.extraction import FieldName
from src.models.ingestion import Category


class LogicalReason(str, Enum):
    """Internal 7-value HITL logical reason taxonomy (DC-02)."""

    MISSING_ATTACHMENT = "missing_attachment"
    UNREADABLE_DOCUMENT = "unreadable_document"
    WRONG_OR_UNCERTAIN_DOCUMENT_TYPE = "wrong_or_uncertain_document_type"
    MISSING_REQUIRED_VALUE = "missing_required_value"
    UNCERTAIN_RESULT = "uncertain_result"
    CONFLICTING_CANDIDATE_VALUES = "conflicting_candidate_values"
    PROCESSING_OR_PROVIDER_FAILURE = "processing_or_provider_failure"


LogicalReasonType = Literal[
    "missing_attachment",
    "unreadable_document",
    "wrong_or_uncertain_document_type",
    "missing_required_value",
    "uncertain_result",
    "conflicting_candidate_values",
    "processing_or_provider_failure",
]


class ReviewAction(str, Enum):
    """Human review update action."""

    CONFIRM = "CONFIRM"
    CORRECT = "CORRECT"


ActionType = Literal["CONFIRM", "CORRECT"]


class Stage(str, Enum):
    """Workflow processing stages."""

    INGESTION = "ingestion"
    CLASSIFICATION = "classification"
    IDENTIFICATION = "identification"
    PARSING = "parsing"
    OCR = "ocr"
    EXTRACTION = "extraction"
    NORMALIZATION = "normalization"
    RELIABILITY = "reliability"
    COMPARISON = "comparison"
    REVIEW = "review"
    SERIALIZATION = "serialization"


StageType = Literal[
    "ingestion",
    "classification",
    "identification",
    "parsing",
    "ocr",
    "extraction",
    "normalization",
    "reliability",
    "comparison",
    "review",
    "serialization",
]


RecoveryState = Literal["NOT_APPLICABLE", "UNAVAILABLE", "EXHAUSTED", "UNRELIABLE"]


class FieldCorrection(Contract):
    """Correction applied by human reviewer to a specific document field."""

    document_id: Text
    field: FieldName
    raw_value: Text
    evidence_ids: Annotated[list[Text], Field(min_length=1)]
    rationale: Text


class RoleCorrection(Contract):
    """Correction applied by human reviewer to a document's assigned role."""

    document_id: Text
    assigned_role: Literal["SI", "BL", "UNKNOWN"]
    evidence_ids: Annotated[list[Text], Field(min_length=1)]
    rationale: Text


class ReviewIssue(Contract):
    """A specific issue requiring human review."""

    issue_id: Text
    stage: Stage | StageType
    logical_reason: LogicalReason | LogicalReasonType
    evaluation_reason: str | None = None
    document_ids: list[Text]
    expected_role: Role | None = None
    fields: list[FieldName]
    evidence_ids: Annotated[list[Text], Field(min_length=1)]
    suggested_action: Text
    recovery_state: RecoveryState
    recovery_detail: Text
    attempt_ids: list[Text]


class ReviewCase(Contract):
    """Structured human review case containing one or more issues."""

    review_id: Text
    state: Literal["OPEN", "RESOLVED"]
    issues: Annotated[list[ReviewIssue], Field(min_length=1)]


class ReviewUpdate(Contract):
    """Human review mutation payload. Forbids direct mismatch/outcome mutation (REG-012)."""

    review_id: Text
    expected_revision: Annotated[int, Field(ge=1)]
    actor_id: Text
    action: ReviewAction | ActionType
    rationale: Text
    category: Category | None = None
    classification_evidence_ids: list[Text] = Field(default_factory=list)
    role_corrections: list[RoleCorrection] = Field(default_factory=list)
    corrections: list[FieldCorrection] = Field(default_factory=list)
    added_evidence: list[FieldEvidence] = Field(default_factory=list)

    @model_validator(mode="after")
    def review_update_invariants(self) -> Self:
        doc_roles: dict[str, str] = {}
        for rc in self.role_corrections:
            if rc.document_id in doc_roles and doc_roles[rc.document_id] != rc.assigned_role:
                raise ValueError("cannot assign conflicting roles to the same document")
            doc_roles[rc.document_id] = rc.assigned_role
        return self
