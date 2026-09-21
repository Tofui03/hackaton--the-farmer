from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

from src.llm.base_adapter import BaseAIAdapter
from src.llm.schemas import DocumentRoleResolutionOutput
from src.models.audit import AttemptTracker
from src.models.base import Contract, Text
from src.models.document import DocumentReference, DocumentRole, ParserResult, ParserStatus, Role
from src.models.evidence import FieldEvidence
from src.models.ingestion import AttachmentReference, EmailRecord
from src.models.review import LogicalReason, LogicalReasonType, RecoveryState, ReviewIssue, Stage
from src.parsers import parse_document

logger = logging.getLogger(__name__)


class RoleBindingResult(Contract):
    """Structured output from Stage 2 attachment identification and role binding."""

    state: Literal["RESOLVED", "NEEDS_REVIEW"]
    si_doc: Optional[DocumentReference] = None
    bl_doc: Optional[DocumentReference] = None
    documents: List[DocumentReference] = []
    evidence: List[FieldEvidence] = []
    review_issue: Optional[ReviewIssue] = None
    logical_reason: Optional[LogicalReason | LogicalReasonType] = None
    reason_detail: Optional[str] = None


def _normalize_attachment_list(
    attachments: Union[EmailRecord, List[Any]],
    base_dir: Optional[Path] = None,
) -> List[Tuple[str, str, Optional[Path]]]:
    """Extract list of (document_id, path_str, resolved_path) from various input forms."""
    raw_list: List[Any] = []
    if isinstance(attachments, EmailRecord):
        raw_list = attachments.attachments
    elif isinstance(attachments, dict):
        raw_list = attachments.get("attachments", [])
    elif isinstance(attachments, list):
        raw_list = attachments
    else:
        raw_list = getattr(attachments, "attachments", [attachments])

    normalized: List[Tuple[str, str, Optional[Path]]] = []
    for a in raw_list:
        if isinstance(a, AttachmentReference):
            doc_id = str(a.document_id)
            path_str = str(a.path)
        elif isinstance(a, dict):
            doc_id = str(a.get("document_id", a.get("path", "doc")))
            path_str = str(a.get("path", doc_id))
        elif isinstance(a, (str, Path)):
            path_str = str(a)
            doc_id = Path(path_str).name
        else:
            doc_id = str(getattr(a, "document_id", getattr(a, "path", str(a))))
            path_str = str(getattr(a, "path", doc_id))

        resolved: Optional[Path] = None
        if base_dir is not None:
            candidate = base_dir / path_str
            if candidate.exists():
                resolved = candidate
        if resolved is None and Path(path_str).exists():
            resolved = Path(path_str)

        normalized.append((doc_id, path_str, resolved))

    return normalized


