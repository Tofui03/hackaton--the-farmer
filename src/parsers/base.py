from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional


class DocumentParseResult:
    """Standard container for parsed document text and state flags."""

    def __init__(
        self,
        text: str = "",
        success: bool = True,
        is_corrupted: bool = False,
        is_scanned: bool = False,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.text = text
        self.success = success
        self.is_corrupted = is_corrupted
        self.is_scanned = is_scanned
        self.error_message = error_message
        self.metadata = metadata or {}

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
    def parse(self, file_path: Path) -> DocumentParseResult:
        """Parse the given file path into a DocumentParseResult."""
        pass
