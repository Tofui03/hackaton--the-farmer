from __future__ import annotations

import logging
from typing import Optional, Sequence
import uuid

from src.models.document import Role
from src.models.evidence import FieldEvidence
from src.models.extraction import FieldName
from src.models.review import (
    LogicalReason,
    LogicalReasonType,
    RecoveryState,
    ReviewCase,
    ReviewIssue,
    Stage,
    StageType,
)

logger = logging.getLogger(__name__)


class EscalationEngine:
    """Centralized dispatcher and factory for human-in-the-loop review cases (DC-02, FR-013)."""

    def __init__(self, default_attempt_id: str = "att_hitl_1") -> None:
        self.default_attempt_id = default_attempt_id

    def create_missing_attachment_issue(
        self,
        issue_id: Optional[str] = None,
        expected_role: Optional[Role] = None,
        document_ids: Optional[Sequence[str]] = None,
        evidence_ids: Optional[Sequence[str]] = None,
        suggested_action: Optional[str] = None,
        recovery_detail: Optional[str] = None,
        attempt_ids: Optional[Sequence[str]] = None,
        stage: Stage | StageType = Stage.IDENTIFICATION,
    ) -> ReviewIssue:
        """Create ReviewIssue for missing comparison attachment (HITL-RSN-001 / FR-014)."""
        iid = issue_id or f"issue_missing_{expected_role or 'doc'}_{uuid.uuid4().hex[:8]}"
        ev_ids = list(evidence_ids) if evidence_ids else [f"ev_{iid}"]
        role_label = f"draft {expected_role}" if expected_role else "required"
        action = suggested_action or f"Request missing {role_label} attachment from sender"
        detail = recovery_detail or f"Required {role_label} document was absent from email attachments"

        return ReviewIssue(
            issue_id=iid,
            stage=stage,
            logical_reason=LogicalReason.MISSING_ATTACHMENT,
            document_ids=list(document_ids or []),
            expected_role=expected_role,
            fields=[],
            evidence_ids=ev_ids,
            suggested_action=action,
            recovery_state="NOT_APPLICABLE",
            recovery_detail=detail,
            attempt_ids=list(attempt_ids or [self.default_attempt_id]),
        )

    def create_unreadable_document_issue(
        self,
        document_id: str,
        issue_id: Optional[str] = None,
        diagnostic: Optional[str] = None,
        evidence_ids: Optional[Sequence[str]] = None,
        suggested_action: Optional[str] = None,
        recovery_state: RecoveryState = "EXHAUSTED",
        attempt_ids: Optional[Sequence[str]] = None,
        stage: Stage | StageType = Stage.PARSING,
    ) -> ReviewIssue:
        """Create ReviewIssue for corrupted or unreadable document (HITL-RSN-002 / NFR-003)."""
        iid = issue_id or f"issue_unreadable_{document_id}_{uuid.uuid4().hex[:8]}"
        ev_ids = list(evidence_ids) if evidence_ids else [f"ev_{iid}"]
        action = suggested_action or f"Request clean, uncorrupted re-upload of {document_id}"
        detail = diagnostic or f"Document {document_id} could not be rendered or parsed"

        return ReviewIssue(
            issue_id=iid,
            stage=stage,
            logical_reason=LogicalReason.UNREADABLE_DOCUMENT,
            document_ids=[document_id],
            expected_role=None,
            fields=[],
            evidence_ids=ev_ids,
            suggested_action=action,
            recovery_state=recovery_state,
            recovery_detail=detail,
            attempt_ids=list(attempt_ids or [self.default_attempt_id]),
        )

    def create_wrong_or_uncertain_document_type_issue(
        self,
        document_ids: Sequence[str],
        issue_id: Optional[str] = None,
        evidence_ids: Optional[Sequence[str]] = None,
        suggested_action: Optional[str] = None,
        recovery_detail: Optional[str] = None,
        attempt_ids: Optional[Sequence[str]] = None,
        stage: Stage | StageType = Stage.IDENTIFICATION,
    ) -> ReviewIssue:
        """Create ReviewIssue for ambiguous or unverified attachment roles (HITL-RSN-003)."""
        doc_list = list(document_ids)
        iid = issue_id or f"issue_doctype_{uuid.uuid4().hex[:8]}"
        ev_ids = list(evidence_ids) if evidence_ids else [f"ev_{iid}"]
        action = suggested_action or "Review attachments and manually assign SI and BL roles"
        detail = recovery_detail or f"Attachment roles ambiguous or unverified for: {doc_list}"

        return ReviewIssue(
            issue_id=iid,
            stage=stage,
            logical_reason=LogicalReason.WRONG_OR_UNCERTAIN_DOCUMENT_TYPE,
            document_ids=doc_list,
            expected_role=None,
            fields=[],
            evidence_ids=ev_ids,
            suggested_action=action,
            recovery_state="NOT_APPLICABLE",
            recovery_detail=detail,
            attempt_ids=list(attempt_ids or [self.default_attempt_id]),
        )

    def create_missing_required_value_issue(
        self,
        document_id: str,
        field: FieldName,
        issue_id: Optional[str] = None,
        evidence_ids: Optional[Sequence[str]] = None,
        suggested_action: Optional[str] = None,
        recovery_detail: Optional[str] = None,
        attempt_ids: Optional[Sequence[str]] = None,
        stage: Stage | StageType = Stage.EXTRACTION,
    ) -> ReviewIssue:
        """Create ReviewIssue for mandatory field missing from document (HITL-RSN-004)."""
        iid = issue_id or f"issue_missing_field_{field}_{uuid.uuid4().hex[:8]}"
        ev_ids = list(evidence_ids) if evidence_ids else [f"ev_{iid}"]
        action = suggested_action or f"Inspect {document_id} to supply missing mandatory field '{field}'"
        detail = recovery_detail or f"Mandatory comparison field '{field}' was not found in {document_id}"

        return ReviewIssue(
            issue_id=iid,
            stage=stage,
            logical_reason=LogicalReason.MISSING_REQUIRED_VALUE,
            document_ids=[document_id],
            expected_role=None,
            fields=[field],
            evidence_ids=ev_ids,
            suggested_action=action,
            recovery_state="NOT_APPLICABLE",
            recovery_detail=detail,
            attempt_ids=list(attempt_ids or [self.default_attempt_id]),
        )

    def create_uncertain_result_issue(
        self,
        document_ids: Sequence[str],
        fields: Optional[Sequence[FieldName]] = None,
        issue_id: Optional[str] = None,
        evidence_ids: Optional[Sequence[str]] = None,
        suggested_action: Optional[str] = None,
        recovery_detail: Optional[str] = None,
        attempt_ids: Optional[Sequence[str]] = None,
        stage: Stage | StageType = Stage.EXTRACTION,
    ) -> ReviewIssue:
        """Create ReviewIssue for ambiguous or low-confidence results (HITL-RSN-005)."""
        iid = issue_id or f"issue_uncertain_{uuid.uuid4().hex[:8]}"
        ev_ids = list(evidence_ids) if evidence_ids else [f"ev_{iid}"]
        action = suggested_action or "Review extracted field candidates to resolve uncertainty"
        detail = recovery_detail or "Extraction or comparison confidence below reliable threshold"

        return ReviewIssue(
            issue_id=iid,
            stage=stage,
            logical_reason=LogicalReason.UNCERTAIN_RESULT,
            document_ids=list(document_ids),
            expected_role=None,
            fields=list(fields or []),
            evidence_ids=ev_ids,
            suggested_action=action,
            recovery_state="UNRELIABLE",
            recovery_detail=detail,
            attempt_ids=list(attempt_ids or [self.default_attempt_id]),
        )

    def create_conflicting_candidate_values_issue(
        self,
        document_id: str,
        field: FieldName,
        candidates: Sequence[str],
        issue_id: Optional[str] = None,
        evidence_ids: Optional[Sequence[str]] = None,
        suggested_action: Optional[str] = None,
        recovery_detail: Optional[str] = None,
        attempt_ids: Optional[Sequence[str]] = None,
        stage: Stage | StageType = Stage.EXTRACTION,
    ) -> ReviewIssue:
        """Create ReviewIssue for multiple conflicting candidate values in document (HITL-RSN-006)."""
        iid = issue_id or f"issue_conflicting_{field}_{uuid.uuid4().hex[:8]}"
        ev_ids = list(evidence_ids) if evidence_ids else [f"ev_{iid}"]
        cand_str = ", ".join(f"'{c}'" for c in candidates)
        action = suggested_action or f"Select authoritative candidate for '{field}' from conflicting options: {cand_str}"
        detail = recovery_detail or f"Multiple conflicting candidate values extracted for '{field}': {cand_str}"

        return ReviewIssue(
            issue_id=iid,
            stage=stage,
            logical_reason=LogicalReason.CONFLICTING_CANDIDATE_VALUES,
            document_ids=[document_id],
            expected_role=None,
            fields=[field],
            evidence_ids=ev_ids,
            suggested_action=action,
            recovery_state="UNRELIABLE",
            recovery_detail=detail,
            attempt_ids=list(attempt_ids or [self.default_attempt_id]),
        )

    def create_processing_or_provider_failure_issue(
        self,
        stage: Stage | StageType,
        document_ids: Sequence[str],
        error_detail: str,
        issue_id: Optional[str] = None,
        fields: Optional[Sequence[FieldName]] = None,
        evidence_ids: Optional[Sequence[str]] = None,
        suggested_action: Optional[str] = None,
        recovery_state: RecoveryState = "EXHAUSTED",
        attempt_ids: Optional[Sequence[str]] = None,
    ) -> ReviewIssue:
        """Create ReviewIssue for OCR/AI provider timeout or retry exhaustion (HITL-RSN-007 / FR-017)."""
        iid = issue_id or f"issue_provider_fail_{uuid.uuid4().hex[:8]}"
        ev_ids = list(evidence_ids) if evidence_ids else [f"ev_{iid}"]
        action = suggested_action or "Check AI provider health logs or retry processing manually"

        return ReviewIssue(
            issue_id=iid,
            stage=stage,
            logical_reason=LogicalReason.PROCESSING_OR_PROVIDER_FAILURE,
            document_ids=list(document_ids),
            expected_role=None,
            fields=list(fields or []),
            evidence_ids=ev_ids,
            suggested_action=action,
            recovery_state=recovery_state,
            recovery_detail=error_detail,
            attempt_ids=list(attempt_ids or [self.default_attempt_id]),
        )

    def dispatch_issue(
        self,
        reason: LogicalReason | LogicalReasonType,
        stage: Stage | StageType,
        document_ids: Sequence[str],
        evidence_ids: Sequence[str],
        suggested_action: str,
        recovery_detail: str,
        fields: Optional[Sequence[FieldName]] = None,
        expected_role: Optional[Role] = None,
        recovery_state: RecoveryState = "NOT_APPLICABLE",
        attempt_ids: Optional[Sequence[str]] = None,
        issue_id: Optional[str] = None,
    ) -> ReviewIssue:
        """Generic dispatcher building a validated ReviewIssue for any LogicalReason."""
        iid = issue_id or f"issue_{reason}_{uuid.uuid4().hex[:8]}"
        return ReviewIssue(
            issue_id=iid,
            stage=stage,
            logical_reason=reason,
            document_ids=list(document_ids),
            expected_role=expected_role,
            fields=list(fields or []),
            evidence_ids=list(evidence_ids),
            suggested_action=suggested_action,
            recovery_state=recovery_state,
            recovery_detail=recovery_detail,
            attempt_ids=list(attempt_ids or [self.default_attempt_id]),
        )

    def build_review_case(
        self,
        review_id: str,
        issues: Sequence[ReviewIssue],
    ) -> ReviewCase:
        """Assemble an open ReviewCase containing at least one ReviewIssue."""
        if not issues:
            raise ValueError("ReviewCase requires at least one ReviewIssue")
        return ReviewCase(
            review_id=review_id,
            state="OPEN",
            issues=list(issues),
        )
