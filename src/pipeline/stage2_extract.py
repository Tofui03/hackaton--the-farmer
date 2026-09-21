import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from src.cache import PipelineCache
from src.parsers import parse_attachment

logger = logging.getLogger(__name__)


class Stage2Extractor:
    """Extracts text from SI and BL attachments, detecting missing, corrupt, or wrong files."""

    def __init__(self, base_dir: Path, cache: Optional[PipelineCache] = None):
        self.base_dir = Path(base_dir)
        self.cache = cache

    def extract_comparison_pair(
        self,
        email: Dict[str, Any],
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        Given a BL_COMPARISON email, returns:
        (ready_for_compare_payload, early_decision_dict)

        If an edge case (missing attachment, corrupt file, wrong doc) is detected,
        ready_for_compare_payload is None and early_decision_dict contains the
        NEEDS_REVIEW outcome.
        """
        eid = email["email_id"]
        attachments = email.get("attachments", [])

        # 1. Check missing attachment (< 2 attachments)
        if len(attachments) < 2:
            return None, {
                "category": "BL_COMPARISON",
                "status": "NEEDS_REVIEW",
                "review_reason": "missing_attachment",
                "defect_fields": [],
                "has_defect": False,
            }

        # 2. Identify SI and BL attachment paths
        si_path = None
        bl_path = None
        for a in attachments:
            a_upper = a.upper()
            if "_SI." in a_upper or "SHIPPING INSTRUCTION" in a_upper:
                si_path = a
            elif "_BL." in a_upper or "BILL OF LADING" in a_upper:
                bl_path = a

        # Fallback if names do not contain _SI or _BL
        if not si_path or not bl_path:
            # If 2 attachments exist, check if one is SI and other BL
            if len(attachments) == 2:
                if "_SI" in attachments[0].upper():
                    si_path, bl_path = attachments[0], attachments[1]
                elif "_BL" in attachments[0].upper():
                    bl_path, si_path = attachments[0], attachments[1]
                else:
                    # Non-standard doc types
                    return None, {
                        "category": "BL_COMPARISON",
                        "status": "NEEDS_REVIEW",
                        "review_reason": "wrong_doc_type",
                        "defect_fields": [],
                        "has_defect": False,
                    }
            else:
                return None, {
                    "category": "BL_COMPARISON",
                    "status": "NEEDS_REVIEW",
                    "review_reason": "missing_attachment",
                    "defect_fields": [],
                    "has_defect": False,
                }

        # 3. Parse SI document
        si_file = self.base_dir / si_path
        si_res = parse_attachment(si_file)
        if si_res.is_corrupted or not si_res.success:
            logger.warning("%s: SI attachment corrupt or unreadable: %s", eid, si_res.error_message)
            return None, {
                "category": "BL_COMPARISON",
                "status": "NEEDS_REVIEW",
                "review_reason": "unreadable",
                "defect_fields": [],
                "has_defect": False,
            }

        # 4. Parse BL document
        bl_file = self.base_dir / bl_path
        bl_res = parse_attachment(bl_file)
        if bl_res.is_corrupted or not bl_res.success:
            logger.warning("%s: BL attachment corrupt or unreadable: %s", eid, bl_res.error_message)
            return None, {
                "category": "BL_COMPARISON",
                "status": "NEEDS_REVIEW",
                "review_reason": "unreadable",
                "defect_fields": [],
                "has_defect": False,
            }

        # Check if both are empty/scanned with no text
        if (si_res.is_scanned or len(si_res.text.strip()) == 0) and (bl_res.is_scanned or len(bl_res.text.strip()) == 0):
            # Scanned image files with no OCR text
            return None, {
                "category": "BL_COMPARISON",
                "status": "NEEDS_REVIEW",
                "review_reason": "unreadable",
                "defect_fields": [],
                "has_defect": False,
            }

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
