from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple, Union

from src.llm.base_adapter import BaseAIAdapter
from src.llm.evidence_validator import validate_evidence_grounding
from src.llm.schemas import EmailClassificationOutput
from src.models.audit import AttemptTracker
from src.models.evidence import FieldEvidence
from src.models.ingestion import (
    AttachmentReference,
    Category,
    ClassificationResult,
    EmailCategory,
    EmailRecord,
)

logger = logging.getLogger(__name__)


def _extract_email_fields(
    email: Union[EmailRecord, Dict[str, Any]],
) -> Tuple[str, str, str, str, List[str]]:
    """Extract (email_id, sender, subject, body, attachment_filenames) safely."""
    if isinstance(email, EmailRecord):
        email_id = str(email.email_id)
        sender = str(email.sender)
        subject = str(email.subject)
        body = str(email.body)
        attachments = [str(a.path) for a in email.attachments]
    elif isinstance(email, dict):
        email_id = str(email.get("email_id", "unknown_email"))
        sender = str(email.get("from", email.get("sender", "")))
        subject = str(email.get("subject", ""))
        body = str(email.get("body", ""))
        raw_atts = email.get("attachments", [])
        attachments = []
        for a in raw_atts:
            if isinstance(a, str):
                attachments.append(a)
            elif isinstance(a, dict):
                attachments.append(str(a.get("path", a.get("document_id", ""))))
            elif hasattr(a, "path"):
                attachments.append(str(a.path))
    else:
        email_id = str(getattr(email, "email_id", "unknown_email"))
        sender = str(getattr(email, "sender", getattr(email, "from", "")))
        subject = str(getattr(email, "subject", ""))
        body = str(getattr(email, "body", ""))
        raw_atts = getattr(email, "attachments", [])
        attachments = [str(getattr(a, "path", a)) for a in raw_atts]

    return email_id, sender, subject, body, attachments


