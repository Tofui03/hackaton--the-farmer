from __future__ import annotations

from typing import Final

from src.parsers.base import BaseParser
from src.parsers.docx_parser import DocxParser
from src.parsers.excel_parser import ExcelParser
from src.parsers.pdf_parser import PdfParser
from src.parsers.text_parser import TextParser


class DocumentParserRegistry:
    """Registry maintaining file extension to BaseParser instance mappings."""

    def __init__(self) -> None:
        self._parsers: dict[str, BaseParser] = {}
        self._initialize_defaults()

    @staticmethod
    def _normalize_ext(ext: str) -> str:
        clean = ext.strip().lower()
        if not clean.startswith("."):
            clean = f".{clean}"
        return clean

    def _initialize_defaults(self) -> None:
        self.register(".txt", TextParser())
        self.register(".docx", DocxParser())
        self.register(".xlsx", ExcelParser())
        self.register(".pdf", PdfParser())

    def register(self, ext: str, parser: BaseParser) -> None:
        """Register or override a parser for a given extension (Open-Closed Principle)."""
        normalized_ext = self._normalize_ext(ext)
        self._parsers[normalized_ext] = parser

    def get_parser(self, ext: str) -> BaseParser | None:
        """Retrieve parser for a given file extension, or None if unsupported."""
        if not ext or not ext.strip():
            return None
        normalized_ext = self._normalize_ext(ext)
        return self._parsers.get(normalized_ext)

    def supported_extensions(self) -> set[str]:
        """Return the set of all currently supported file extensions."""
        return set(self._parsers.keys())


DEFAULT_PARSER_REGISTRY: Final[DocumentParserRegistry] = DocumentParserRegistry()
