from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple, Union

from src.llm.base_adapter import BaseAIAdapter
from src.llm.evidence_validator import validate_evidence_grounding
from src.llm.schemas import DocumentFieldExtractionOutput, ExtractedFieldRaw
from src.models.audit import AttemptTracker
from src.models.document import Role
from src.models.evidence import FieldEvidence
from src.models.extraction import (
    FIELD_NAMES,
    DocumentExtraction,
    ExtractedField,
    FieldCandidate,
    FieldName,
    FieldReliability,
    NormalizedField,
)
from src.normalization.text_normalizer import normalize_text
from src.normalization.unit_normalizer import (
    normalize_container_count,
    normalize_gross_weight_kg,
)

logger = logging.getLogger(__name__)

FIELD_ALIASES: Dict[FieldName, List[str]] = {
    "shipper": [
        "SHIPPER / EXPORTER",
        "SHIPPER/EXPORTER",
        "CONSIGNOR / EXPORTER",
        "CONSIGNOR/EXPORTER",
        "SHIPPER NAME",
        "SHIPPER",
        "CONSIGNOR",
        "EXPORTER",
    ],
    "consignee": [
        "CONSIGNEE / IMPORTER",
        "CONSIGNEE/IMPORTER",
        "CONSIGNEE NAME",
        "CONSIGNEE",
        "TO THE ORDER OF",
        "RECEIVER",
        "IMPORTER",
        "SOLD TO",
        "DELIVER TO",
    ],
    "notify_party": [
        "NOTIFY PARTY / APPLICANT",
        "NOTIFY PARTY",
        "NOTIFY APPLICANT",
        "NOTIFY ADDRESS",
        "ALSO NOTIFY",
        "NOTIFY",
    ],
    "port_of_loading": [
        "PORT OF LOADING",
        "LOADING PORT",
        "POL",
        "PORT OF DEPARTURE",
        "AIRPORT OF DEPARTURE",
    ],
    "port_of_discharge": [
        "PORT OF DISCHARGE",
        "DISCHARGE PORT",
        "POD",
        "PORT OF ARRIVAL",
        "AIRPORT OF DESTINATION",
    ],
    "container_count": [
        "CONTAINER COUNT",
        "NO. OF CONTAINERS",
        "NUMBER OF CONTAINERS",
        "TOTAL CONTAINERS",
        "CONTAINER QTY",
        "CONTAINERS",
        "CONTAINER(S)",
        "QTY",
    ],
    "gross_weight_kg": [
        "TOTAL GROSS WEIGHT",
        "GROSS WEIGHT",
        "GROSS WT",
        "G.W.",
        "GW",
        "WEIGHT (KG)",
        "WEIGHT",
    ],
}

ALL_LABELS: List[str] = [
    alias for aliases in FIELD_ALIASES.values() for alias in aliases
] + [
    "DESCRIPTION OF GOODS",
    "DESCRIPTION",
    "GOODS",
    "MARKS AND NUMBERS",
    "MARKS",
    "VESSEL",
    "VOYAGE",
    "BOOKING NO",
    "B/L NO",
    "BL NO",
    "CARRIER",
    "DATE",
    "SEAL NO",
    "MEASUREMENT",
    "CBM",
]

NUMBER_WORDS: Dict[str, int] = {
    "ONE": 1,
    "TWO": 2,
    "THREE": 3,
    "FOUR": 4,
    "FIVE": 5,
    "SIX": 6,
    "SEVEN": 7,
    "EIGHT": 8,
    "NINE": 9,
    "TEN": 10,
    "ELEVEN": 11,
    "TWELVE": 12,
    "THIRTEEN": 13,
    "FOURTEEN": 14,
    "FIFTEEN": 15,
    "SIXTEEN": 16,
    "SEVENTEEN": 17,
    "EIGHTEEN": 18,
    "NINETEEN": 19,
    "TWENTY": 20,
}


def _is_section_header(line: str) -> bool:
    """Check if a line starts with a known document section header."""
    clean = line.strip().upper()
    for lbl in ALL_LABELS:
        if clean.startswith(lbl + ":") or clean.startswith(lbl + " :") or clean == lbl:
            return True
    return False


def _extract_multiline_block(
    lines: List[str], start_line_idx: int, initial_text: str
) -> str:
    """Extract a multi-line corporate address block without truncation (UT-EXT-003)."""
    block_lines = [initial_text] if initial_text.strip() else []

    idx = start_line_idx + 1
    while idx < len(lines):
        line = lines[idx]
        stripped = line.strip()

        # Stop on empty lines or when encountering another recognized section header
        if not stripped:
            break
        if _is_section_header(line):
            break

        block_lines.append(stripped)
        idx += 1

    return "\n".join(block_lines).strip()