def deterministic_classify_email(
    email: Union[EmailRecord, Dict[str, Any]],
) -> Optional[Tuple[ClassificationResult, List[FieldEvidence]]]:
    """Deterministic fast-path for email intent classification (DEC-AI-P03, EC-001, EC-002, REG-001).
    
    Returns:
        (ClassificationResult, [FieldEvidence]) if intent is unambiguously resolved,
        or None if email is ambiguous and requires AI-on-demand inspection.
    """
    email_id, sender, subject, body, attachments = _extract_email_fields(email)

    subj_upper = subject.upper()
    body_upper = body.upper()
    combined_upper = f"{subj_upper}\n{body_upper}"

    # 1. SPAM check (EC-001)
    spam_phrases = [
        "WEIRD TRICK",
        "INCREASE YOUR SHIPPING REVENUE",
        "CASINO",
        "PRIZE",
        "EXCLUSIVE OFFER",
        "UNSUBSCRIBE",
        "FREE TRIAL",
        "CLICK HERE",
        "MARKETING OFFER",
        "PROMOTIONAL OFFER",
    ]
    for p in spam_phrases:
        if p in subj_upper or p in body_upper:
            quote = p
            m = re.search(re.escape(p), subject, re.IGNORECASE) or re.search(
                re.escape(p), body, re.IGNORECASE
            )
            if m:
                quote = m.group(0)
            ev_id = f"ev_cls_{email_id}_1"
            ev = FieldEvidence(
                evidence_id=ev_id,
                source_type="email",
                source_id=email_id,
                kind="text_span",
                quote=quote,
            )
            return (
                ClassificationResult(
                    state="RESOLVED",
                    category=EmailCategory.SPAM,
                    reason=f"Spam solicitation indicator detected: '{quote}'",
                    evidence_ids=[ev_id],
                    confidence_indicator="HIGH",
                ),
                [ev],
            )

    # 2. DOCUMENT_COMPARISON check (EC-001, EC-002, REG-001, PIPE-CLS-002, PIPE-CLS-003, PIPE-CLS-004)
    # Important: Body comparison intent prevails over conflicting subject keywords (PIPE-CLS-002).
    # Attachment count MUST NOT gate comparison intent; 0 attachments still yields document_comparison (PIPE-CLS-004, REG-001).
    comparison_body_patterns = [
        r"(?:COMPARE|CHECK|VERIFY|CONFIRM|REVIEW)\b.*?\b(?:DRAFT\s+BL|BL|BILL\s+OF\s+LADING)\b.*?\b(?:SI|SHIPPING\s+INSTRUCTION)\b",
        r"(?:COMPARE|CHECK|VERIFY|CONFIRM|REVIEW)\b.*?\b(?:SI|SHIPPING\s+INSTRUCTION)\b.*?\b(?:DRAFT\s+BL|BL|BILL\s+OF\s+LADING)\b",
        r"\b(?:ATTACHED|FIND\s+ATTACHED|SEE\s+ATTACHED)\b.*?\b(?:SI|SHIPPING\s+INSTRUCTION)\b.*?\b(?:DRAFT\s+BL|BL|BILL\s+OF\s+LADING)\b",
        r"\b(?:ATTACHED|FIND\s+ATTACHED|SEE\s+ATTACHED)\b.*?\b(?:DRAFT\s+BL|BL|BILL\s+OF\s+LADING)\b.*?\b(?:SI|SHIPPING\s+INSTRUCTION)\b",
        r"\bATTACHED\s+ARE\s+THE\s+SI\s+AND\s+DRAFT\s+BL\b",
        r"\bATTACHED\s+ARE\s+THE\s+DRAFT\s+BL\s+AND\s+SI\b",
        r"\bPLEASE\s+SEE\s+ATTACHED\s+DRAFT\s+BL\s+AND\s+SI\b",
        r"\bPLEASE\s+SEE\s+ATTACHED\s+SI\s+AND\s+DRAFT\s+BL\b",
        r"\bCOMPARE\s+ATTACHED\s+SI\s+AND\s+DRAFT\s+BL\b",
        r"\bCOMPARE\s+ATTACHED\s+DRAFT\s+BL\s+AND\s+SI\b",
        r"\bVERIFY\s+ATTACHED\s+SI\s+AND\s+DRAFT\s+BL\b",
        r"\bVERIFY\s+ATTACHED\s+DRAFT\s+BL\s+AND\s+SI\b",
    ]

    for pat in comparison_body_patterns:
        m = re.search(pat, body, re.IGNORECASE)
        if m:
            quote = m.group(0).strip()
            ev_id = f"ev_cls_{email_id}_1"
            ev = FieldEvidence(
                evidence_id=ev_id,
                source_type="email",
                source_id=email_id,
                kind="text_span",
                quote=quote,
            )
            return (
                ClassificationResult(
                    state="RESOLVED",
                    category=EmailCategory.DOCUMENT_COMPARISON,
                    reason=f"Body shipping document comparison intent detected: '{quote}'",
                    evidence_ids=[ev_id],
                    confidence_indicator="HIGH",
                ),
                [ev],
            )

    # Subject comparison patterns (EC-002, REG-001: zero attachment gate)
    if "TO CONFIRM DOCS" in subj_upper or "BL COMPARISON" in subj_upper or "DOCS COMPARISON" in subj_upper:
        m = re.search(r"TO CONFIRM DOCS|BL COMPARISON|DOCS COMPARISON", subject, re.IGNORECASE)
        quote = m.group(0) if m else "TO CONFIRM DOCS"
        ev_id = f"ev_cls_{email_id}_1"
        ev = FieldEvidence(
            evidence_id=ev_id,
            source_type="email",
            source_id=email_id,
            kind="text_span",
            quote=quote,
        )
        return (
            ClassificationResult(
                state="RESOLVED",
                category=EmailCategory.DOCUMENT_COMPARISON,
                reason=f"Subject shipping document comparison intent detected: '{quote}'",
                evidence_ids=[ev_id],
                confidence_indicator="HIGH",
            ),
            [ev],
        )

    # Both SI and BL attachments present with verification request in subject or body
    has_si_att = any("_SI." in a.upper() for a in attachments)
    has_bl_att = any("_BL." in a.upper() for a in attachments)
    if has_si_att and has_bl_att:
        # Check for confirmation/checking intent
        confirm_indicators = ["CONFIRM", "CHECK", "VERIFY", "COMPARE", "REVIEW", "DOCS"]
        if any(w in combined_upper for w in confirm_indicators):
            quote = subject.strip() or "SI and BL attachments with verification request"
            ev_id = f"ev_cls_{email_id}_1"
            ev = FieldEvidence(
                evidence_id=ev_id,
                source_type="email",
                source_id=email_id,
                kind="text_span",
                quote=quote[:100],
            )
            return (
                ClassificationResult(
                    state="RESOLVED",
                    category=EmailCategory.DOCUMENT_COMPARISON,
                    reason="SI and BL paired attachments detected with verification request",
                    evidence_ids=[ev_id],
                    confidence_indicator="HIGH",
                ),
                [ev],
            )

    # 3. INVOICE_QUERY check (EC-001, FR-004, PIPE-CLS-005)
    invoice_keywords = [
        "LOCAL CHARGES",
        "TELEX RELEASE CHARGES",
        "TELEX RELEASE",
        "D & D CHARGES",
        "DEMURRAGE",
        "DETENTION",
        "FREIGHT PAYMENT",
        "TOTAL FREIGHT",
        "QUERY ON INVOICE",
        "INVOICE QUERY",
        "INVOICE PAYMENT",
        "PAYMENT INQUIRY",
        "BILLING INQUIRY",
    ]
    for kw in invoice_keywords:
        if kw in subj_upper or kw in body_upper:
            m = re.search(re.escape(kw), subject, re.IGNORECASE) or re.search(
                re.escape(kw), body, re.IGNORECASE
            )
            quote = m.group(0) if m else kw
            ev_id = f"ev_cls_{email_id}_1"
            ev = FieldEvidence(
                evidence_id=ev_id,
                source_type="email",
                source_id=email_id,
                kind="text_span",
                quote=quote,
            )
            return (
                ClassificationResult(
                    state="RESOLVED",
                    category=EmailCategory.INVOICE_QUERY,
                    reason=f"Billing / invoice query intent detected: '{quote}'",
                    evidence_ids=[ev_id],
                    confidence_indicator="HIGH",
                ),
                [ev],
            )

    # Single INVOICE keyword if clearly billing-focused
    if "INVOICE" in subj_upper:
        m = re.search(r"\bINVOICE\b", subject, re.IGNORECASE)
        quote = m.group(0) if m else "INVOICE"
        ev_id = f"ev_cls_{email_id}_1"
        ev = FieldEvidence(
            evidence_id=ev_id,
            source_type="email",
            source_id=email_id,
            kind="text_span",
            quote=quote,
        )
        return (
            ClassificationResult(
                state="RESOLVED",
                category=EmailCategory.INVOICE_QUERY,
                reason=f"Invoice query subject detected: '{quote}'",
                evidence_ids=[ev_id],
                confidence_indicator="HIGH",
            ),
            [ev],
        )

    # 4. NEW_SHIPPING_INSTRUCTION check (EC-001)
    si_subject_keywords = [
        "REQUEST SI",
        "SI NEEDED",
        "SUBMIT SI",
        "SHIPPING INSTRUCTION",
        "SUBMISSION OF SI",
        "SEND SI",
        "PLEASE ASSIST TO SEND SI",
        "NEW SHIPPING INSTRUCTION",
        "SI SUBMISSION",
    ]
    for kw in si_subject_keywords:
        if kw in subj_upper:
            m = re.search(re.escape(kw), subject, re.IGNORECASE)
            quote = m.group(0) if m else kw
            ev_id = f"ev_cls_{email_id}_1"
            ev = FieldEvidence(
                evidence_id=ev_id,
                source_type="email",
                source_id=email_id,
                kind="text_span",
                quote=quote,
            )
            return (
                ClassificationResult(
                    state="RESOLVED",
                    category=EmailCategory.NEW_SHIPPING_INSTRUCTION,
                    reason=f"New shipping instruction submission/request detected: '{quote}'",
                    evidence_ids=[ev_id],
                    confidence_indicator="HIGH",
                ),
                [ev],
            )

    if "SHIPPING INSTRUCTION" in body_upper and not has_bl_att:
        m = re.search(r"SHIPPING INSTRUCTION", body, re.IGNORECASE)
        quote = m.group(0) if m else "SHIPPING INSTRUCTION"
        ev_id = f"ev_cls_{email_id}_1"
        ev = FieldEvidence(
            evidence_id=ev_id,
            source_type="email",
            source_id=email_id,
            kind="text_span",
            quote=quote,
        )
        return (
            ClassificationResult(
                state="RESOLVED",
                category=EmailCategory.NEW_SHIPPING_INSTRUCTION,
                reason=f"Shipping instruction body reference detected: '{quote}'",
                evidence_ids=[ev_id],
                confidence_indicator="HIGH",
            ),
            [ev],
        )

    # 5. GENERAL check (EC-001)
    general_keywords = [
        "VESSEL SCHEDULE",
        "SAILING SCHEDULE",
        "ETA UPDATE",
        "SCHEDULE UPDATE",
        "NOTICE OF ARRIVAL",
        "ARRIVAL NOTICE",
        "GENERAL UPDATE",
        "PORT CONGESTION UPDATE",
        "HOLIDAY NOTICE",
    ]
    for kw in general_keywords:
        if kw in subj_upper or kw in body_upper:
            m = re.search(re.escape(kw), subject, re.IGNORECASE) or re.search(
                re.escape(kw), body, re.IGNORECASE
            )
            quote = m.group(0) if m else kw
            ev_id = f"ev_cls_{email_id}_1"
            ev = FieldEvidence(
                evidence_id=ev_id,
                source_type="email",
                source_id=email_id,
                kind="text_span",
                quote=quote,
            )
            return (
                ClassificationResult(
                    state="RESOLVED",
                    category=EmailCategory.GENERAL,
                    reason=f"General operational update detected: '{quote}'",
                    evidence_ids=[ev_id],
                    confidence_indicator="HIGH",
                ),
                [ev],
            )

    # If heuristics are inconclusive, return None to signal AI-on-demand evaluation
    return None


