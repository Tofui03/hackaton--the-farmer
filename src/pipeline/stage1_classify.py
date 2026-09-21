import logging
import re
from typing import Any, Dict, List, Optional
from src.cache import PipelineCache
from src.llm.client import GeminiClient
from src.llm.prompts import BATCH_CLASSIFY_SYSTEM_PROMPT, build_batch_classify_prompt

logger = logging.getLogger(__name__)


def rule_based_classify(email: Dict[str, Any]) -> str:
    """Heuristic classifier used as baseline or fallback."""
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
    has_si_att = any("_SI." in a.upper() for a in attachments)
    has_bl_att = any("_BL." in a.upper() for a in attachments)
    if (has_si_att and has_bl_att) or ("TO CONFIRM DOCS" in subject and len(attachments) >= 1):
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
    """Classifies inbox emails into the 5 target categories using batched LLM calls."""

    def __init__(
        self,
        gemini_client: Optional[GeminiClient] = None,
        cache: Optional[PipelineCache] = None,
        batch_size: int = 30,
        use_heuristics_fallback: bool = True,
    ):
        self.gemini_client = gemini_client
        self.cache = cache
        self.batch_size = batch_size
        self.use_heuristics_fallback = use_heuristics_fallback

    def classify_all(self, emails: List[Dict[str, Any]]) -> Dict[str, str]:
        """Classify a list of email dicts. Returns dict of email_id -> category."""
        results: Dict[str, str] = {}
        pending_batch: List[Dict[str, Any]] = []

        # 1. Recover from cache if available
        for e in emails:
            eid = e["email_id"]
            if self.cache:
                cached_cat = self.cache.get_classification(eid)
                if cached_cat:
                    results[eid] = cached_cat
                    continue
            pending_batch.append(e)

        if not pending_batch:
            return results

        # 2. Process remaining emails
        if self.gemini_client and self.gemini_client.is_ready():
            logger.info("Classifying %d pending emails with Gemini API (batch size %d)...", len(pending_batch), self.batch_size)
            for i in range(0, len(pending_batch), self.batch_size):
                chunk = pending_batch[i : i + self.batch_size]
                prompt = build_batch_classify_prompt(chunk)
                try:
                    llm_output = self.gemini_client.generate_json(
                        system_instruction=BATCH_CLASSIFY_SYSTEM_PROMPT,
                        user_prompt=prompt,
                    )
                    if isinstance(llm_output, list):
                        for item in llm_output:
                            eid = item.get("email_id")
                            cat = item.get("category", "GENERAL")
                            if eid:
                                results[eid] = cat
                                if self.cache:
                                    self.cache.set_classification(eid, cat)
                except Exception as e:
                    logger.error("LLM batch classification failed for chunk %d: %s", i, e)
                    if self.use_heuristics_fallback:
                        logger.info("Applying heuristic fallback for chunk %d", i)
                        for e in chunk:
                            eid = e["email_id"]
                            cat = rule_based_classify(e)
                            results[eid] = cat
                            if self.cache:
                                self.cache.set_classification(eid, cat)
                    else:
                        raise

            if self.cache:
                self.cache.save()
        else:
            # LLM not ready / dry-run mode -> use heuristic classification
            logger.info("Gemini API not configured or ready; using heuristic classification for %d emails.", len(pending_batch))
            for e in pending_batch:
                eid = e["email_id"]
                cat = rule_based_classify(e)
                results[eid] = cat
                if self.cache:
                    self.cache.set_classification(eid, cat)
            if self.cache:
                self.cache.save()

        return results
