from __future__ import annotations

from abc import ABC, abstractmethod
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.models.document import ParserResult, ParserStatus

logger = logging.getLogger(__name__)

# Standard directory for synthetic AI/OCR fixtures
_OCR_FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "tests" / "fixtures" / "ai" / "ocr"


def validate_bounding_box(
    bbox: List[float] | Tuple[float, float, float, float]
) -> bool:
    """Validate normalized bounding box coordinates.
    
    Coordinates must satisfy 0.0 <= x0 < x1 <= 1.0 and 0.0 <= y0 < y1 <= 1.0.
    Inverted, negative, or out-of-range geometry returns False.
    """
    if len(bbox) != 4:
        return False
    x0, y0, x1, y1 = bbox
    return (
        0.0 <= x0 < x1 <= 1.0
        and 0.0 <= y0 < y1 <= 1.0
    )


def normalize_pixel_box(
    pixel_box: Dict[str, Any],
    width: int,
    height: int,
) -> Optional[List[float]]:
    """Convert pixel bounding box (xmin, ymin, xmax, ymax) to normalized coordinates.
    
    Returns normalized [x0, y0, x1, y1] or None if dimensions or coordinates are invalid.
    """
    if width <= 0 or height <= 0:
        return None
    xmin = pixel_box.get("xmin")
    ymin = pixel_box.get("ymin")
    xmax = pixel_box.get("xmax")
    ymax = pixel_box.get("ymax")
    if None in (xmin, ymin, xmax, ymax):
        return None

    try:
        x0 = float(xmin) / float(width)
        y0 = float(ymin) / float(height)
        x1 = float(xmax) / float(width)
        y1 = float(ymax) / float(height)
    except (ValueError, TypeError, ZeroDivisionError):
        return None

    coords = [round(x0, 4), round(y0, 4), round(x1, 4), round(y1, 4)]
    if validate_bounding_box(coords):
        return coords
    return None


class BaseVisionAdapter(ABC):
    """Abstract interface for OCR / Multimodal Vision recovery adapters."""

    @abstractmethod
    def recover_document(
        self,
        file_path: Path,
        document_id: Optional[str] = None,
    ) -> ParserResult:
        """Attempt to recover document text, layout, and region grounding from image/scan."""
        pass


