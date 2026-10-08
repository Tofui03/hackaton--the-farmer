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
        from src.application.use_cases.verify_email import EmailVerificationUseCase

        self.verification_use_case = EmailVerificationUseCase(
            classifier=self.classifier,
            role_binder=self.role_binder,
            extractor=self.extractor,
            escalation_engine=self.escalation_engine,
            audit_store=self.audit_store,
            base_dir=base_dir,
        )

    def process_email(
        self,
        raw_email: Union[EmailRecord, Dict[str, Any]],
        document_texts: Optional[Dict[str, str]] = None,
    ) -> AuditRecord:
        """Execute verification pipeline on a single email, delegating to EmailVerificationUseCase."""
        return self.verification_use_case.execute(raw_email, document_texts=document_texts)

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