def _parse_container_count_value(raw_str: str) -> Tuple[str, Optional[int]]:
    """Parse container count supporting spelled words and equipment summing (UT-EXT-007, UT-EXT-008)."""
    s = raw_str.strip()

    # 1. Multi-size equipment notation: '2 X 40HC, 1 X 20GP' -> 3 (UT-EXT-008)
    eq_matches = re.findall(r"(\d+)\s*[xX]\s*(?:\d+['\w]*)?", s)
    if len(eq_matches) >= 1:
        total = sum(int(cnt) for cnt in eq_matches)
        return s, total

    # 2. Parenthesized number format: 'Three (3) Containers' -> 3 (UT-EXT-007)
    paren_match = re.search(r"\((\d+)\)", s)
    if paren_match:
        return s, int(paren_match.group(1))

    # 3. Spelled English words: 'Three Containers' -> 3 (UT-EXT-007)
    upper_s = s.upper()
    for word, val in NUMBER_WORDS.items():
        if re.search(rf"\b{word}\b", upper_s):
            return s, val

    # 4. Standard discrete integer: '  3  ' or '2 Containers'
    num_match = re.search(r"\b(\d+)\b", s)
    if num_match:
        return s, int(num_match.group(1))

    return s, None


def _find_verbatim_quote(document_text: str, candidate_text: str) -> Optional[str]:
    """Find the exact verbatim substring in document_text matching candidate_text."""
    if not candidate_text:
        return None
    # 1. Exact match
    if candidate_text in document_text:
        return candidate_text

    # 2. Case-insensitive search
    pattern = re.escape(candidate_text.strip())
    match = re.search(pattern, document_text, re.IGNORECASE)
    if match:
        return match.group(0)

    # 3. First line search
    first_line = candidate_text.splitlines()[0].strip()
    if first_line and first_line in document_text:
        return first_line

    match_first = re.search(re.escape(first_line), document_text, re.IGNORECASE)
    if match_first:
        return match_first.group(0)

    return None


