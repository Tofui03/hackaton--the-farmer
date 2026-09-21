from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import Field
from src.models.base import Contract


class EmailClassificationOutput(Contract):
    """Canonical structured output schema for email intent classification (Stage 1 / DEC-P01)."""

    category: Literal[
        "document_comparison",
        "new_shipping_instruction",
        "invoice_query",
        "general",
        "spam",
    ]
    reason: str = ""
    evidence: List[str] = Field(default_factory=list)
    evidence_quote: Optional[str] = None
    confidence: Optional[float] = None
    confidence_indicator: Literal["HIGH", "MEDIUM", "LOW"] = "HIGH"


# Backward-compatible alias matching test plan nomenclature (AI-ADP-001)
ClassificationResponse = EmailClassificationOutput


class DocumentRoleResolutionOutput(Contract):
    """Canonical structured output schema for document role binding (Stage 2 / DEC-P01)."""

    document_roles: Dict[str, Literal["SI", "BL", "UNKNOWN"]]
    rationale: str = ""
    confidence: Optional[float] = None
    confidence_indicator: Literal["HIGH", "MEDIUM", "LOW"] = "HIGH"


class ExtractedFieldRaw(Contract):
    """Raw candidate representation of an extracted field before normalization (Stage 3A)."""

    raw_value: Optional[Union[str, int, float, bool]] = None
    status: Literal["FOUND", "MISSING", "UNREADABLE", "UNCERTAIN", "CONFLICTING"] = "FOUND"
    evidence: Optional[str] = None
    ocr_box: Optional[Dict[str, Any]] = None
    candidates: Optional[List[Dict[str, Any]]] = None


class DocumentFieldExtractionOutput(Contract):
    """Canonical structured output schema for document field extraction (Stage 3A / DEC-P01)."""

    document_id: str
    role: Literal["SI", "BL", "UNKNOWN"]
    fields: Dict[str, ExtractedFieldRaw]
    confidence: Optional[float] = None
    confidence_indicator: Literal["HIGH", "MEDIUM", "LOW"] = "HIGH"


__all__ = [
    "EmailClassificationOutput",
    "ClassificationResponse",
    "DocumentRoleResolutionOutput",
    "ExtractedFieldRaw",
    "DocumentFieldExtractionOutput",
]
