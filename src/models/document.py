from __future__ import annotations

from enum import Enum
from typing import Literal, Self
from pydantic import Field, model_validator
from src.models.base import Contract, Text, require


class DocumentRole(str, Enum):
    """Document role in shipping comparison."""

    SI = "SI"
    BL = "BL"
    UNKNOWN = "UNKNOWN"


Role = Literal["SI", "BL"]
DocumentRoleType = Literal["SI", "BL", "UNKNOWN"]


class ParserStatus(str, Enum):
    """Execution status of document parser."""

    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    UNREADABLE = "UNREADABLE"
    UNSUPPORTED = "UNSUPPORTED"


ParserStatusType = Literal["SUCCESS", "PARTIAL", "UNREADABLE", "UNSUPPORTED"]


class DocumentReference(Contract):
    """Document identity, observed role, and identification evidence linkage."""

    document_id: Text
    role: DocumentRole | DocumentRoleType
    identification_evidence_ids: list[Text]


class ParserResult(Contract):
    """Structured result returned by document parsers and OCR recovery."""

    document_id: Text
    status: ParserStatus | ParserStatusType
    text: str | None
    usable_for_extraction: bool
    diagnostic_evidence_ids: list[Text]
    attempt_ids: list[Text]

    # Usability and diagnostic metadata (T02-02)
    raw_text: str | None = None
    clean_text: str | None = None
    page_count: int | None = None
    table_count: int | None = None
    is_scanned: bool = False
    error_message: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def content_state(self) -> Self:
        if self.status in ("SUCCESS", "PARTIAL"):
            require(self.text is not None and bool(self.text.strip()), "empty extraction is not success/partial")
        if self.status in ("UNREADABLE", "UNSUPPORTED"):
            require(not self.usable_for_extraction and bool(self.diagnostic_evidence_ids), "failed parsing needs diagnostic context")
        return self
