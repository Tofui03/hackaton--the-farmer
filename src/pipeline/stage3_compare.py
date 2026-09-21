import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from src.cache import PipelineCache
from src.llm.client import GeminiClient
from src.llm.prompts import DOC_COMPARE_SYSTEM_PROMPT, build_doc_compare_prompt

logger = logging.getLogger(__name__)

VALID_7_FIELDS = [
    "shipper",
    "consignee",
    "notify_party",
    "port_of_loading",
    "port_of_discharge",
    "container_count",
    "gross_weight_kg",
]


def normalize_text_field(val: str) -> str:
    """Normalize company or entity names: strip suffixes, punctuation, whitespace."""
    if not val:
        return ""
    s = val.upper()
    s = re.sub(r"[^\w\s]", " ", s)
    # Remove common corporate suffixes
    suffixes = [
        r"\bSDN\s+BHD\b",
        r"\bBHD\b",
        r"\bLTD\b",
        r"\bLIMITED\b",
        r"\bLLC\b",
        r"\bCORP\b",
        r"\bCORPORATION\b",
        r"\bCO\b",
        r"\bINC\b",
        r"\bGMBH\b",
        r"\bPTE\b",
        r"\bS\s*P\b",
    ]
    for suf in suffixes:
        s = re.sub(suf, "", s)
    return re.sub(r"\s+", " ", s).strip()


def normalize_port(val: str) -> str:
    """Normalize port: extract UN/LOCODE or port name."""
    if not val:
        return ""
    s = val.upper()
    # Check for UN/LOCODE in parentheses e.g. (MYPKG)
    match = re.search(r"\(([A-Z]{5})\)", s)
    if match:
        return match.group(1)
    # Strip common prefixes/suffixes
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def normalize_container_count(val: str) -> Optional[int]:
    """Extract integer count of containers, e.g. '1 x 40 HC' -> 1."""
    if not val:
        return None
    # Look for patterns like '1 x 40', '15X20', '3 containers', or just '3'
    m = re.search(r"(\d+)\s*(?:X|CONTAINER)", val, re.IGNORECASE)
    if m:
        return int(m.group(1))
    digits = re.findall(r"\b\d+\b", val)
    if digits:
        return int(digits[0])
    return None


def normalize_weight_kg(val: str) -> Optional[float]:
    """Normalize weight to float kg."""
    if not val:
        return None
    # Remove commas
    clean = val.replace(",", "")
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:KG|KGS)?", clean, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return None


def extract_fields_from_text(text: str) -> Dict[str, str]:
    """Rule-based extractor for standard text/table templates."""
    fields = {k: "" for k in VALID_7_FIELDS}
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    for line in lines:
        upper = line.upper()

        # Shipper
        if ("SHIPPER" in upper or "EXPORTER" in upper) and not fields["shipper"]:
            parts = re.split(r"[:|]", line, 1)
            if len(parts) > 1:
                fields["shipper"] = parts[1].strip()

        # Consignee
        elif "CONSIGNEE" in upper and not fields["consignee"]:
            parts = re.split(r"[:|]", line, 1)
            if len(parts) > 1:
                fields["consignee"] = parts[1].strip()

        # Notify Party
        elif ("NOTIFY" in upper) and not fields["notify_party"]:
            parts = re.split(r"[:|]", line, 1)
            if len(parts) > 1:
                fields["notify_party"] = parts[1].strip()

        # Port of Loading
        elif ("PORT OF LOADING" in upper or "LOAD PORT" in upper or "POL" in upper) and not fields["port_of_loading"]:
            parts = re.split(r"[:|]", line, 1)
            if len(parts) > 1:
                fields["port_of_loading"] = parts[1].strip()

        # Port of Discharge
        elif ("DISCHARGE PORT" in upper or "PORT OF DISCHARGE" in upper or "POD" in upper) and not fields["port_of_discharge"]:
            parts = re.split(r"[:|]", line, 1)
            if len(parts) > 1:
                fields["port_of_discharge"] = parts[1].strip()

        # Container count
        elif ("CONTAINER" in upper or "NO. OF CONTAINERS" in upper or "PACKAGES" in upper) and not fields["container_count"]:
            parts = re.split(r"[:|]", line, 1)
            if len(parts) > 1:
                fields["container_count"] = parts[1].strip()

        # Gross Weight
        elif ("GROSS WEIGHT" in upper or "GROSS WT" in upper or "WEIGHT (KG)" in upper) and not fields["gross_weight_kg"]:
            parts = re.split(r"[:|]", line, 1)
            if len(parts) > 1:
                fields["gross_weight_kg"] = parts[1].strip()

    return fields