def rule_based_classify(email: Dict[str, Any]) -> str:
    """Legacy heuristic classifier preserved for backward compatibility.
    
    Returns legacy competition format strings:
    BL_COMPARISON, INVOICE_QUERY, SI_REQUEST, SPAM, GENERAL.
    
    Note: Attachment gate len(attachments) >= 1 removed per EC-002, REG-001.
    """
    subject = email.get("subject", "").upper()
    body = email.get("body", "").upper()
    attachments = email.get("attachments", [])

    # Check for SPAM
    spam_patterns = [
        "WEIRD TRICK",
        "INCREASE YOUR SHIPPING REVENUE",
        "CASINO",
        "PRIZE",
        "EXCLUSIVE OFFER",
        "UNSUBSCRIBE",
        "FREE TRIAL",
        "MARKETING",
        "CLICK HERE",
    ]
    if any(p in subject or p in body for p in spam_patterns):
        return "SPAM"

    # Check for BL_COMPARISON (has SI/BL attachments or explicit checking language)
    # REG-001: Decoupled attachment count from intent!
    has_si_att = any("_SI." in a.upper() for a in attachments if isinstance(a, str))
    has_bl_att = any("_BL." in a.upper() for a in attachments if isinstance(a, str))
    if (has_si_att and has_bl_att) or ("TO CONFIRM DOCS" in subject):
        return "BL_COMPARISON"

    # Check for SI_REQUEST in subject first
    si_subject_keywords = [
        "REQUEST SI",
        "SI NEEDED",
        "SUBMIT SI",
        "SHIPPING INSTRUCTION",
        "SUBMISSION OF SI",
        "SEND SI",
        "PLEASE ASSIST TO SEND SI",
    ]
    if any(k in subject for k in si_subject_keywords):
        return "SI_REQUEST"

    # Check for INVOICE_QUERY (subject priority)
    invoice_keywords = [
        "INVOICE",
        "LOCAL CHARGES",
        "THC",
        "TELEX RELEASE",
        "D & D CHARGES",
        "DEMURRAGE",
        "DETENTION",
        "FREIGHT PAYMENT",
        "TOTAL FREIGHT",
    ]
    if any(k in subject for k in invoice_keywords):
        return "INVOICE_QUERY"

    # Check body for SI vs Invoice if subject was inconclusive
    if "SHIPPING INSTRUCTION" in body and "INVOICE" not in subject:
        return "SI_REQUEST"

    if any(k in body for k in invoice_keywords) and "QUERY ON INVOICE" in body:
        return "INVOICE_QUERY"

    # Other operational updates
    return "GENERAL"


