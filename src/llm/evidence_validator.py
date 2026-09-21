from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Union
from src.models.evidence import EvidenceKind, FieldEvidence

logger = logging.getLogger(__name__)


def validate_evidence_grounding(
    evidence: Union[FieldEvidence, Dict[str, Any], str],
    source_text: Optional[str] = None,
    page_count: Optional[int] = None,
    confidence: Optional[Union[float, str]] = None,
) -> bool:
    """Validate that extracted evidence is empirically grounded in source document content.
    
    Invariants (T07-03, REG-011, UT-EXT-013):
    1. Confidence Decoupling: Even if confidence is 1.0 or HIGH, ungrounded evidence is REJECTED.
    2. text_span: Verbatim quote MUST be present in source_text. Missing or hallucinated quotes fail.
    3. page_region: Bounding box coordinates must be normalized and ordered, page within page_count.
    4. table_cell: Coordinates (table, row, col) must be specified and valid.
    """
    # 1. Normalize input to FieldEvidence or dictionary representation
    quote: Optional[str] = None
    kind: str = "text_span"
    location: Optional[Dict[str, Any]] = None

    if isinstance(evidence, str):
        quote = evidence.strip()
        kind = "text_span"
    elif isinstance(evidence, FieldEvidence):
        quote = str(evidence.quote).strip() if evidence.quote else None
        kind = str(evidence.kind.value if isinstance(evidence.kind, EvidenceKind) else evidence.kind)
        if evidence.location:
            location = evidence.location.model_dump()
    elif isinstance(evidence, dict):
        quote = str(evidence.get("quote") or evidence.get("evidence", "")).strip() or None
        kind = str(evidence.get("kind", "text_span"))
        location = evidence.get("location")

    # 2. Validate based on evidence kind
    if kind in ("text_span", "text"):
        if not quote:
            logger.warning("Rejected text_span evidence: missing quote.")
            return False
        if source_text is None:
            logger.warning("Rejected text_span evidence: source_text is None.")
            return False
        # Invariant: quote must exist as a verbatim substring in parsed source text (UT-EXT-013)
        if quote not in source_text:
            logger.warning("Rejected ungrounded quote not found in source text: %r", quote)
            return False
        return True

    elif kind in ("page_region", "ocr_box", "ocr_region"):
        if not location or "bbox" not in location:
            logger.warning("Rejected region evidence: missing bbox.")
            return False
        bbox = location["bbox"]
        if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
            return False
        x0, y0, x1, y1 = bbox
        if not (0.0 <= x0 < x1 <= 1.0 and 0.0 <= y0 < y1 <= 1.0):
            logger.warning("Rejected region evidence: invalid bbox geometry %s", bbox)
            return False
        page = location.get("page")
        if page is None or page < 1:
            return False
        if page_count is not None and page > page_count:
            return False
        return True

    elif kind in ("table_cell", "cell"):
        if not location:
            return False
        table = location.get("table")
        row = location.get("row")
        col = location.get("column")
        if table is None or row is None or col is None:
            return False
        if row < 0 or col < 0:
            return False
        return True

    elif kind in ("document_metadata", "processing_error", "human_review"):
        # Contextual evidence types must have non-empty detail
        detail = evidence.detail if isinstance(evidence, FieldEvidence) else (
            evidence.get("detail") if isinstance(evidence, dict) else None
        )
        return bool(detail and str(detail).strip())

    return False


__all__ = [
    "validate_evidence_grounding",
]
