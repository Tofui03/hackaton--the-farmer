import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from src.cache import PipelineCache
from src.parsers import parse_attachment
from src.pipeline.schema import AuditOutputRecord, HITLEscalation

logger = logging.getLogger(__name__)


class Stage2Extractor:
    """Extracts text from SI and BL attachments, generating HITL escalations on document issues."""

    def __init__(self, base_dir: Path, cache: Optional[PipelineCache] = None):
        self.base_dir = Path(base_dir)
        self.cache = cache

    def extract_comparison_pair(
        self,
        email: Dict[str, Any],
    ) -> Tuple[Optional[Dict[str, Any]], Optional[AuditOutputRecord]]:
        """
        Given a document-comparison email, returns:
        (ready_for_compare_payload, early_audit_record)

        If an issue is detected (missing attachment, corrupt file, unreadable scan),
        early_audit_record provides a fully-structured HITL escalation with evidence.
        """
        eid = email["email_id"]
        attachments = email.get("attachments", [])

        # Secret 3: Missing attachment (< 2 attachments)
        if len(attachments) < 2:
            early_record = AuditOutputRecord(
                email_id=eid,
                category="document_comparison",
                mismatch_detected=False,
                result_summary="Human review required: Missing attachment",
                discrepancies=[],
                hitl_escalation=HITLEscalation(
                    needed=True,
                    reason="missing_attachment",
                    evidence=f"Expected SI and BL pair; found {len(attachments)} attachment(s): {attachments}",
                ),
            )
            return None, early_record

        # Identify SI and BL attachment paths
        si_path = None
        bl_path = None
        for a in attachments:
            a_upper = a.upper()
            if "_SI." in a_upper or "SHIPPING INSTRUCTION" in a_upper:
                si_path = a
            elif "_BL." in a_upper or "BILL OF LADING" in a_upper:
                bl_path = a

        if not si_path or not bl_path:
            if len(attachments) == 2:
                if "_SI" in attachments[0].upper():
                    si_path, bl_path = attachments[0], attachments[1]
                elif "_BL" in attachments[0].upper():
                    bl_path, si_path = attachments[0], attachments[1]
                else:
                    early_record = AuditOutputRecord(
                        email_id=eid,
                        category="document_comparison",
                        mismatch_detected=False,
                        result_summary="Human review required: Wrong document type",
                        discrepancies=[],
                        hitl_escalation=HITLEscalation(
                            needed=True,
                            reason="wrong_doc_type",
                            evidence=f"Non-standard attachment names: {attachments}",
                        ),
                    )
                    return None, early_record
            else:
                early_record = AuditOutputRecord(
                    email_id=eid,
                    category="document_comparison",
                    mismatch_detected=False,
                    result_summary="Human review required: Missing attachment",
                    discrepancies=[],
                    hitl_escalation=HITLEscalation(
                        needed=True,
                        reason="missing_attachment",
                        evidence=f"Could not resolve SI and BL pair from {attachments}",
                    ),
                )
                return None, early_record

        # Parse SI document
        si_file = self.base_dir / si_path
        si_res = parse_attachment(si_file)
        if si_res.is_corrupted or not si_res.success:
            logger.warning("%s: SI attachment corrupt or unreadable: %s", eid, si_res.error_message)
            early_record = AuditOutputRecord(
                email_id=eid,
                category="document_comparison",
                mismatch_detected=False,
                result_summary="Human review required: Unreadable/corrupt SI attachment",
                discrepancies=[],
                hitl_escalation=HITLEscalation(
                    needed=True,
                    reason="unreadable",
                    evidence=f"SI file {si_path} unreadable: {si_res.error_message}",
                ),
            )
            return None, early_record

        # Parse BL document
        bl_file = self.base_dir / bl_path
        bl_res = parse_attachment(bl_file)
        if bl_res.is_corrupted or not bl_res.success:
            logger.warning("%s: BL attachment corrupt or unreadable: %s", eid, bl_res.error_message)
            early_record = AuditOutputRecord(
                email_id=eid,
                category="document_comparison",
                mismatch_detected=False,
                result_summary="Human review required: Unreadable/corrupt BL attachment",
                discrepancies=[],
                hitl_escalation=HITLEscalation(
                    needed=True,
                    reason="unreadable",
                    evidence=f"BL file {bl_path} unreadable: {bl_res.error_message}",
                ),
            )
            return None, early_record

        # Secret 3: Scanned image with no text extracted
        if (si_res.is_scanned or len(si_res.text.strip()) == 0) and (bl_res.is_scanned or len(bl_res.text.strip()) == 0):
            early_record = AuditOutputRecord(
                email_id=eid,
                category="document_comparison",
                mismatch_detected=False,
                result_summary="Human review required: Scanned image document with no text layer",
                discrepancies=[],
                hitl_escalation=HITLEscalation(
                    needed=True,
                    reason="unreadable",
                    evidence=f"Both {si_path} and {bl_path} are image-only scans with no extractable text",
                ),
            )
            return None, early_record

        # Cache extractions
        if self.cache:
            self.cache.set_extraction(si_path, si_res.to_dict())
            self.cache.set_extraction(bl_path, bl_res.to_dict())

        payload = {
            "email_id": eid,
            "email_meta": email,
            "si_path": si_path,
            "bl_path": bl_path,
            "si_text": si_res.text,
            "bl_text": bl_res.text,
            "si_is_scanned": si_res.is_scanned,
            "bl_is_scanned": bl_res.is_scanned,
        }
        return payload, None
