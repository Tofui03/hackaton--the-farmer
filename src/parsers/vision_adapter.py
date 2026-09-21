from __future__ import annotations

from abc import ABC, abstractmethod
import json
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.models.document import ParserResult, ParserStatus

logger = logging.getLogger(__name__)


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
    
    Operates strictly on injected payload data or response providers.
    Does NOT access or depend on test-directory filesystem paths.
    """

    def __init__(
        self,
        payload: Optional[Dict[str, Any]] = None,
        payloads_by_document_id: Optional[Dict[str, Dict[str, Any]]] = None,
        response_provider: Optional[Callable[[Path, str], Optional[Dict[str, Any]]]] = None,
        simulated_faults: Optional[List[str]] = None,
        technical_attempt_limit: int = 3,
    ):
        self.payload = payload
        self.payloads_by_document_id = dict(payloads_by_document_id or {})
        self.response_provider = response_provider
        self.simulated_faults = list(simulated_faults) if simulated_faults else []
        self.technical_attempt_limit = technical_attempt_limit
        self.call_count = 0
        self.recorded_attempts: List[str] = []

    def _resolve_payload(self, file_path: Path, doc_id: str) -> Optional[Dict[str, Any]]:
        """Resolve payload from injected provider, mapping, or single payload."""
        if self.response_provider is not None:
            try:
                return self.response_provider(file_path, doc_id)
            except Exception as e:
                logger.warning("Response provider raised error: %s", e)
                return None

        if doc_id in self.payloads_by_document_id:
            return self.payloads_by_document_id[doc_id]

        if file_path.name in self.payloads_by_document_id:
            return self.payloads_by_document_id[file_path.name]

        return self.payload

    def recover_document(
        self,
        file_path: Path,
        document_id: Optional[str] = None,
    ) -> ParserResult:
        doc_id = document_id or file_path.name
        self.call_count += 1
        attempts: List[str] = []

        # 1. Bounded Technical Retry Simulation (DEC-AI-P01, AI-OCR-005, AI-OCR-006)
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

        # Current attempt
        att_id = f"att_ocr_{doc_id}_{attempt_num}"
        attempts.append(att_id)
        self.recorded_attempts.append(att_id)

        # 2. Retrieve payload strictly from injected sources
        payload = self._resolve_payload(file_path, doc_id)
        if payload is None:
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

        if "text" in payload and payload["text"]:
            text_fragments.append(payload["text"])

        recovered_text = "\n".join(text_fragments) if text_fragments else None

        # 4. Diagnostic Evidence and Usability Metadata
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

        # If footer is blurry but essential fields are sharp (AI-OCR-002),
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
    
    Architectural invariants:
    - If ordinary parse is already usable and not scanned (e.g. vector PDF) -> BYPASS OCR.
    - If ordinary parse is scanned (is_scanned = True) or unusable:
        - If adapter is provided: INVOKE adapter.recover_document().
        - If adapter is None: DO NOT invoke MockVisionAdapter or invent data;
          return unreadable ParserResult indicating no vision adapter is configured.
    """
    # 1. Routing bypass: usable vector PDF / document bypasses OCR
    if parser_result.usable_for_extraction and not parser_result.is_scanned:
        return parser_result

    # 2. Check eligibility for OCR recovery (is_scanned or unreadable)
    if not parser_result.is_scanned and parser_result.status != ParserStatus.UNREADABLE:
        return parser_result

    # 3. Guard against unconfigured recovery adapter (Mock must never be production default)
    if adapter is None:
        doc_id = str(parser_result.document_id)
        diag_ids = list(parser_result.diagnostic_evidence_ids)
        diag_unconf = f"no_vision_adapter_configured_{doc_id}"
        if diag_unconf not in diag_ids:
            diag_ids.append(diag_unconf)
        return ParserResult(
            document_id=doc_id,
            status=ParserStatus.UNREADABLE,
            text=None,
            usable_for_extraction=False,
            diagnostic_evidence_ids=diag_ids,
            attempt_ids=list(parser_result.attempt_ids) or [f"att_ocr_{doc_id}_none"],
            error_message="no_vision_adapter_configured",
            is_scanned=parser_result.is_scanned,
            metadata={
                **parser_result.metadata,
                "recovery_attempted": "false",
                "recovery_error": "no_vision_adapter_configured",
            },
        )

    # 4. Invoke configured OCR / Vision recovery
    return adapter.recover_document(
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