def _classify_single_attachment_deterministically(
    doc_id: str,
    path_str: str,
    resolved_path: Optional[Path] = None,
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Determine role ('SI', 'BL', 'IRRELEVANT', or None) and header snippet for an attachment.
    
    Returns:
        (detected_role, evidence_snippet, error_state)
    """
    name_upper = Path(path_str).name.upper()

    # Check for irrelevant types first (PAR-ROLE-007)
    irrelevant_keywords = [
        "PACKING LIST",
        "PACKING_LIST",
        "COMMERCIAL INVOICE",
        "COMMERCIAL_INVOICE",
        "CUSTOMS INVOICE",
        "CERTIFICATE OF ORIGIN",
    ]
    for kw in irrelevant_keywords:
        if kw in name_upper:
            return "IRRELEVANT", f"Filename contains irrelevant document type: '{kw}'", None

    # Check for corrupt stream if file exists on disk (PAR-ROLE-008, NFR-003)
    content_text: Optional[str] = None
    if resolved_path is not None and resolved_path.exists():
        parse_res = parse_document(resolved_path, document_id=doc_id)
        if parse_res.status == ParserStatus.UNREADABLE or not parse_res.usable_for_extraction:
            return None, None, f"Corrupted or unreadable stream: {parse_res.error_message or 'unreadable'}"
        content_text = (parse_res.clean_text or parse_res.text or "").strip()

    # Check content text for irrelevant document type (PAR-ROLE-007)
    if content_text:
        content_head_upper = content_text[:2000].upper()
        for kw in irrelevant_keywords:
            if kw in content_head_upper:
                return "IRRELEVANT", f"Document header specifies irrelevant type: '{kw}'", None

    # Filename patterns for SI (PAR-ROLE-001)
    si_name_patterns = ["_SI.", "_SI_", "SHIPPING INSTRUCTION", "SHIPPING_INSTRUCTION"]
    if any(p in name_upper for p in si_name_patterns) or name_upper.startswith("SI_") or name_upper.startswith("SI."):
        return "SI", f"Filename convention matched SI: '{Path(path_str).name}'", None

    # Filename patterns for BL (PAR-ROLE-001)
    bl_name_patterns = ["_BL.", "_BL_", "BILL OF LADING", "BILL_OF_LADING", "DRAFT BL", "DRAFT_BL"]
    if any(p in name_upper for p in bl_name_patterns) or name_upper.startswith("BL_") or name_upper.startswith("BL."):
        return "BL", f"Filename convention matched Draft BL: '{Path(path_str).name}'", None

    # Content header inspection if generic filename (PAR-ROLE-002)
    if content_text:
        head_upper = content_text[:2000].upper()
        if "SHIPPING INSTRUCTION" in head_upper:
            return "SI", "Document header text indicates 'SHIPPING INSTRUCTION'", None
        if "BILL OF LADING" in head_upper or "DRAFT B/L" in head_upper or "DRAFT BILL OF LADING" in head_upper:
            return "BL", "Document header text indicates 'BILL OF LADING'", None

    return None, None, None


class Stage2RoleBinder:
    """Binds attachments to SI and Draft BL roles with deterministic-first rules and AI-on-demand (T09-01, T09-02)."""

    def __init__(
        self,
        base_dir: Optional[Path] = None,
        ai_adapter: Optional[BaseAIAdapter] = None,
    ):
        self.base_dir = Path(base_dir) if base_dir else None
        self.ai_adapter = ai_adapter

    def bind_roles(
        self,
        attachments: Union[EmailRecord, List[Any]],
        tracker: Optional[AttemptTracker] = None,
        operation_id: str = "role_binding",
    ) -> RoleBindingResult:
        """Execute role binding and return RoleBindingResult or structured HITL ReviewIssue."""
        items = _normalize_attachment_list(attachments, base_dir=self.base_dir)

        # 1. Zero Attachments Check (PAR-ROLE-003/004, HITL-RSN-001)
        if not items:
            ev = FieldEvidence(
                evidence_id="ev_role_err_no_attachments",
                source_type="processing",
                source_id="email",
                kind="processing_error",
                detail="Expected SI and BL attachments, but attachments list is empty",
            )
            issue = ReviewIssue(
                issue_id=f"issue_{operation_id}_missing_all",
                stage=Stage.IDENTIFICATION,
                logical_reason=LogicalReason.MISSING_ATTACHMENT,
                document_ids=[],
                expected_role=None,
                fields=[],
                evidence_ids=[ev.evidence_id],
                suggested_action="Request SI and draft BL attachments from sender",
                recovery_state="NOT_APPLICABLE",
                recovery_detail="Zero attachments provided in email record",
                attempt_ids=[f"att_{operation_id}_1"],
            )
            return RoleBindingResult(
                state="NEEDS_REVIEW",
                review_issue=issue,
                logical_reason=LogicalReason.MISSING_ATTACHMENT,
                reason_detail="Zero attachments found",
                evidence=[ev],
            )

        # 2. Duplicate Self-Collision Check (PAR-ROLE-006)
        # If the same file is passed multiple times or same ID attempted for both roles
        unique_paths = {path_str for _, path_str, _ in items}
        unique_ids = {doc_id for doc_id, _, _ in items}
        if len(items) >= 2 and (len(unique_paths) < len(items) or len(unique_ids) < len(items)):
            ev = FieldEvidence(
                evidence_id="ev_role_err_same_file",
                source_type="processing",
                source_id=items[0][0],
                kind="processing_error",
                detail="Single attachment attempted for multiple comparison roles",
            )
            issue = ReviewIssue(
                issue_id=f"issue_{operation_id}_same_file",
                stage=Stage.IDENTIFICATION,
                logical_reason=LogicalReason.WRONG_OR_UNCERTAIN_DOCUMENT_TYPE,
                document_ids=list(unique_ids),
                expected_role=None,
                fields=[],
                evidence_ids=[ev.evidence_id],
                suggested_action="Reject duplicate attachment pairing; require distinct SI and BL documents",
                recovery_state="NOT_APPLICABLE",
                recovery_detail="Identical attachment file supplied for both comparison roles",
                attempt_ids=[f"att_{operation_id}_1"],
            )
            return RoleBindingResult(
                state="NEEDS_REVIEW",
                review_issue=issue,
                logical_reason=LogicalReason.WRONG_OR_UNCERTAIN_DOCUMENT_TYPE,
                reason_detail="Same file attempted for both SI and BL roles",
                evidence=[ev],
            )

        # 3. Deterministic / Usability Analysis per Attachment
        si_candidates: List[Tuple[str, str, str]] = []  # (doc_id, path_str, evidence)
        bl_candidates: List[Tuple[str, str, str]] = []
        irrelevant_candidates: List[Tuple[str, str, str]] = []
        unknown_candidates: List[Tuple[str, str]] = []

        for doc_id, path_str, resolved in items:
            role, ev_snippet, err = _classify_single_attachment_deterministically(
                doc_id=doc_id,
                path_str=path_str,
                resolved_path=resolved,
            )

            # Check for corrupt stream (PAR-ROLE-008, NFR-003, HITL-RSN-002)
            if err is not None:
                ev = FieldEvidence(
                    evidence_id=f"ev_role_corrupt_{doc_id}",
                    source_type="document",
                    source_id=doc_id,
                    kind="processing_error",
                    detail=err,
                )
                issue = ReviewIssue(
                    issue_id=f"issue_{operation_id}_corrupt_{doc_id}",
                    stage=Stage.IDENTIFICATION,
                    logical_reason=LogicalReason.UNREADABLE_DOCUMENT,
                    document_ids=[doc_id],
                    expected_role=None,
                    fields=[],
                    evidence_ids=[ev.evidence_id],
                    suggested_action=f"Request clean, uncorrupted re-submission of document {doc_id}",
                    recovery_state="UNRELIABLE",
                    recovery_detail=err,
                    attempt_ids=[f"att_{operation_id}_corrupt"],
                )
                return RoleBindingResult(
                    state="NEEDS_REVIEW",
                    review_issue=issue,
                    logical_reason=LogicalReason.UNREADABLE_DOCUMENT,
                    reason_detail=err,
                    evidence=[ev],
                )

            if role == "SI":
                si_candidates.append((doc_id, path_str, ev_snippet or "SI pattern"))
            elif role == "BL":
                bl_candidates.append((doc_id, path_str, ev_snippet or "BL pattern"))
            elif role == "IRRELEVANT":
                irrelevant_candidates.append((doc_id, path_str, ev_snippet or "Irrelevant type"))
            else:
                unknown_candidates.append((doc_id, path_str))

        # 4. Irrelevant Document Check (PAR-ROLE-007)
        if irrelevant_candidates and (not si_candidates or not bl_candidates):
            irr_doc_id, _, irr_ev = irrelevant_candidates[0]
            ev = FieldEvidence(
                evidence_id=f"ev_role_irr_{irr_doc_id}",
                source_type="document",
                source_id=irr_doc_id,
                kind="document_metadata",
                detail=irr_ev,
            )
            issue = ReviewIssue(
                issue_id=f"issue_{operation_id}_irrelevant_{irr_doc_id}",
                stage=Stage.IDENTIFICATION,
                logical_reason=LogicalReason.WRONG_OR_UNCERTAIN_DOCUMENT_TYPE,
                document_ids=[irr_doc_id],
                expected_role=None,
                fields=[],
                evidence_ids=[ev.evidence_id],
                suggested_action="Reject irrelevant document (packing list/invoice); request valid Draft BL",
                recovery_state="NOT_APPLICABLE",
                recovery_detail=f"Attachment {irr_doc_id} identified as irrelevant type",
                attempt_ids=[f"att_{operation_id}_irr"],
            )
            return RoleBindingResult(
                state="NEEDS_REVIEW",
                review_issue=issue,
                logical_reason=LogicalReason.WRONG_OR_UNCERTAIN_DOCUMENT_TYPE,
                reason_detail="Irrelevant attachment type detected",
                evidence=[ev],
            )

        # 5. Single Attachment Check (PAR-ROLE-003, PAR-ROLE-004, HITL-RSN-001)
        if len(items) == 1:
            doc_id, _, _ = items[0]
            if bl_candidates and not si_candidates:
                # BL attached, SI missing (PAR-ROLE-003)
                ev = FieldEvidence(
                    evidence_id="ev_role_missing_si",
                    source_type="processing",
                    source_id=doc_id,
                    kind="processing_error",
                    detail="Draft BL attached, but Shipping Instruction (SI) is missing",
                )
                issue = ReviewIssue(
                    issue_id=f"issue_{operation_id}_missing_si",
                    stage=Stage.IDENTIFICATION,
                    logical_reason=LogicalReason.MISSING_ATTACHMENT,
                    document_ids=[doc_id],
                    expected_role=DocumentRole.SI,
                    fields=[],
                    evidence_ids=[ev.evidence_id],
                    suggested_action="Request missing Shipping Instruction (SI) attachment from sender",
                    recovery_state="NOT_APPLICABLE",
                    recovery_detail="Only Draft BL attached; SI is absent",
                    attempt_ids=[f"att_{operation_id}_miss_si"],
                )
                return RoleBindingResult(
                    state="NEEDS_REVIEW",
                    review_issue=issue,
                    logical_reason=LogicalReason.MISSING_ATTACHMENT,
                    reason_detail="SI missing from comparison pair",
                    evidence=[ev],
                )
            elif si_candidates and not bl_candidates:
                # SI attached, BL missing (PAR-ROLE-004)
                ev = FieldEvidence(
                    evidence_id="ev_role_missing_bl",
                    source_type="processing",
                    source_id=doc_id,
                    kind="processing_error",
                    detail="Shipping Instruction (SI) attached, but Draft BL is missing",
                )
                issue = ReviewIssue(
                    issue_id=f"issue_{operation_id}_missing_bl",
                    stage=Stage.IDENTIFICATION,
                    logical_reason=LogicalReason.MISSING_ATTACHMENT,
                    document_ids=[doc_id],
                    expected_role=DocumentRole.BL,
                    fields=[],
                    evidence_ids=[ev.evidence_id],
                    suggested_action="Request missing Draft Bill of Lading (BL) attachment from sender",
                    recovery_state="NOT_APPLICABLE",
                    recovery_detail="Only SI attached; Draft BL is absent",
                    attempt_ids=[f"att_{operation_id}_miss_bl"],
                )
                return RoleBindingResult(
                    state="NEEDS_REVIEW",
                    review_issue=issue,
                    logical_reason=LogicalReason.MISSING_ATTACHMENT,
                    reason_detail="Draft BL missing from comparison pair",
                    evidence=[ev],
                )
            else:
                # Single unknown attachment
                ev = FieldEvidence(
                    evidence_id="ev_role_single_unknown",
                    source_type="processing",
                    source_id=doc_id,
                    kind="processing_error",
                    detail=f"Single attachment {doc_id} provided; both SI and BL required",
                )
                issue = ReviewIssue(
                    issue_id=f"issue_{operation_id}_single_unknown",
                    stage=Stage.IDENTIFICATION,
                    logical_reason=LogicalReason.MISSING_ATTACHMENT,
                    document_ids=[doc_id],
                    expected_role=None,
                    fields=[],
                    evidence_ids=[ev.evidence_id],
                    suggested_action="Request complete SI and Draft BL pair from sender",
                    recovery_state="NOT_APPLICABLE",
                    recovery_detail="Incomplete attachment pair",
                    attempt_ids=[f"att_{operation_id}_single"],
                )
                return RoleBindingResult(
                    state="NEEDS_REVIEW",
                    review_issue=issue,
                    logical_reason=LogicalReason.MISSING_ATTACHMENT,
                    reason_detail="Incomplete attachment pair",
                    evidence=[ev],
                )

        # 6. Duplicate Candidate Check (PAR-ROLE-005)
        if len(si_candidates) > 1:
            conflict_ids = [c[0] for c in si_candidates]
            ev = FieldEvidence(
                evidence_id="ev_role_dup_si",
                source_type="processing",
                source_id=conflict_ids[0],
                kind="processing_error",
                detail=f"Multiple conflicting SI candidate attachments: {conflict_ids}",
            )
            issue = ReviewIssue(
                issue_id=f"issue_{operation_id}_dup_si",
                stage=Stage.IDENTIFICATION,
                logical_reason=LogicalReason.WRONG_OR_UNCERTAIN_DOCUMENT_TYPE,
                document_ids=conflict_ids,
                expected_role=DocumentRole.SI,
                fields=[],
                evidence_ids=[ev.evidence_id],
                suggested_action="Human operator review required to resolve ambiguous multiple SI candidate files",
                recovery_state="NOT_APPLICABLE",
                recovery_detail="Duplicate SI candidates found",
                attempt_ids=[f"att_{operation_id}_dup_si"],
            )
            return RoleBindingResult(
                state="NEEDS_REVIEW",
                review_issue=issue,
                logical_reason=LogicalReason.WRONG_OR_UNCERTAIN_DOCUMENT_TYPE,
                reason_detail="Multiple conflicting SI files attached",
                evidence=[ev],
            )

        if len(bl_candidates) > 1:
            conflict_ids = [c[0] for c in bl_candidates]
            ev = FieldEvidence(
                evidence_id="ev_role_dup_bl",
                source_type="processing",
                source_id=conflict_ids[0],
                kind="processing_error",
                detail=f"Multiple conflicting Draft BL candidate attachments: {conflict_ids}",
            )
            issue = ReviewIssue(
                issue_id=f"issue_{operation_id}_dup_bl",
                stage=Stage.IDENTIFICATION,
                logical_reason=LogicalReason.WRONG_OR_UNCERTAIN_DOCUMENT_TYPE,
                document_ids=conflict_ids,
                expected_role=DocumentRole.BL,
                fields=[],
                evidence_ids=[ev.evidence_id],
                suggested_action="Human operator review required to resolve ambiguous multiple BL candidate files",
                recovery_state="NOT_APPLICABLE",
                recovery_detail="Duplicate Draft BL candidates found",
                attempt_ids=[f"att_{operation_id}_dup_bl"],
            )
            return RoleBindingResult(
                state="NEEDS_REVIEW",
                review_issue=issue,
                logical_reason=LogicalReason.WRONG_OR_UNCERTAIN_DOCUMENT_TYPE,
                reason_detail="Multiple conflicting Draft BL files attached",
                evidence=[ev],
            )

        # 7. Tier 1 Deterministic Success (PAR-ROLE-001, DEC-AI-P03)
        if len(si_candidates) == 1 and len(bl_candidates) == 1:
            si_id, _, si_ev_detail = si_candidates[0]
            bl_id, _, bl_ev_detail = bl_candidates[0]

            if si_id == bl_id:
                # Same file collision guard
                ev = FieldEvidence(
                    evidence_id="ev_role_same_file_collision",
                    source_type="processing",
                    source_id=si_id,
                    kind="processing_error",
                    detail="Same attachment file assigned to both SI and BL roles",
                )
                issue = ReviewIssue(
                    issue_id=f"issue_{operation_id}_collision",
                    stage=Stage.IDENTIFICATION,
                    logical_reason=LogicalReason.WRONG_OR_UNCERTAIN_DOCUMENT_TYPE,
                    document_ids=[si_id],
                    expected_role=None,
                    fields=[],
                    evidence_ids=[ev.evidence_id],
                    suggested_action="Require distinct files for SI and Draft BL",
                    recovery_state="NOT_APPLICABLE",
                    recovery_detail="Role collision on same document ID",
                    attempt_ids=[f"att_{operation_id}_col"],
                )
                return RoleBindingResult(
                    state="NEEDS_REVIEW",
                    review_issue=issue,
                    logical_reason=LogicalReason.WRONG_OR_UNCERTAIN_DOCUMENT_TYPE,
                    reason_detail="Same file assigned to both roles",
                    evidence=[ev],
                )

            ev_si = FieldEvidence(
                evidence_id=f"ev_role_si_{si_id}",
                source_type="document",
                source_id=si_id,
                kind="document_metadata",
                detail=si_ev_detail,
            )
            ev_bl = FieldEvidence(
                evidence_id=f"ev_role_bl_{bl_id}",
                source_type="document",
                source_id=bl_id,
                kind="document_metadata",
                detail=bl_ev_detail,
            )
            si_doc = DocumentReference(
                document_id=si_id,
                role=DocumentRole.SI,
                identification_evidence_ids=[ev_si.evidence_id],
            )
            bl_doc = DocumentReference(
                document_id=bl_id,
                role=DocumentRole.BL,
                identification_evidence_ids=[ev_bl.evidence_id],
            )
            return RoleBindingResult(
                state="RESOLVED",
                si_doc=si_doc,
                bl_doc=bl_doc,
                documents=[si_doc, bl_doc],
                evidence=[ev_si, ev_bl],
            )

        # 8. Tier 2: On-Demand AI Role Resolution (PAR-ROLE-002)
        if self.ai_adapter is not None and unknown_candidates:
            try:
                ai_input = [item[0] for item in items]
                ai_res: DocumentRoleResolutionOutput = self.ai_adapter.resolve_document_roles(
                    attachments=ai_input,
                    tracker=tracker,
                )

                assigned_si: List[str] = [
                    doc_id for doc_id, role in ai_res.document_roles.items() if role == "SI"
                ]
                assigned_bl: List[str] = [
                    doc_id for doc_id, role in ai_res.document_roles.items() if role == "BL"
                ]

                if len(assigned_si) == 1 and len(assigned_bl) == 1 and assigned_si[0] != assigned_bl[0]:
                    si_id = assigned_si[0]
                    bl_id = assigned_bl[0]
                    ev_si = FieldEvidence(
                        evidence_id=f"ev_role_ai_si_{si_id}",
                        source_type="document",
                        source_id=si_id,
                        kind="document_metadata",
                        detail=f"AI semantic role resolution assigned SI: {ai_res.rationale}",
                    )
                    ev_bl = FieldEvidence(
                        evidence_id=f"ev_role_ai_bl_{bl_id}",
                        source_type="document",
                        source_id=bl_id,
                        kind="document_metadata",
                        detail=f"AI semantic role resolution assigned BL: {ai_res.rationale}",
                    )
                    si_doc = DocumentReference(
                        document_id=si_id,
                        role=DocumentRole.SI,
                        identification_evidence_ids=[ev_si.evidence_id],
                    )
                    bl_doc = DocumentReference(
                        document_id=bl_id,
                        role=DocumentRole.BL,
                        identification_evidence_ids=[ev_bl.evidence_id],
                    )
                    return RoleBindingResult(
                        state="RESOLVED",
                        si_doc=si_doc,
                        bl_doc=bl_doc,
                        documents=[si_doc, bl_doc],
                        evidence=[ev_si, ev_bl],
                    )
            except Exception as e:
                logger.warning("AI role resolution failed: %s", e)

        # 9. Inconclusive Roles Escalation
        all_ids = [item[0] for item in items]
        ev = FieldEvidence(
            evidence_id="ev_role_uncertain",
            source_type="processing",
            source_id=all_ids[0] if all_ids else "email",
            kind="processing_error",
            detail=f"Could not conclusively identify SI and Draft BL from attachments: {all_ids}",
        )
        issue = ReviewIssue(
            issue_id=f"issue_{operation_id}_uncertain",
            stage=Stage.IDENTIFICATION,
            logical_reason=LogicalReason.WRONG_OR_UNCERTAIN_DOCUMENT_TYPE,
            document_ids=all_ids,
            expected_role=None,
            fields=[],
            evidence_ids=[ev.evidence_id],
            suggested_action="Review attachments manually to bind SI and Draft BL roles",
            recovery_state="NOT_APPLICABLE",
            recovery_detail="Inconclusive document role binding",
            attempt_ids=[f"att_{operation_id}_uncertain"],
        )
        return RoleBindingResult(
            state="NEEDS_REVIEW",
            review_issue=issue,
            logical_reason=LogicalReason.WRONG_OR_UNCERTAIN_DOCUMENT_TYPE,
            reason_detail="Inconclusive role binding",
            evidence=[ev],
        )


def bind_attachment_roles(
    attachments: Union[EmailRecord, List[Any]],
    base_dir: Optional[Path] = None,
    ai_adapter: Optional[BaseAIAdapter] = None,
    tracker: Optional[AttemptTracker] = None,
) -> RoleBindingResult:
    """Convenience functional interface for attachment role binding."""
    binder = Stage2RoleBinder(base_dir=base_dir, ai_adapter=ai_adapter)
    return binder.bind_roles(attachments=attachments, tracker=tracker)


__all__ = [
    "RoleBindingResult",
    "Stage2RoleBinder",
    "bind_attachment_roles",
]