class Stage3Extractor:
    """Stage 3 extraction engine with deterministic alias tables, AI fallback, and reliability gating."""

    def __init__(
        self,
        ai_adapter: Optional[BaseAIAdapter] = None,
    ):
        self.ai_adapter = ai_adapter

    def extract_document_fields(
        self,
        document_id: str,
        role: Role,
        document_text: str,
        tracker: Optional[AttemptTracker] = None,
    ) -> Tuple[DocumentExtraction, List[FieldEvidence]]:
        """Extract exactly the 7 mandatory fields for a single document."""
        lines = document_text.splitlines()
        fields_map: Dict[FieldName, ExtractedField] = {}
        all_evidence: List[FieldEvidence] = []

        # 1. Deterministic Extraction Pass (T10-01)
        raw_candidates: Dict[FieldName, Tuple[str, str]] = {}  # field -> (raw_value, quote)

        for field in FIELD_NAMES:
            aliases = FIELD_ALIASES[field]
            found_raw: Optional[str] = None
            found_quote: Optional[str] = None

            for alias in aliases:
                # Search for alias followed by colon or space
                pattern = re.compile(
                    rf"^[ \t]*{re.escape(alias)}[ \t]*(?::|-)[ \t]*(.*)$",
                    re.IGNORECASE | re.MULTILINE,
                )
                match = pattern.search(document_text)
                if match:
                    same_line_val = match.group(1).strip()
                    matched_line = match.group(0)

                    # For address fields (shipper/consignee/notify_party), capture multiline block
                    if field in ("shipper", "consignee", "notify_party"):
                        # Find line index of this match
                        match_start = match.start()
                        line_idx = document_text[:match_start].count("\n")
                        raw_val = _extract_multiline_block(
                            lines, line_idx, same_line_val
                        )
                    else:
                        raw_val = same_line_val

                    if raw_val:
                        found_raw = raw_val
                        # Find verbatim quote
                        verbatim = _find_verbatim_quote(document_text, raw_val)
                        found_quote = verbatim or matched_line
                        break

            if found_raw and found_quote:
                raw_candidates[field] = (found_raw, found_quote)

        # 2. AI Semantic Extraction Fallback (T10-02)
        missing_fields = [f for f in FIELD_NAMES if f not in raw_candidates]
        if missing_fields and self.ai_adapter is not None:
            try:
                ai_output: DocumentFieldExtractionOutput = (
                    self.ai_adapter.extract_fields(
                        document_text=document_text,
                        role=role,
                        tracker=tracker,
                    )
                )

                for f in missing_fields:
                    if f in ai_output.fields:
                        ai_field: ExtractedFieldRaw = ai_output.fields[f]
                        if ai_field.status == "FOUND" and ai_field.raw_value is not None:
                            # Validate source grounding (UT-EXT-013)
                            is_grounded, val_error = validate_evidence_grounding(
                                extracted_field=ai_field,
                                document_text=document_text,
                            )
                            if is_grounded:
                                val_str = str(ai_field.raw_value)
                                quote = ai_field.evidence or val_str
                                verbatim = _find_verbatim_quote(document_text, quote) or quote
                                raw_candidates[f] = (val_str, verbatim)
                            else:
                                logger.warning(
                                    "AI candidate for %s rejected as ungrounded: %s",
                                    f,
                                    val_error,
                                )
            except Exception as e:
                logger.warning("AI extraction fallback failed for %s: %s", document_id, e)

        # 3. Field-Level Reliability Gate & Normalization (T10-03)
        for field in FIELD_NAMES:
            if field in raw_candidates:
                raw_val, quote = raw_candidates[field]

                # Create source-grounded FieldEvidence
                ev_id = f"ev_{document_id}_{field}"
                ev = FieldEvidence(
                    evidence_id=ev_id,
                    source_type="document",
                    source_id=document_id,
                    kind="text_span",
                    quote=quote,
                )
                all_evidence.append(ev)

                # Deterministic Normalization
                norm_res: Optional[NormalizedField] = None
                if field == "container_count":
                    _, parsed_int = _parse_container_count_value(raw_val)
                    norm_res = normalize_container_count(parsed_int)
                elif field == "gross_weight_kg":
                    norm_res = normalize_gross_weight_kg(raw_val)
                else:
                    norm_res = normalize_text(field, raw_val)

                if norm_res is not None and norm_res.state == "VALID":
                    candidate = FieldCandidate(
                        raw_value=raw_val,
                        evidence_ids=[ev_id],
                    )
                    fields_map[field] = ExtractedField(
                        field=field,
                        reliability=FieldReliability.RELIABLE,
                        candidates=[candidate],
                        selected_candidate=0,
                        normalized=norm_res,
                        explanation=f"Field deterministically extracted and normalized with valid evidence: '{quote[:60]}'",
                    )
                else:
                    # Normalization invalid
                    fields_map[field] = ExtractedField(
                        field=field,
                        reliability=FieldReliability.UNCERTAIN,
                        candidates=[],
                        selected_candidate=None,
                        normalized=None,
                        explanation=f"Field extraction failed canonical normalization: raw '{raw_val}'",
                    )
            else:
                # Field missing completely (UT-EXT-011)
                fields_map[field] = ExtractedField(
                    field=field,
                    reliability=FieldReliability.MISSING,
                    candidates=[],
                    selected_candidate=None,
                    normalized=None,
                    explanation="Mandatory field absent from document text",
                )

        doc_extraction = DocumentExtraction(
            document_id=document_id,
            role=role,
            fields=fields_map,
        )

        return doc_extraction, all_evidence

    def extract_comparison_pair_fields(
        self,
        si_id: str,
        si_text: str,
        bl_id: str,
        bl_text: str,
        tracker: Optional[AttemptTracker] = None,
    ) -> Tuple[DocumentExtraction, DocumentExtraction, List[FieldEvidence]]:
        """Extract fields for both SI and BL documents in a comparison pair."""
        si_extraction, si_evidence = self.extract_document_fields(
            document_id=si_id,
            role="SI",
            document_text=si_text,
            tracker=tracker,
        )
        bl_extraction, bl_evidence = self.extract_document_fields(
            document_id=bl_id,
            role="BL",
            document_text=bl_text,
            tracker=tracker,
        )
        return si_extraction, bl_extraction, si_evidence + bl_evidence


def extract_fields_from_text(
    document_id: str,
    role: Role,
    document_text: str,
    ai_adapter: Optional[BaseAIAdapter] = None,
    tracker: Optional[AttemptTracker] = None,
) -> Tuple[DocumentExtraction, List[FieldEvidence]]:
    """Functional interface for extracting seven fields from document text."""
    extractor = Stage3Extractor(ai_adapter=ai_adapter)
    return extractor.extract_document_fields(
        document_id=document_id,
        role=role,
        document_text=document_text,
        tracker=tracker,
    )


__all__ = [
    "Stage3Extractor",
    "extract_fields_from_text",
    "FIELD_ALIASES",
]
