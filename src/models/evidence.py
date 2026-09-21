from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal, Self
from pydantic import Field, model_validator
from src.models.base import Contract, Text, require


class EvidenceKind(str, Enum):
    """Supported source-grounded evidence types."""

    TEXT_SPAN = "text_span"
    TABLE_CELL = "table_cell"
    PAGE_REGION = "page_region"
    DOCUMENT_METADATA = "document_metadata"
    PROCESSING_ERROR = "processing_error"
    HUMAN_REVIEW = "human_review"


EvidenceKindType = Literal[
    "text_span",
    "table_cell",
    "page_region",
    "document_metadata",
    "processing_error",
    "human_review",
]

EvidenceSourceType = Literal["email", "document", "processing", "human_review"]


class EvidenceLocation(Contract):
    """Structural coordinates within a source document."""

    section: str | None = None
    page: Annotated[int, Field(ge=1)] | None = None
    table: str | None = None
    row: Annotated[int, Field(ge=0)] | None = None
    column: Annotated[int, Field(ge=0)] | None = None
    bbox: Annotated[list[Annotated[float, Field(ge=0, le=1)]], Field(min_length=4, max_length=4)] | None = None

    @model_validator(mode="after")
    def coordinates(self) -> Self:
        if self.bbox is not None:
            require(self.page is not None, "region requires page")
            x0, y0, x1, y1 = self.bbox
            require(x0 < x1 and y0 < y1, "bbox must be an ordered non-empty region")
        return self


class FieldEvidence(Contract):
    """Source-grounded evidence citation for an extracted value, role, or error."""

    evidence_id: Text
    source_type: EvidenceSourceType
    source_id: Text
    kind: EvidenceKind | EvidenceKindType
    quote: Text | None = None
    location: EvidenceLocation | None = None
    detail: Text | None = None

    @model_validator(mode="after")
    def payload(self) -> Self:
        if self.kind in ("text_span", "table_cell"):
            require(self.quote is not None, "text/cell evidence requires source text")
        if self.kind == "table_cell":
            require(
                self.location is not None
                and self.location.table is not None
                and self.location.row is not None
                and self.location.column is not None,
                "cell requires table and coordinates",
            )
        if self.kind == "page_region":
            require(
                self.location is not None and self.location.bbox is not None,
                "region requires coordinates",
            )
        if self.kind in ("document_metadata", "processing_error", "human_review"):
            require(self.detail is not None, "context evidence requires detail")
        return self
