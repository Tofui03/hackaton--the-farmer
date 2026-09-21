from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional
from src.models.document import ParserResult, ParserStatus


class DocumentParseResult:
    """Standard container for parsed document text and state flags (legacy compatibility)."""

    def __init__(
        self,
        text: str = "",
        success: bool = True,
        is_corrupted: bool = False,
        is_scanned: bool = False,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        parser_result: Optional[ParserResult] = None,
    ):
        self.text = text
        self.success = success
        self.is_corrupted = is_corrupted
        self.is_scanned = is_scanned
        self.error_message = error_message
        self.metadata = metadata or {}
        self.parser_result = parser_result

    @classmethod
    def from_parser_result(cls, res: ParserResult) -> DocumentParseResult:
        is_corrupted = (res.status == ParserStatus.UNREADABLE and not res.is_scanned)
        success = (res.status in (ParserStatus.SUCCESS, ParserStatus.PARTIAL))
        return cls(
            text=res.text or "",
            success=success,
            is_corrupted=is_corrupted,
            is_scanned=res.is_scanned,
            error_message=res.error_message,
            metadata={
                **res.metadata,
                "document_id": str(res.document_id),
                "status": str(res.status),
                "usable_for_extraction": str(res.usable_for_extraction),
            },
            parser_result=res,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "success": self.success,
            "is_corrupted": self.is_corrupted,
            "is_scanned": self.is_scanned,
            "error_message": self.error_message,
            "metadata": self.metadata,
        }


class BaseParser(ABC):
    """Abstract base class for attachment file parsers."""

    @abstractmethod
    def parse(self, file_path: Path, document_id: Optional[str] = None) -> ParserResult:
        """Parse the given file path into a canonical ParserResult."""
        pass
