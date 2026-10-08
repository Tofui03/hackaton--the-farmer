from __future__ import annotations

from pathlib import Path
from typing import Optional
import pytest

from src.models.document import ParserResult, ParserStatus
from src.parsers import (
    DEFAULT_PARSER_REGISTRY,
    BaseParser,
    DocumentParserFactory,
    DocumentParserRegistry,
    DocxParser,
    ExcelParser,
    PdfParser,
    TextParser,
)


class DummyCustomParser(BaseParser):
    """Dummy parser for testing registry extensibility."""

    def parse(self, file_path: Path, document_id: Optional[str] = None) -> ParserResult:
        doc_id = document_id or file_path.name
        return ParserResult(
            document_id=doc_id,
            status=ParserStatus.SUCCESS,
            text="custom parser content",
            usable_for_extraction=True,
            diagnostic_evidence_ids=[],
            attempt_ids=[],
            metadata={"parser": "dummy"},
        )


class TestDocumentParserRegistry:
    """Unit tests for DocumentParserRegistry."""

    def test_default_registry_covers_four_extensions(self) -> None:
        supported = DEFAULT_PARSER_REGISTRY.supported_extensions()
        assert supported == {".txt", ".docx", ".xlsx", ".pdf"}

        assert isinstance(DEFAULT_PARSER_REGISTRY.get_parser(".txt"), TextParser)
        assert isinstance(DEFAULT_PARSER_REGISTRY.get_parser(".docx"), DocxParser)
        assert isinstance(DEFAULT_PARSER_REGISTRY.get_parser(".xlsx"), ExcelParser)
        assert isinstance(DEFAULT_PARSER_REGISTRY.get_parser(".pdf"), PdfParser)

    def test_case_insensitivity_and_leading_dot_tolerance(self) -> None:
        # Both uppercase and lowercase with/without dot should resolve correctly
        assert isinstance(DEFAULT_PARSER_REGISTRY.get_parser(".PDF"), PdfParser)
        assert isinstance(DEFAULT_PARSER_REGISTRY.get_parser("PDF"), PdfParser)
        assert isinstance(DEFAULT_PARSER_REGISTRY.get_parser(".TXT"), TextParser)
        assert isinstance(DEFAULT_PARSER_REGISTRY.get_parser("txt"), TextParser)
        assert isinstance(DEFAULT_PARSER_REGISTRY.get_parser(".DOCX"), DocxParser)
        assert isinstance(DEFAULT_PARSER_REGISTRY.get_parser("xlsx"), ExcelParser)

    def test_unknown_extensions_return_none(self) -> None:
        assert DEFAULT_PARSER_REGISTRY.get_parser(".unknown") is None
        assert DEFAULT_PARSER_REGISTRY.get_parser(".zip") is None
        assert DEFAULT_PARSER_REGISTRY.get_parser(".csv") is None
        assert DEFAULT_PARSER_REGISTRY.get_parser("") is None
        assert DEFAULT_PARSER_REGISTRY.get_parser("   ") is None

    def test_register_dynamic_custom_parser(self) -> None:
        registry = DocumentParserRegistry()
        custom = DummyCustomParser()

        # Register .csv with no leading dot and uppercase
        registry.register("CSV", custom)

        assert ".csv" in registry.supported_extensions()
        assert registry.get_parser(".csv") is custom
        assert registry.get_parser("csv") is custom
        assert registry.get_parser(".CSV") is custom

    def test_register_override_existing_parser(self) -> None:
        registry = DocumentParserRegistry()
        custom_txt = DummyCustomParser()
        registry.register(".txt", custom_txt)

        assert registry.get_parser(".txt") is custom_txt


class TestDocumentParserFactory:
    """Unit tests for DocumentParserFactory."""

    def test_factory_resolves_parser_by_path(self) -> None:
        factory = DocumentParserFactory()

        assert isinstance(factory.get_parser_for_path(Path("/tmp/sample.txt")), TextParser)
        assert isinstance(factory.get_parser_for_path(Path("docs/spec.docx")), DocxParser)
        assert isinstance(factory.get_parser_for_path(Path("data/table.xlsx")), ExcelParser)
        assert isinstance(factory.get_parser_for_path(Path("shipping/bill.pdf")), PdfParser)
        assert isinstance(factory.get_parser_for_path(Path("shipping/bill.PDF")), PdfParser)

    def test_factory_returns_none_for_unsupported_path(self) -> None:
        factory = DocumentParserFactory()
        assert factory.get_parser_for_path(Path("archive.zip")) is None
        assert factory.get_parser_for_path(Path("file_without_extension")) is None

    def test_factory_dependency_injection(self) -> None:
        custom_registry = DocumentParserRegistry()
        custom = DummyCustomParser()
        custom_registry.register(".xyz", custom)

        factory = DocumentParserFactory(registry=custom_registry)
        assert factory.get_parser_for_path(Path("test.xyz")) is custom
        assert factory.get_parser_for_path(Path("test.txt")) is not None
