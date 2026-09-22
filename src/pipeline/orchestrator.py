from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Sequence, Tuple, Union
import uuid

from src.comparator.field_comparator import compare_seven_fields
from src.hitl.escalation_engine import EscalationEngine
from src.llm.base_adapter import BaseAIAdapter
from src.models.audit import (
    AttemptRecord,
    AttemptTracker,
    AuditRecord,
    ProcessingMetadata,
)
from src.models.comparison import Discrepancy, PartialResult
from src.models.document import DocumentReference, ParserResult, ParserStatus, Role
from src.models.evidence import FieldEvidence
from src.models.extraction import (
    FIELD_NAMES,
    DocumentExtraction,
    FieldName,
    FieldReliability,
)
from src.models.ingestion import (
    AttachmentReference,
    ClassificationResult,
    EmailRecord,
)
from src.models.review import LogicalReason, ReviewCase, ReviewIssue, Stage, StageType
from src.parsers import parse_document
from src.pipeline.stage1_classify import Stage1Classifier
from src.pipeline.stage2_role_binding import RoleBindingResult, Stage2RoleBinder
from src.pipeline.stage3_extract import Stage3Extractor
from src.store.audit_store import AuditStore

logger = logging.getLogger(__name__)


def to_email_record(raw: Union[EmailRecord, Dict[str, Any]]) -> EmailRecord:
    """Convert raw dict or EmailRecord to validated EmailRecord instance."""
    if isinstance(raw, EmailRecord):
        return raw

    email_id = str(raw.get("email_id", f"email_{uuid.uuid4().hex[:8]}"))
    sender = str(raw.get("from", raw.get("sender", "unknown@example.com")))
    subject = str(raw.get("subject", ""))
    body = str(raw.get("body", ""))
    raw_atts = raw.get("attachments", [])

    attachments: List[AttachmentReference] = []
    for a in raw_atts:
        if isinstance(a, AttachmentReference):
            attachments.append(a)
        elif isinstance(a, str):
            doc_id = Path(a).name
            attachments.append(AttachmentReference(document_id=doc_id, path=a))
        elif isinstance(a, dict):
            doc_id = str(a.get("document_id", Path(a.get("path", "doc")).name))
            path_str = str(a.get("path", doc_id))
            mime = a.get("mime_type")
            attachments.append(
                AttachmentReference(document_id=doc_id, path=path_str, mime_type=mime)
            )

    return EmailRecord(
        email_id=email_id,
        sender=sender,
        subject=subject,
        body=body,
        attachments=attachments,
    )


def _dedup_evidence(evidence_list: Sequence[FieldEvidence]) -> List[FieldEvidence]:
    """Deduplicate evidence items by evidence_id while preserving order."""
    seen = set()
    deduped = []
    for ev in evidence_list:
        if ev.evidence_id not in seen:
            seen.add(ev.evidence_id)
            deduped.append(ev)
    return deduped


def record_attempt(
    tracker: AttemptTracker,
    operation_id: str,
    stage: Stage | StageType,
    kind: Literal["primary", "technical_retry", "semantic_repair", "fallback", "ocr"] = "primary",
    outcome: Literal["SUCCEEDED", "FAILED", "INVALID"] = "SUCCEEDED",
    attempt_id: Optional[str] = None,
) -> AttemptRecord:
    """Record an execution attempt in the AttemptTracker."""
    att_num = len(tracker.attempts) + 1
    aid = attempt_id or f"att_{operation_id}_{att_num}"
    att = AttemptRecord(
        attempt_id=aid,
        operation_id=operation_id,
        stage=stage,
        kind=kind,
        attempt_number=att_num,
        outcome=outcome,
    )
    tracker.attempts.append(att)
    return att


