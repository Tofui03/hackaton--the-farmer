import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from src.cache import PipelineCache
from src.llm.client import GeminiClient
from src.llm.prompts import DOC_COMPARE_SYSTEM_PROMPT, build_doc_compare_prompt
from src.pipeline.schema import AuditOutputRecord, Discrepancy, HITLEscalation

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

# Field aliases according to Secret 1
FIELD_ALIASES = {
    "port_of_loading": [
        "PORT OF LOADING",
        "LOAD PORT",
        "POL",
        "LOADING PORT",
        "PORT OF LOAD",
    ],
    "port_of_discharge": [
        "PORT OF DISCHARGE",
        "DISCHARGE PORT",
        "POD",
        "DISCHARGING PORT",
        "DESTINATION PORT",
    ],
    "gross_weight_kg": [
        "GROSS WEIGHT",
        "TOTAL WEIGHT",
        "G.W.",
        "G.W",
        "CARGO WEIGHT",
        "GROSS WT",
        "WEIGHT (KG)",
        "TOTAL GROSS WEIGHT",
    ],
    "container_count": [
        "CONTAINER COUNT",
        "TOTAL CONTAINERS",
        "QTY OF UNITS",
        "QUANTITY OF UNITS",
        "NO. OF CONTAINERS",
        "NUMBER OF CONTAINERS",
        "NO. OF PACKAGES",
        "CONTAINERS",
    ],
    "shipper": [
        "SHIPPER",
        "EXPORTER",
        "SHIPPER/EXPORTER",
        "SHIPPER / EXPORTER",
    ],
    "consignee": [
        "CONSIGNEE",
        "CONSIGNEE (NON-NEGOTIABLE)",
        "RECEIVER",
    ],
    "notify_party": [
        "NOTIFY PARTY",
        "NOTIFY",
        "ALSO NOTIFY",
    ],
}

WORD_TO_DIGIT = {
    "ZERO": 0, "ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5,
    "SIX": 6, "SEVEN": 7, "EIGHT": 8, "NINE": 9, "TEN": 10,
    "ELEVEN": 11, "TWELVE": 12, "TWENTY": 20, "THIRTY": 30, "FORTY": 40,
}


def normalize_text_entity(val: str) -> str:
    """Normalize company or entity names: strip punctuation, corporate suffixes, whitespace."""
    if not val:
        return ""
    s = val.upper()
    # Replace punctuation with space
    s = re.sub(r"[^\w\s]", " ", s)
    # Remove common corporate entity suffixes
    suffixes = [
        r"\bSDN\s+BHD\b",
        r"\bBHD\b",
        r"\bLIMITED\b",
        r"\bLTD\b",
        r"\bLLC\b",
        r"\bCORP\b",
        r"\bCORPORATION\b",
        r"\bCO\b",
        r"\bINC\b",
        r"\bINCORPORATED\b",
        r"\bGMBH\b",
        r"\bPTE\b",
        r"\bS\s*P\b",
        r"\bPLC\b",
    ]
    for suf in suffixes:
        s = re.sub(suf, "", s)
    return re.sub(r"\s+", " ", s).strip()


def normalize_port_name(val: str) -> str:
    """Normalize port: prioritize UN/LOCODE e.g. (MYPKG), then city name."""
    if not val:
        return ""
    s = val.upper()
    # Check for UN/LOCODE in parentheses e.g. (MYPKG) or (PECLL)
    match = re.search(r"\(([A-Z]{5})\)", s)
    if match:
        return match.group(1)
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def normalize_container_count(val: str) -> Optional[int]:
    """
    Extract pure Arabic number for container count.
    Handles 'Three (3) Containers', '1 x 40 HC', '15X20', etc.
    """
    if not val:
        return None
    s = val.strip().upper()

    # 1. Check parenthetical digit first, e.g. 'Three (3) Containers' -> 3
    paren_match = re.search(r"\((\d+)\)", s)
    if paren_match:
        return int(paren_match.group(1))

    # 2. Check pattern like '1 x 40' or '15X20'
    x_match = re.search(r"(\d+)\s*(?:X|CONTAINER)", s)
    if x_match:
        return int(x_match.group(1))

    # 3. Check for spelled out words e.g. 'Three Containers'
    for word, digit in WORD_TO_DIGIT.items():
        if re.search(rf"\b{word}\b", s):
            return digit

    # 4. Fallback to any standalone integer
    digits = re.findall(r"\b\d+\b", s)
    if digits:
        return int(digits[0])

    return None


