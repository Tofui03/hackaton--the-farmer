from __future__ import annotations

from pathlib import Path

from src.parsers.base import BaseParser
from src.parsers.registry import DEFAULT_PARSER_REGISTRY, DocumentParserRegistry


class DocumentParserFactory:
    """Factory creating/retrieving parsers for specific file paths."""

    def __init__(self, registry: DocumentParserRegistry | None = None) -> None:
        self.registry: DocumentParserRegistry = registry or DEFAULT_PARSER_REGISTRY

    def get_parser_for_path(self, file_path: Path) -> BaseParser | None:
        """Extract suffix from path and fetch corresponding parser from registry."""
        suffix = file_path.suffix
        return self.registry.get_parser(suffix)