class PipelineOrchestrator:
    """End-to-end verification orchestrator integrating Stages 1-4 with AuditRecord synthesis (T11-02)."""

    def __init__(
        self,
        base_dir: Optional[Path] = None,
        ai_adapter: Optional[BaseAIAdapter] = None,
        audit_store: Optional[AuditStore] = None,
    ) -> None:
        self.base_dir = base_dir
        self.ai_adapter = ai_adapter
        self.audit_store = audit_store or AuditStore()
        self.classifier = Stage1Classifier(ai_adapter=ai_adapter)
        self.role_binder = Stage2RoleBinder(base_dir=base_dir, ai_adapter=ai_adapter)
        self.extractor = Stage3Extractor(ai_adapter=ai_adapter)
        self.escalation_engine = EscalationEngine()

    def process_email(
        self,
        raw_email: Union[EmailRecord, Dict[str, Any]],
        document_texts: Optional[Dict[str, str]] = None,
    ) -> AuditRecord:
        """Execute verification pipeline on a single email, emitting validated AuditRecord."""
        email_rec = to_email_record(raw_email)
        email_id = email_rec.email_id

        all_evidence: List[FieldEvidence] = []
        tracker = AttemptTracker()

        # -----------------------------------------------------------------
        # Stage 1: Intent Classification (Fast Veto Rule / FR-004)
        # -----------------------------------------------------------------
        cls_result, cls_ev = self.classifier.classify(email_rec, tracker=tracker)
        all_evidence.extend(cls_ev)

        # Ensure classification evidence has source_id == email_id
        for ev in cls_ev:
            if ev.source_type == "email" and ev.source_id != email_id:
                ev.source_id = email_id

        # Ambiguous classification intent (PIPE-CLS-006 / HITL-RSN-005)
        if cls_result.state == "NEEDS_REVIEW" or cls_result.category is None:
            ev_id = f"ev_cls_ambiguous_{email_id}"
            ev = FieldEvidence(
                evidence_id=ev_id,
                source_type="email",
                source_id=email_id,
                kind="text_span",
                quote=(email_rec.subject[:50] or email_rec.body[:50] or "Email intent").strip(),
            )
            all_evidence.append(ev)
            cls_result.evidence_ids.append(ev_id)

            issue = self.escalation_engine.create_uncertain_result_issue(
                document_ids=[],
                evidence_ids=[ev_id],
                suggested_action="Review inbound email intent; classification was inconclusive",
                recovery_detail="Inbound email intent could not be classified definitively as document_comparison",
                attempt_ids=[a.attempt_id for a in tracker.attempts] or ["att_cls_1"],
                stage=Stage.CLASSIFICATION,
            )
            for att_id in issue.attempt_ids:
                if not any(a.attempt_id == att_id for a in tracker.attempts):
                    record_attempt(tracker, email_id, Stage.CLASSIFICATION, "primary", "FAILED", attempt_id=att_id)

            review_case = self.escalation_engine.build_review_case(
                review_id=f"rev_{email_id}_1",
                issues=[issue],
            )
            audit_rec = AuditRecord(
                email_id=email_id,
                revision=1,
                previous_revision=None,
                email=email_rec,
                classification=cls_result,
                state="NEEDS_REVIEW",
                outcome=None,
                mismatch_detected=None,
                result_summary="Review required: Ambiguous email intent",
                documents=[],
                parsers=[],
                extractions=[],
                evidence=_dedup_evidence(all_evidence),
                partial_result=None,
                discrepancies=[],
                review=review_case,
                processing=ProcessingMetadata(
                    technical_attempt_limit=3,
                    semantic_attempt_limit=2,
                    attempts=tracker.attempts,
                ),
            )
            self.audit_store.save(audit_rec)
            return audit_rec

        # Non-comparison categories terminate immediately (FR-004)
        if cls_result.category != "document_comparison":
            audit_rec = AuditRecord(
                email_id=email_id,
                revision=1,
                previous_revision=None,
                email=email_rec,
                classification=cls_result,
                state="COMPLETE",
                outcome="NOT_APPLICABLE",
                mismatch_detected=None,
                result_summary=f"Non-comparison category: {cls_result.category}",
                documents=[],
                parsers=[],
                extractions=[],
                evidence=_dedup_evidence(all_evidence),
                partial_result=None,
                discrepancies=[],
                review=None,
                processing=ProcessingMetadata(
                    technical_attempt_limit=3,
                    semantic_attempt_limit=2,
                    attempts=tracker.attempts,
                ),
            )
            self.audit_store.save(audit_rec)
            return audit_rec

        # -----------------------------------------------------------------
        # Stage 2: Attachment Role Binding (T09)
        # -----------------------------------------------------------------
        role_result: RoleBindingResult = self.role_binder.bind_roles(
            attachments=email_rec,
            tracker=tracker,
            operation_id=email_id,
        )
        all_evidence.extend(role_result.evidence)

        if role_result.state == "NEEDS_REVIEW":
            issue = role_result.review_issue
            if issue is None:
                issue = self.escalation_engine.create_missing_attachment_issue(
                    issue_id=f"issue_missing_{email_id}",
                    expected_role="BL",
                    evidence_ids=[ev.evidence_id for ev in role_result.evidence] or [f"ev_role_{email_id}"],
                    attempt_ids=[a.attempt_id for a in tracker.attempts] or ["att_role_1"],
                )

            # Ensure evidence items exist in all_evidence
            for evid in issue.evidence_ids:
                if not any(e.evidence_id == evid for e in all_evidence):
                    all_evidence.append(
                        FieldEvidence(
                            evidence_id=evid,
                            source_type="email",
                            source_id=email_id,
                            kind="processing_error",
                            detail=f"Role binding escalation evidence: {issue.logical_reason}",
                        )
                    )

            # Ensure attempt_ids exist in tracker
            for att_id in issue.attempt_ids:
                if not any(a.attempt_id == att_id for a in tracker.attempts):
                    record_attempt(tracker, email_id, Stage.IDENTIFICATION, "primary", "FAILED", attempt_id=att_id)

            review_case = self.escalation_engine.build_review_case(
                review_id=f"rev_{email_id}_1",
                issues=[issue],
            )
            audit_rec = AuditRecord(
                email_id=email_id,
                revision=1,
                previous_revision=None,
                email=email_rec,
                classification=cls_result,
                state="NEEDS_REVIEW",
                outcome=None,
                mismatch_detected=None,
                result_summary=f"Review required: {role_result.reason_detail or 'unresolved attachments'}",
                documents=role_result.documents,
                parsers=[],
                extractions=[],
                evidence=_dedup_evidence(all_evidence),
                partial_result=PartialResult(
                    comparisons=[],
                    unresolved_fields=list(FIELD_NAMES),
                ),
                discrepancies=[],
                review=review_case,
                processing=ProcessingMetadata(
                    technical_attempt_limit=3,
                    semantic_attempt_limit=2,
                    attempts=tracker.attempts,
                ),
            )
            self.audit_store.save(audit_rec)
            return audit_rec

        # -----------------------------------------------------------------
        # Stage 3: Parsing & Usability (T05, T06)
        # -----------------------------------------------------------------
        si_doc = role_result.si_doc
        bl_doc = role_result.bl_doc
        assert si_doc is not None and bl_doc is not None

        si_text: str = ""
        bl_text: str = ""
        parsers: List[ParserResult] = []

        for doc in [si_doc, bl_doc]:
            doc_id = doc.document_id
            if document_texts and doc_id in document_texts:
                p_text = document_texts[doc_id]
                p_att_id = f"att_{doc_id}_parse"
                p_ev_id = f"ev_{doc_id}_parse"
                if not any(a.attempt_id == p_att_id for a in tracker.attempts):
                    p_att = record_attempt(tracker, doc_id, Stage.PARSING, "primary", "SUCCEEDED", attempt_id=p_att_id)
                    p_att_id = p_att.attempt_id
                all_evidence.append(
                    FieldEvidence(
                        evidence_id=p_ev_id,
                        source_type="document",
                        source_id=doc_id,
                        kind="text_span",
                        quote=(p_text[:50] or "Document text").strip(),
                    )
                )
                p_res = ParserResult(
                    document_id=doc_id,
                    status=ParserStatus.SUCCESS,
                    text=p_text,
                    usable_for_extraction=True,
                    diagnostic_evidence_ids=[p_ev_id],
                    attempt_ids=[p_att_id],
                )
                parsers.append(p_res)
                if doc.role == "SI":
                    si_text = p_text
                else:
                    bl_text = p_text
            else:
                # Parse from filesystem
                doc_path = Path(doc.path)
                if self.base_dir and not doc_path.is_absolute():
                    doc_path = self.base_dir / doc_path
                p_res = parse_document(doc_path, document_id=doc_id)
                # Align attempts with tracker
                for att_id in p_res.attempt_ids:
                    if not any(a.attempt_id == att_id for a in tracker.attempts):
                        record_attempt(
                            tracker,
                            doc_id,
                            Stage.PARSING,
                            "primary",
                            "SUCCEEDED" if p_res.usable_for_extraction else "FAILED",
                            attempt_id=att_id,
                        )
                for evid in p_res.diagnostic_evidence_ids:
                    all_evidence.append(
                        FieldEvidence(
                            evidence_id=evid,
                            source_type="document",
                            source_id=doc_id,
                            kind="processing_error" if not p_res.usable_for_extraction else "text_span",
                            detail=p_res.error_message or "Parser output",
                        )
                    )
                parsers.append(p_res)
                if doc.role == "SI":
                    si_text = p_res.text or ""
                else:
                    bl_text = p_res.text or ""

        # Check for unreadable document (HITL-RSN-002)
        unreadable_parsers = [p for p in parsers if not p.usable_for_extraction]
        if unreadable_parsers:
            bad_p = unreadable_parsers[0]
            issue = self.escalation_engine.create_unreadable_document_issue(
                document_id=bad_p.document_id,
                diagnostic=bad_p.error_message or "Document could not be parsed or rendered",
                evidence_ids=bad_p.diagnostic_evidence_ids,
                attempt_ids=bad_p.attempt_ids,
            )
            for att_id in issue.attempt_ids:
                if not any(a.attempt_id == att_id for a in tracker.attempts):
                    record_attempt(tracker, bad_p.document_id, Stage.PARSING, "primary", "FAILED", attempt_id=att_id)

            review_case = self.escalation_engine.build_review_case(
                review_id=f"rev_{email_id}_1",
                issues=[issue],
            )
            audit_rec = AuditRecord(
                email_id=email_id,
                revision=1,
                previous_revision=None,
                email=email_rec,
                classification=cls_result,
                state="NEEDS_REVIEW",
                outcome=None,
                mismatch_detected=None,
                result_summary=f"Review required: Unreadable document '{bad_p.document_id}'",
                documents=role_result.documents,
                parsers=parsers,
                extractions=[],
                evidence=_dedup_evidence(all_evidence),
                partial_result=PartialResult(
                    comparisons=[],
                    unresolved_fields=list(FIELD_NAMES),
                ),
                discrepancies=[],
                review=review_case,
                processing=ProcessingMetadata(
                    technical_attempt_limit=3,
                    semantic_attempt_limit=2,
                    attempts=tracker.attempts,
                ),
            )
            self.audit_store.save(audit_rec)
            return audit_rec

        # -----------------------------------------------------------------
        # Stage 3: Field Extraction & Reliability Gate (T10)
        # -----------------------------------------------------------------
        si_extraction, bl_extraction, ext_evidence = (
            self.extractor.extract_comparison_pair_fields(
                si_id=si_doc.document_id,
                si_text=si_text,
                bl_id=bl_doc.document_id,
                bl_text=bl_text,
                tracker=tracker,
            )
        )
        all_evidence.extend(ext_evidence)

        # -----------------------------------------------------------------
        # Stage 4: Deterministic 7-Field Comparison (T04, T11)
        # -----------------------------------------------------------------
        comp_res = compare_seven_fields(si_extraction, bl_extraction)

        if comp_res.unresolved_fields:
            # At least one field is unresolved -> state = NEEDS_REVIEW (PIPE-CMP-004, DC-03)
            review_issues: List[ReviewIssue] = []
            for uf in comp_res.unresolved_fields:
                si_f = si_extraction.fields.get(uf)
                bl_f = bl_extraction.fields.get(uf)

                ev_ids = [
                    ev.evidence_id
                    for ev in ext_evidence
                    if f"_{uf}" in ev.evidence_id
                ]
                if not ev_ids:
                    gen_ev_id = f"ev_{email_id}_unresolved_{uf}"
                    all_evidence.append(
                        FieldEvidence(
                            evidence_id=gen_ev_id,
                            source_type="email",
                            source_id=email_id,
                            kind="processing_error",
                            detail=f"Field {uf} missing or ungrounded",
                        )
                    )
                    ev_ids = [gen_ev_id]

                if si_f and si_f.reliability == FieldReliability.MISSING:
                    iss = self.escalation_engine.create_missing_required_value_issue(
                        document_id=si_doc.document_id,
                        field=uf,
                        evidence_ids=ev_ids,
                        attempt_ids=[a.attempt_id for a in tracker.attempts] or ["att_ext_1"],
                    )
                    review_issues.append(iss)
                elif bl_f and bl_f.reliability == FieldReliability.MISSING:
                    iss = self.escalation_engine.create_missing_required_value_issue(
                        document_id=bl_doc.document_id,
                        field=uf,
                        evidence_ids=ev_ids,
                        attempt_ids=[a.attempt_id for a in tracker.attempts] or ["att_ext_1"],
                    )
                    review_issues.append(iss)
                else:
                    iss = self.escalation_engine.create_uncertain_result_issue(
                        document_ids=[si_doc.document_id, bl_doc.document_id],
                        fields=[uf],
                        evidence_ids=ev_ids,
                        attempt_ids=[a.attempt_id for a in tracker.attempts] or ["att_ext_1"],
                    )
                    review_issues.append(iss)

            for iss in review_issues:
                for att_id in iss.attempt_ids:
                    if not any(a.attempt_id == att_id for a in tracker.attempts):
                        record_attempt(tracker, email_id, Stage.EXTRACTION, "primary", "FAILED", attempt_id=att_id)

            review_case = self.escalation_engine.build_review_case(
                review_id=f"rev_{email_id}_1",
                issues=review_issues,
            )

            audit_rec = AuditRecord(
                email_id=email_id,
                revision=1,
                previous_revision=None,
                email=email_rec,
                classification=cls_result,
                state="NEEDS_REVIEW",
                outcome=None,
                mismatch_detected=None,
                result_summary=comp_res.result_summary,
                documents=role_result.documents,
                parsers=parsers,
                extractions=[si_extraction, bl_extraction],
                evidence=_dedup_evidence(all_evidence),
                partial_result=comp_res.partial_result,
                discrepancies=comp_res.discrepancies,
                review=review_case,
                processing=ProcessingMetadata(
                    technical_attempt_limit=3,
                    semantic_attempt_limit=2,
                    attempts=tracker.attempts,
                ),
            )
            self.audit_store.save(audit_rec)
            return audit_rec

        # -----------------------------------------------------------------
        # Complete Comparison (PIPE-CMP-001, 002, 003)
        # -----------------------------------------------------------------
        audit_rec = AuditRecord(
            email_id=email_id,
            revision=1,
            previous_revision=None,
            email=email_rec,
            classification=cls_result,
            state="COMPLETE",
            outcome=comp_res.outcome,
            mismatch_detected=comp_res.mismatch_detected,
            result_summary=comp_res.result_summary,
            documents=role_result.documents,
            parsers=parsers,
            extractions=[si_extraction, bl_extraction],
            evidence=_dedup_evidence(all_evidence),
            partial_result=comp_res.partial_result,
            discrepancies=comp_res.discrepancies,
            review=None,
            processing=ProcessingMetadata(
                technical_attempt_limit=3,
                semantic_attempt_limit=2,
                attempts=tracker.attempts,
            ),
        )
        self.audit_store.save(audit_rec)
        return audit_rec

    def process_all(
        self,
        emails: Sequence[Union[EmailRecord, Dict[str, Any]]],
        document_texts: Optional[Dict[str, str]] = None,
    ) -> List[AuditRecord]:
        """Batch process a sequence of emails, returning list of AuditRecords."""
        records: List[AuditRecord] = []
        for em in emails:
            rec = self.process_email(em, document_texts=document_texts)
            records.append(rec)
        return records