class Stage1Classifier:
    """Classifies incoming emails into canonical EmailCategory using deterministic fast-path and AI-on-demand."""

    def __init__(
        self,
        ai_adapter: Optional[BaseAIAdapter] = None,
        cache: Optional[Any] = None,
        batch_size: int = 30,
        use_heuristics_fallback: bool = True,
    ):
        self.ai_adapter = ai_adapter
        self.cache = cache
        self.batch_size = batch_size
        self.use_heuristics_fallback = use_heuristics_fallback

    def classify(
        self,
        email: Union[EmailRecord, Dict[str, Any]],
        tracker: Optional[AttemptTracker] = None,
    ) -> Tuple[ClassificationResult, List[FieldEvidence]]:
        """Classify a single email into a ClassificationResult with source-grounded evidence."""
        # 1. Deterministic Fast-Path (DEC-AI-P03, PIPE-CLS-007)
        det_res = deterministic_classify_email(email)
        if det_res is not None:
            return det_res

        # 2. On-Demand AI Fallback (if deterministic is inconclusive)
        email_id, _, subject, body, _ = _extract_email_fields(email)

        if self.ai_adapter is not None:
            try:
                ai_output: EmailClassificationOutput = self.ai_adapter.classify_email(
                    email_record=email,
                    tracker=tracker,
                )

                # 1. Check for actual ambiguity / unresolved category (DC-01)
                valid_categories = {c.value for c in EmailCategory}
                if not ai_output.category or ai_output.category not in valid_categories:
                    return (
                        ClassificationResult(
                            state="NEEDS_REVIEW",
                            category=None,
                            reason=f"Ambiguous email intent: AI returned unresolved category. Detail: {ai_output.reason}",
                            evidence_ids=[],
                            confidence_indicator=ai_output.confidence_indicator or "LOW",
                        ),
                        [],
                    )

                # 2. Ground evidence from AI output in email text (REG-011)
                evidence_list: List[FieldEvidence] = []
                ev_ids: List[str] = []
                full_text = f"{subject}\n{body}".strip()

                raw_quotes = list(ai_output.evidence or [])
                if ai_output.evidence_quote and ai_output.evidence_quote not in raw_quotes:
                    raw_quotes.append(ai_output.evidence_quote)

                # Validate every claimed quote is empirically grounded in source text
                ungrounded_quotes = []
                for idx, ev_str in enumerate(raw_quotes, start=1):
                    ev_str_clean = str(ev_str).strip()
                    if not ev_str_clean:
                        continue
                    if not validate_evidence_grounding(ev_str_clean, source_text=full_text):
                        ungrounded_quotes.append(ev_str_clean)
                    else:
                        ev_id = f"ev_cls_{email_id}_{idx}"
                        ev = FieldEvidence(
                            evidence_id=ev_id,
                            source_type="email",
                            source_id=email_id,
                            kind="text_span",
                            quote=ev_str_clean,
                        )
                        evidence_list.append(ev)
                        ev_ids.append(ev_id)

                # Rejection rule (REG-011): A HIGH-confidence hallucination must not resolve.
                # If explicit evidence quotes were provided but any was ungrounded, reject the classification.
                if ungrounded_quotes:
                    logger.warning(
                        "Rejected ungrounded AI classification evidence for %s: %s",
                        email_id,
                        ungrounded_quotes,
                    )
                    return (
                        ClassificationResult(
                            state="NEEDS_REVIEW",
                            category=None,
                            reason=f"AI classification rejected due to ungrounded evidence: {ungrounded_quotes[0]!r}",
                            evidence_ids=[],
                            confidence_indicator=ai_output.confidence_indicator or "HIGH",
                        ),
                        [],
                    )

                # If no explicit evidence quotes were provided, attempt fallback to grounded subject or body snippet
                if not ev_ids:
                    fallback_quote = subject.strip() if subject.strip() else body[:60].strip()
                    if fallback_quote and validate_evidence_grounding(fallback_quote, source_text=full_text):
                        ev_id = f"ev_cls_{email_id}_1"
                        ev = FieldEvidence(
                            evidence_id=ev_id,
                            source_type="email",
                            source_id=email_id,
                            kind="text_span",
                            quote=fallback_quote,
                        )
                        evidence_list.append(ev)
                        ev_ids.append(ev_id)
                    else:
                        return (
                            ClassificationResult(
                                state="NEEDS_REVIEW",
                                category=None,
                                reason="AI classification could not be grounded in email context",
                                evidence_ids=[],
                                confidence_indicator=ai_output.confidence_indicator or "LOW",
                            ),
                            [],
                        )

                # 3. Canonical grounded output resolves regardless of confidence (confidence is diagnostic metadata)
                return (
                    ClassificationResult(
                        state="RESOLVED",
                        category=ai_output.category,
                        reason=ai_output.reason or "AI classification resolved",
                        evidence_ids=ev_ids,
                        confidence_indicator=ai_output.confidence_indicator or "MEDIUM",
                    ),
                    evidence_list,
                )

            except Exception as e:
                logger.warning("AI classification failed for email %s: %s", email_id, e)

        # 3. Ambiguous Intent Escalation (DC-01, HITL-RSN-005, PIPE-CLS-006)
        return (
            ClassificationResult(
                state="NEEDS_REVIEW",
                category=None,
                reason="Ambiguous email intent; heuristics inconclusive and AI confidence low or unavailable",
                evidence_ids=[],
                confidence_indicator="LOW",
            ),
            [],
        )

    def classify_all(
        self,
        emails: List[Union[EmailRecord, Dict[str, Any]]],
        tracker: Optional[AttemptTracker] = None,
    ) -> Dict[str, ClassificationResult]:
        """Classify a collection of emails, returning mapping from email_id to ClassificationResult."""
        results: Dict[str, ClassificationResult] = {}
        for email in emails:
            email_id, _, _, _, _ = _extract_email_fields(email)
            res, _ = self.classify(email, tracker=tracker)
            results[email_id] = res
        return results


__all__ = [
    "Stage1Classifier",
    "deterministic_classify_email",
    "rule_based_classify",
]