def normalize_gross_weight_kg(val: str) -> Optional[float]:
    """
    Convert gross weight to numerical kg.
    Handles MT (Metric Tons * 1000), comma thousand-separators, and 'KG'.
    """
    if not val:
        return None
    s = val.replace(",", "").strip().upper()

    # Check for MT / Metric Tons (1 MT = 1000 kg)
    mt_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:MT|METRIC\s*TON|TONS?)\b", s)
    if mt_match:
        return float(mt_match.group(1)) * 1000.0

    # Check for KG / KGS
    kg_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:KG|KGS)?", s)
    if kg_match:
        return float(kg_match.group(1))

    return None


def extract_fields_with_aliases(text: str) -> Dict[str, str]:
    """Extract standard 7 fields using the comprehensive alias table."""
    fields = {k: "" for k in VALID_7_FIELDS}
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    for line in lines:
        if ":" in line or "|" in line:
            delim = ":" if ":" in line else "|"
            hdr, val = line.split(delim, 1)
            hdr_u = hdr.upper().strip()
            val = val.strip()

            for field_name, aliases in FIELD_ALIASES.items():
                if not fields[field_name] and any(alias in hdr_u for alias in aliases):
                    fields[field_name] = val
                    break

    return fields


def rule_based_compare_audit(
    email_id: str,
    si_text: str,
    bl_text: str,
) -> AuditOutputRecord:
    """
    Evaluate SI vs BL using Secret 1 (Zero False Alarms) and Secret 2 (SI as Golden Reference).
    Returns an AuditOutputRecord adhering strictly to the user's output contract.
    """
    si_fields = extract_fields_with_aliases(si_text)
    bl_fields = extract_fields_with_aliases(bl_text)

    # Secret 3: Check for missing required values (HITL trigger)
    missing_fields = []
    for f in VALID_7_FIELDS:
        if not si_fields.get(f) or not bl_fields.get(f):
            missing_fields.append(f)

    if missing_fields:
        return AuditOutputRecord(
            email_id=email_id,
            category="document_comparison",
            mismatch_detected=False,
            result_summary="Human review required: Missing mandatory field value(s)",
            discrepancies=[],
            hitl_escalation=HITLEscalation(
                needed=True,
                reason="missing_value",
                evidence=f"Missing fields in document: {', '.join(missing_fields)}",
            ),
        )

    discrepancies: List[Discrepancy] = []

    # 1. Text entity comparisons (shipper, consignee, notify_party)
    for f in ["shipper", "consignee", "notify_party"]:
        si_raw = si_fields[f]
        bl_raw = bl_fields[f]
        si_norm = normalize_text_entity(si_raw)
        bl_norm = normalize_text_entity(bl_raw)

        # Zero False Alarm: if core entity matches or is substring, consider Match
        if si_norm != bl_norm:
            if si_norm not in bl_norm and bl_norm not in si_norm:
                discrepancies.append(
                    Discrepancy(field=f, si_value=si_raw, bl_value=bl_raw)
                )

    # 2. Ports (port_of_loading, port_of_discharge)
    for f in ["port_of_loading", "port_of_discharge"]:
        si_raw = si_fields[f]
        bl_raw = bl_fields[f]
        si_port = normalize_port_name(si_raw)
        bl_port = normalize_port_name(bl_raw)

        if si_port != bl_port:
            if si_port not in bl_port and bl_port not in si_port:
                discrepancies.append(
                    Discrepancy(field=f, si_value=si_raw, bl_value=bl_raw)
                )

    # 3. Container Count
    si_cnt = normalize_container_count(si_fields["container_count"])
    bl_cnt = normalize_container_count(bl_fields["container_count"])
    if si_cnt is not None and bl_cnt is not None and si_cnt != bl_cnt:
        discrepancies.append(
            Discrepancy(
                field="container_count",
                si_value=si_cnt,
                bl_value=bl_cnt,
            )
        )

    # 4. Gross Weight (kg)
    si_wt = normalize_gross_weight_kg(si_fields["gross_weight_kg"])
    bl_wt = normalize_gross_weight_kg(bl_fields["gross_weight_kg"])
    if si_wt is not None and bl_wt is not None and abs(si_wt - bl_wt) > 1.0:
        discrepancies.append(
            Discrepancy(
                field="gross_weight_kg",
                si_value=si_wt,
                bl_value=bl_wt,
            )
        )

    if discrepancies:
        # Secret 2: format discrepancy summary
        diff_strs = [f"{d.field} (SI: {d.si_value} / BL: {d.bl_value})" for d in discrepancies]
        summary = f"Mismatches detected: {'; '.join(diff_strs)}"
        return AuditOutputRecord(
            email_id=email_id,
            category="document_comparison",
            mismatch_detected=True,
            result_summary=summary,
            discrepancies=discrepancies,
            hitl_escalation=HITLEscalation(needed=False),
        )
    else:
        # Secret 2: Exact phrase required when all 7 fields match
        return AuditOutputRecord(
            email_id=email_id,
            category="document_comparison",
            mismatch_detected=False,
            result_summary="No mismatch detected",
            discrepancies=[],
            hitl_escalation=HITLEscalation(needed=False),
        )