class MockVisionAdapter(BaseVisionAdapter):
    """Deterministic, offline-testable Vision/OCR adapter for CI and automated testing.
    
    Supports:
    - Loading synthetic OCR fixtures from tests/fixtures/ai/ocr/
    - Simulating technical transient faults with bounded retries (DEC-AI-P01)
    - Simulating total provider exhaustion escalating to processing_or_provider_failure
    - Partial degradation handling (DEC-AI-P04 / AI-OCR-002)
    - Unreadable mandatory fields (AI-OCR-003) and conflicting readings (AI-OCR-004)
    """

    def __init__(
        self,
        fixture_path: Optional[Path] = None,
        fixture_data: Optional[Dict[str, Any]] = None,
        simulated_faults: Optional[List[str]] = None,
        technical_attempt_limit: int = 3,
        fixtures_dir: Optional[Path] = None,
    ):
        self.fixture_path = fixture_path
        self.fixture_data = fixture_data
        self.simulated_faults = list(simulated_faults) if simulated_faults else []
        self.technical_attempt_limit = technical_attempt_limit
        self.fixtures_dir = fixtures_dir or _OCR_FIXTURES_DIR
        self.call_count = 0
        self.recorded_attempts: List[str] = []

    def _find_fixture_payload(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Find matching synthetic fixture payload by document_id or filename."""
        if self.fixture_data is not None:
            return self.fixture_data

        if self.fixture_path is not None and self.fixture_path.exists():
            try:
                return json.loads(self.fixture_path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning("Failed to load specified fixture %s: %s", self.fixture_path, e)
                return None

        # Search in fixtures_dir (both valid and failures subdirectories)
        candidates = [
            self.fixtures_dir / "valid" / "ocr_valid_full_recovery.json",
            self.fixtures_dir / "valid" / "ocr_valid_partial_clean_fields.json",
            self.fixtures_dir / "failures" / "ocr_unreadable_mandatory_field.json",
            self.fixtures_dir / "failures" / "ocr_conflicting_readings.json",
        ]

        for cand in candidates:
            if cand.exists():
                try:
                    payload = json.loads(cand.read_text(encoding="utf-8"))
                    cand_doc_id = payload.get("document_id", "")
                    if cand_doc_id == doc_id or cand.name == doc_id:
                        return payload
                except Exception:
                    continue

        # If doc_id specifically hints at readable vs degraded
        if "001" in doc_id or "readable" in doc_id:
            target = self.fixtures_dir / "valid" / "ocr_valid_full_recovery.json"
            if target.exists():
                return json.loads(target.read_text(encoding="utf-8"))
        elif "002" in doc_id or "degraded" in doc_id:
            target = self.fixtures_dir / "valid" / "ocr_valid_partial_clean_fields.json"
            if target.exists():
                return json.loads(target.read_text(encoding="utf-8"))
        elif "stained" in doc_id:
            target = self.fixtures_dir / "failures" / "ocr_unreadable_mandatory_field.json"
            if target.exists():
                return json.loads(target.read_text(encoding="utf-8"))
        elif "lowres" in doc_id or "ambiguous" in doc_id:
            target = self.fixtures_dir / "failures" / "ocr_conflicting_readings.json"
            if target.exists():
                return json.loads(target.read_text(encoding="utf-8"))

        return None

    def recover_document(
        self,
        file_path: Path,
        document_id: Optional[str] = None,
    ) -> ParserResult:
        doc_id = document_id or file_path.name
        self.call_count += 1
        attempts: List[str] = []

        # 1. Bounded Technical Retry Simulation (DEC-AI-P01, AI-OCR-005, AI-OCR-006)
        # Process configured simulated technical faults
        attempt_num = 1
        while self.simulated_faults and attempt_num <= self.technical_attempt_limit:
            fault = self.simulated_faults.pop(0)
            att_id = f"att_ocr_{doc_id}_{attempt_num}"
            attempts.append(att_id)
            self.recorded_attempts.append(att_id)

            if attempt_num == self.technical_attempt_limit and fault in (
                "rate_limit_429",
                "provider_unavailable_503",
                "timeout",
                "connection_error",
                "provider_failure",
            ):
                # Retries exhausted -> escalate to processing_or_provider_failure
                return ParserResult(
                    document_id=doc_id,
                    status=ParserStatus.UNREADABLE,
                    text=None,
                    usable_for_extraction=False,
                    diagnostic_evidence_ids=[f"diag_provider_failure_exhausted_{doc_id}"],
                    attempt_ids=attempts,
                    error_message="processing_or_provider_failure",
                    is_scanned=True,
                    metadata={
                        "recovery_method": "ocr_vision",
                        "adapter": "MockVisionAdapter",
                        "failure_reason": "processing_or_provider_failure",
                        "total_attempts": str(len(attempts)),
                    },
                )
            attempt_num += 1

        # Current successful attempt
        att_id = f"att_ocr_{doc_id}_{attempt_num}"
        attempts.append(att_id)
        self.recorded_attempts.append(att_id)

        # 2. Retrieve fixture data
        payload = self._find_fixture_payload(doc_id)
        if payload is None:
            # Empty / missing payload -> Recovery failure
            return ParserResult(
                document_id=doc_id,
                status=ParserStatus.UNREADABLE,
                text=None,
                usable_for_extraction=False,
                diagnostic_evidence_ids=[f"diag_ocr_payload_not_found_{doc_id}"],
                attempt_ids=attempts,
                error_message="empty_or_missing_ocr_recovery_payload",
                is_scanned=True,
                metadata={
                    "recovery_method": "ocr_vision",
                    "adapter": "MockVisionAdapter",
                    "document_id": doc_id,
                },
            )

        # 3. Post-Recovery Validation of Payload
        raster_dims = payload.get("raster_dimensions", {})
        width = raster_dims.get("width", 600)
        height = raster_dims.get("height", 800)

        fields_data: Dict[str, Any] = payload.get("fields", {})
        confidence = str(payload.get("confidence_indicator", "HIGH"))
        footer_legible = payload.get("footer_terms_legible", True)

        # Extract textual fragments and validate bounding boxes
        text_fragments: List[str] = []
        valid_ocr_boxes: Dict[str, List[float]] = {}
        unreadable_fields: List[str] = []
        conflicting_fields: Dict[str, List[str]] = {}

        for field_name, field_info in fields_data.items():
            raw_val = field_info.get("raw_value")
            field_status = field_info.get("status", "FOUND")

            if field_status == "UNREADABLE":
                unreadable_fields.append(field_name)
            elif field_status == "CONFLICTING":
                candidates = field_info.get("candidates", [])
                cand_vals = [str(c.get("raw_value")) for c in candidates if "raw_value" in c]
                conflicting_fields[field_name] = cand_vals
            elif raw_val is not None:
                text_fragments.append(str(raw_val))

            # Grounding: Validate bounding box geometry if present
            pixel_box = field_info.get("ocr_box")
            if pixel_box:
                normalized = normalize_pixel_box(pixel_box, width, height)
                if normalized:
                    valid_ocr_boxes[field_name] = normalized
                else:
                    logger.warning("Rejected invalid bounding box geometry for %s: %s", field_name, pixel_box)

        # In case explicit text is provided in payload
        if "text" in payload and payload["text"]:
            text_fragments.append(payload["text"])

        # Assembled recovered text
        recovered_text = "\n".join(text_fragments) if text_fragments else None

        # 4. Determine Recovered Usability State & Diagnostic Evidence
        diagnostic_ids: List[str] = [f"diag_ocr_recovered_{doc_id}"]
        metadata: Dict[str, str] = {
            "recovery_method": "ocr_vision",
            "adapter": "MockVisionAdapter",
            "source_document": doc_id,
            "confidence": confidence,
            "page_count": "1",
        }

        if valid_ocr_boxes:
            metadata["ocr_boxes"] = json.dumps(valid_ocr_boxes)

        # Handle T06-02 partial degradation & legibility gates
        if unreadable_fields:
            metadata["unreadable_fields"] = json.dumps(unreadable_fields)
            for uf in unreadable_fields:
                diagnostic_ids.append(f"diag_unreadable_{uf}")

        if conflicting_fields:
            metadata["conflicting_fields"] = json.dumps(conflicting_fields)
            for cf in conflicting_fields:
                diagnostic_ids.append(f"diag_conflict_{cf}")

        if not footer_legible:
            metadata["footer_terms_legible"] = "false"
            metadata["partial_degradation"] = "footer_terms_illegible"

        # Evaluate final status under contract rules
        if not recovered_text or not recovered_text.strip():
            # If no usable text recovered at all
            return ParserResult(
                document_id=doc_id,
                status=ParserStatus.UNREADABLE,
                text=None,
                usable_for_extraction=False,
                diagnostic_evidence_ids=diagnostic_ids,
                attempt_ids=attempts,
                error_message="empty_ocr_text_recovery",
                is_scanned=True,
                metadata=metadata,
            )

        # If footer is blurry but essential comparison fields are sharp (AI-OCR-002)
        # or if mandatory fields are stained/conflicting but partial text was recovered
        if not footer_legible or unreadable_fields or conflicting_fields:
            return ParserResult(
                document_id=doc_id,
                status=ParserStatus.PARTIAL,
                text=recovered_text,
                clean_text=recovered_text,
                raw_text=recovered_text,
                usable_for_extraction=True,
                page_count=1,
                diagnostic_evidence_ids=diagnostic_ids,
                attempt_ids=attempts,
                is_scanned=True,
                metadata=metadata,
            )

        # Clean successful recovery (AI-OCR-001)
        return ParserResult(
            document_id=doc_id,
            status=ParserStatus.SUCCESS,
            text=recovered_text,
            clean_text=recovered_text,
            raw_text=recovered_text,
            usable_for_extraction=True,
            page_count=1,
            diagnostic_evidence_ids=diagnostic_ids,
            attempt_ids=attempts,
            is_scanned=True,
            metadata=metadata,
        )


def recover_document_if_needed(
    parser_result: ParserResult,
    file_path: Path,
    adapter: Optional[BaseVisionAdapter] = None,
) -> ParserResult:
    """Assess if document needs OCR/Vision recovery and invoke adapter if needed.
    
    Architectural invariant:
    - If ordinary parse is already usable and not scanned (e.g. vector PDF) -> BYPASS OCR.
    - If ordinary parse is scanned (is_scanned = True) or unusable -> INVOKE OCR recovery.
    """
    # 1. Routing bypass: usable vector PDF / document bypasses OCR
    if parser_result.usable_for_extraction and not parser_result.is_scanned:
        return parser_result

    # 2. Check eligibility for OCR recovery (is_scanned or unreadable)
    if not parser_result.is_scanned and parser_result.status != ParserStatus.UNREADABLE:
        return parser_result

    # 3. Invoke targeted OCR / Vision recovery
    active_adapter = adapter or MockVisionAdapter()
    return active_adapter.recover_document(
        file_path=file_path,
        document_id=str(parser_result.document_id),
    )


__all__ = [
    "BaseVisionAdapter",
    "MockVisionAdapter",
    "recover_document_if_needed",
    "validate_bounding_box",
    "normalize_pixel_box",
]