def rule_based_compare(si_text: str, bl_text: str) -> Dict[str, Any]:
    """Deterministic comparison baseline."""
    si_fields = extract_fields_from_text(si_text)
    bl_fields = extract_fields_from_text(bl_text)

    # Check for missing values
    missing_fields = []
    for f in VALID_7_FIELDS:
        if not si_fields.get(f) or not bl_fields.get(f):
            missing_fields.append(f)

    if missing_fields:
        # If critical fields are missing, escalate to NEEDS_REVIEW (missing_value)
        return {
            "status": "NEEDS_REVIEW",
            "review_reason": "missing_value",
            "has_defect": False,
            "defect_fields": [],
        }

    defects = []

    # 1. Text entity comparisons
    for f in ["shipper", "consignee", "notify_party"]:
        si_norm = normalize_text_field(si_fields[f])
        bl_norm = normalize_text_field(bl_fields[f])
        if si_norm != bl_norm:
            # Check prefix or substring if high similarity
            if si_norm not in bl_norm and bl_norm not in si_norm:
                defects.append(f)

    # 2. Ports
    for f in ["port_of_loading", "port_of_discharge"]:
        si_port = normalize_port(si_fields[f])
        bl_port = normalize_port(bl_fields[f])
        if si_port != bl_port:
            defects.append(f)

    # 3. Containers
    si_cnt = normalize_container_count(si_fields["container_count"])
    bl_cnt = normalize_container_count(bl_fields["container_count"])
    if si_cnt is not None and bl_cnt is not None and si_cnt != bl_cnt:
        defects.append("container_count")

    # 4. Weight
    si_wt = normalize_weight_kg(si_fields["gross_weight_kg"])
    bl_wt = normalize_weight_kg(bl_fields["gross_weight_kg"])
    if si_wt is not None and bl_wt is not None and abs(si_wt - bl_wt) > 1.0:
        defects.append("gross_weight_kg")

    if defects:
        return {
            "status": "MISMATCH",
            "review_reason": None,
            "has_defect": True,
            "defect_fields": sorted(defects),
        }
    else:
        return {
            "status": "OK",
            "review_reason": None,
            "has_defect": False,
            "defect_fields": [],
        }


class Stage3Comparator:
    """Compares SI vs draft BL using Gemini API with deterministic fallback."""

    def __init__(
        self,
        gemini_client: Optional[GeminiClient] = None,
        cache: Optional[PipelineCache] = None,
    ):
        self.gemini_client = gemini_client
        self.cache = cache

    def compare(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Perform comparison on ready payload."""
        eid = payload["email_id"]

        # Check cache
        if self.cache:
            cached = self.cache.get_comparison(eid)
            if cached:
                return cached

        # Use Gemini LLM if ready
        if self.gemini_client and self.gemini_client.is_ready():
            prompt = build_doc_compare_prompt(
                email_id=eid,
                email_meta=payload["email_meta"],
                si_text=payload["si_text"],
                bl_text=payload["bl_text"],
            )
            try:
                raw_res = self.gemini_client.generate_json(
                    system_instruction=DOC_COMPARE_SYSTEM_PROMPT,
                    user_prompt=prompt,
                )
                status = raw_res.get("status", "OK")
                reason = raw_res.get("review_reason")
                has_defect = raw_res.get("has_defect", False)
                defect_fields = raw_res.get("defect_fields", [])

                # Enforce schema validity
                if status == "MISMATCH":
                    has_defect = True
                    reason = None
                    # filter to valid 7 fields
                    defect_fields = [f for f in defect_fields if f in VALID_7_FIELDS]
                    if not defect_fields:
                        status = "OK"
                        has_defect = False
                elif status == "OK":
                    has_defect = False
                    reason = None
                    defect_fields = []
                elif status == "NEEDS_REVIEW":
                    has_defect = False
                    defect_fields = []
                    if reason not in ["wrong_doc_type", "missing_attachment", "unreadable", "missing_value"]:
                        reason = "unreadable"

                result = {
                    "category": "BL_COMPARISON",
                    "status": status,
                    "review_reason": reason,
                    "has_defect": has_defect,
                    "defect_fields": defect_fields,
                }
                if self.cache:
                    self.cache.set_comparison(eid, result)
                    self.cache.save()
                return result
            except Exception as e:
                logger.error("%s: LLM comparison failed: %s. Falling back to rule-based comparison.", eid, e)

        # Fallback to rule-based comparison
        res = rule_based_compare(payload["si_text"], payload["bl_text"])
        result = {
            "category": "BL_COMPARISON",
            "status": res["status"],
            "review_reason": res["review_reason"],
            "has_defect": res["has_defect"],
            "defect_fields": res["defect_fields"],
        }
        if self.cache:
            self.cache.set_comparison(eid, result)
            self.cache.save()
        return result