class Stage3Comparator:
    """Audit comparator integrating Gemini LLM and deterministic Zero-False-Alarm logic."""

    def __init__(
        self,
        gemini_client: Optional[GeminiClient] = None,
        cache: Optional[PipelineCache] = None,
    ):
        self.gemini_client = gemini_client
        self.cache = cache

    def compare(self, payload: Dict[str, Any]) -> AuditOutputRecord:
        """Compare SI vs BL and return an AuditOutputRecord adhering to contract."""
        eid = payload["email_id"]

        # 1. Check cache
        if self.cache:
            cached = self.cache.get_comparison(eid)
            if cached and "result_summary" in cached:
                return AuditOutputRecord(**cached)

        # 2. Use Gemini if ready
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
                defect_fields = raw_res.get("defect_fields", [])
                si_data = raw_res.get("extracted_si", {})
                bl_data = raw_res.get("extracted_bl", {})

                if status == "NEEDS_REVIEW":
                    record = AuditOutputRecord(
                        email_id=eid,
                        category="document_comparison",
                        mismatch_detected=False,
                        result_summary=f"Human review required: {reason or 'unreadable'}",
                        discrepancies=[],
                        hitl_escalation=HITLEscalation(
                            needed=True,
                            reason=reason or "unreadable",
                            evidence=raw_res.get("discrepancy_explanation", "LLM flagged uncertainty"),
                        ),
                    )
                elif status == "MISMATCH" and defect_fields:
                    discrepancies = [
                        Discrepancy(
                            field=f,
                            si_value=si_data.get(f, "SI value"),
                            bl_value=bl_data.get(f, "BL value"),
                        )
                        for f in defect_fields
                        if f in VALID_7_FIELDS
                    ]
                    diff_strs = [f"{d.field} (SI: {d.si_value} / BL: {d.bl_value})" for d in discrepancies]
                    record = AuditOutputRecord(
                        email_id=eid,
                        category="document_comparison",
                        mismatch_detected=True,
                        result_summary=f"Mismatches detected: {'; '.join(diff_strs)}",
                        discrepancies=discrepancies,
                        hitl_escalation=HITLEscalation(needed=False),
                    )
                else:
                    record = AuditOutputRecord(
                        email_id=eid,
                        category="document_comparison",
                        mismatch_detected=False,
                        result_summary="No mismatch detected",
                        discrepancies=[],
                        hitl_escalation=HITLEscalation(needed=False),
                    )

                if self.cache:
                    self.cache.set_comparison(eid, record.model_dump())
                    self.cache.save()
                return record
            except Exception as e:
                logger.error("%s: Gemini comparison failed: %s; falling back to deterministic audit.", eid, e)

        # 3. Fallback: Deterministic Zero-False-Alarm Audit
        record = rule_based_compare_audit(
            email_id=eid,
            si_text=payload["si_text"],
            bl_text=payload["bl_text"],
        )

        if self.cache:
            self.cache.set_comparison(eid, record.model_dump())
            self.cache.save()

        return record
