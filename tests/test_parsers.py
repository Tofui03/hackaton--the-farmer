from __future__ import annotations

import json
from pathlib import Path
import tempfile
import pytest
from src.models.document import ParserResult, ParserStatus
from src.parsers import (
    DocxParser,
    ExcelParser,
    PdfParser,
    TextParser,
    parse_attachment,
    parse_document,
)
from src.parsers.base import DocumentParseResult

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "documents"


def test_text_parser():
    """PAR-TXT-001: Plain text parser reads BOM-safe UTF-8, returns canonical ParserResult."""
    p = FIXTURES_DIR / "txt" / "txt_si_001_clean.txt"
    assert p.exists(), f"Fixture missing: {p}"

    # 1. Canonical BaseParser.parse() returning ParserResult
    res = TextParser().parse(p)
    assert isinstance(res, ParserResult)
    assert res.status == ParserStatus.SUCCESS
    assert res.usable_for_extraction is True
    assert res.is_scanned is False
    assert res.text is not None
    assert "SHIPPING INSTRUCTION" in res.text
    assert "PACIFIC SYNTHETIC LOGISTICS" in res.text
    assert res.metadata.get("encoding") == "utf-8"

    # 2. Legacy parse_attachment() wrapper returning DocumentParseResult
    legacy_res = parse_attachment(p)
    assert isinstance(legacy_res, DocumentParseResult)
    assert legacy_res.success is True
    assert legacy_res.is_corrupted is False
    assert "SHIPPING INSTRUCTION" in legacy_res.text


def test_text_parser_encoding_policy():
    """Verifies BOM-safe UTF-8 decoding and rejection of silent Latin-1/CP1252 reinterpretation."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # UTF-8 with BOM
        bom_file = Path(tmp_dir) / "bom.txt"
        bom_file.write_bytes("SHIPPING INSTRUCTION UTF-8 BOM".encode("utf-8-sig"))
        assert bom_file.read_bytes().startswith(b"\xef\xbb\xbf")
        res_bom = TextParser().parse(bom_file)
        assert res_bom.status == ParserStatus.SUCCESS
        assert "SHIPPING INSTRUCTION" in res_bom.text
        assert "\ufeff" not in res_bom.text  # Stripped by utf-8-sig

        # Corrupted non-UTF-8 binary bytes: must NOT silently succeed as Latin-1
        bad_file = Path(tmp_dir) / "corrupt.txt"
        bad_file.write_bytes(b"\xff\xfe\x80\x81\x82\x83\x84\x85 INVALID BINARY BYTES")
        res_bad = TextParser().parse(bad_file)
        assert res_bad.status == ParserStatus.UNREADABLE
        assert res_bad.usable_for_extraction is False
        assert "binary_decode_replacement_corruption" in res_bad.error_message


def test_excel_parser():
    """PAR-XLSX-001: Excel sheet parser separates verbatim cell content from cell_coordinates metadata."""
    p = FIXTURES_DIR / "xlsx" / "xlsx_si_001_clean.xlsx"
    assert p.exists(), f"Fixture missing: {p}"

    res = ExcelParser().parse(p)
    assert isinstance(res, ParserResult)
    assert res.status == ParserStatus.SUCCESS
    assert res.usable_for_extraction is True
    assert res.text is not None
    assert "--- Sheet:" not in res.text
    assert "PACIFIC SYNTHETIC LOGISTICS" in res.text
    assert "Shipment_Header" in res.metadata["sheets"]

    # Verify generated labels (e.g. [Sheet ... Row ...]) do NOT contaminate text
    assert "[Sheet " not in res.text
    assert "[R1C1]" not in res.text

    # Verify exact cell-level openpyxl coordinates preserved in metadata
    assert "cell_coordinates" in res.metadata
    coords = json.loads(res.metadata["cell_coordinates"])
    assert len(coords) > 0
    first_cell = coords[0]
    assert "sheet" in first_cell
    assert "coordinate" in first_cell  # e.g. 'A1'
    assert "row" in first_cell
    assert "column" in first_cell
    assert "value" in first_cell

    legacy_res = parse_attachment(p)
    assert isinstance(legacy_res, DocumentParseResult)
    assert legacy_res.success is True
    assert legacy_res.is_corrupted is False
    assert len(legacy_res.text) > 50


def test_docx_parser():
    """PAR-DOCX-001: Word document parser separates verbatim text from table/cell coordinate metadata."""
    p = FIXTURES_DIR / "docx" / "docx_bl_001_table.docx"
    assert p.exists(), f"Fixture missing: {p}"

    res = DocxParser().parse(p)
    assert isinstance(res, ParserResult)
    assert res.status == ParserStatus.SUCCESS
    assert res.usable_for_extraction is True
    assert res.table_count is not None and res.table_count >= 1
    assert "PACIFIC SYNTHETIC LOGISTICS" in res.text

    # Verify generated labels (e.g. [Table 0 Row 0]) do NOT contaminate verbatim source text
    assert "[Table " not in res.text
    assert "[R0C0]" not in res.text

    # Verify exact table/row/column coordinates preserved in metadata
    assert "cell_coordinates" in res.metadata
    coords = json.loads(res.metadata["cell_coordinates"])
    assert len(coords) > 0
    first_cell = coords[0]
    assert "table" in first_cell
    assert "row" in first_cell
    assert "column" in first_cell
    assert "text" in first_cell

    legacy_res = parse_attachment(p)
    assert isinstance(legacy_res, DocumentParseResult)
    assert legacy_res.success is True
    assert legacy_res.is_corrupted is False
    assert len(legacy_res.text) > 50


def test_pdf_parser_valid():
    """PAR-PDF-001: Standard vector PDF parser records page count and extracts text."""
    p = FIXTURES_DIR / "pdf" / "pdf_si_001_clean.pdf"
    assert p.exists(), f"Fixture missing: {p}"

    res = PdfParser().parse(p)
    assert isinstance(res, ParserResult)
    assert res.status == ParserStatus.SUCCESS
    assert res.usable_for_extraction is True
    assert res.page_count is not None and res.page_count >= 1
    assert len(res.text) > 100

    legacy_res = parse_attachment(p)
    assert isinstance(legacy_res, DocumentParseResult)
    assert legacy_res.success is True
    assert legacy_res.is_corrupted is False
    assert len(legacy_res.text) > 100


def test_pdf_parser_corrupted():
    """PAR-PDF-002: Corrupted PDF stream is intercepted cleanly as UNREADABLE without crashing."""
    p = FIXTURES_DIR / "malformed" / "corrupt_stream.pdf"
    assert p.exists(), f"Fixture missing: {p}"

    res = PdfParser().parse(p)
    assert isinstance(res, ParserResult)
    assert res.status == ParserStatus.UNREADABLE
    assert res.usable_for_extraction is False
    assert res.is_scanned is False
    assert bool(res.diagnostic_evidence_ids)
    assert res.error_message is not None

    legacy_res = parse_attachment(p)
    assert isinstance(legacy_res, DocumentParseResult)
    assert legacy_res.success is False
    assert legacy_res.is_corrupted is True


def test_parse_document_router():
    """Verifies canonical parse_document routing across all formats and unsupported extensions."""
    txt_res = parse_document(FIXTURES_DIR / "txt" / "txt_si_001_clean.txt")
    assert txt_res.status == ParserStatus.SUCCESS

    docx_res = parse_document(FIXTURES_DIR / "docx" / "docx_bl_001_table.docx")
    assert docx_res.status == ParserStatus.SUCCESS

    xlsx_res = parse_document(FIXTURES_DIR / "xlsx" / "xlsx_si_001_clean.xlsx")
    assert xlsx_res.status == ParserStatus.SUCCESS

    pdf_res = parse_document(FIXTURES_DIR / "pdf" / "pdf_si_001_clean.pdf")
    assert pdf_res.status == ParserStatus.SUCCESS

    unsupported_res = parse_document(Path("dummy.unknown_ext"))
    assert unsupported_res.status == ParserStatus.UNREADABLE  # File does not exist

    # Create dummy temp check for unsupported extension routing
    with tempfile.NamedTemporaryFile(suffix=".xyz") as tmp:
        unsupp_existing = parse_document(Path(tmp.name))
        assert unsupp_existing.status == ParserStatus.UNSUPPORTED
        assert unsupp_existing.usable_for_extraction is False


def test_source_grounding_provenance_and_delimiter_isolation():
    """Verifies that generated delimiters (pipe ' | ') and sheet headers are NOT treated as source evidence.

    Actual cell-level source grounding must use the clean cell values and exact coordinates
    stored in metadata['cell_coordinates'], isolated from parser-generated serialization syntax.
    """
    # 1. DOCX: Verify cell text isolation from pipe delimiter
    docx_res = DocxParser().parse(FIXTURES_DIR / "docx" / "docx_bl_001_table.docx")
    assert docx_res.status == ParserStatus.SUCCESS
    coords_docx = json.loads(docx_res.metadata["cell_coordinates"])
    for cell in coords_docx:
        # Each cell has clean text without artificial pipe delimiter
        assert " | " not in cell["text"]
        assert "table" in cell
        assert "row" in cell
        assert "column" in cell

    # 2. XLSX: Verify cell value isolation from sheet headers
    xlsx_res = ExcelParser().parse(FIXTURES_DIR / "xlsx" / "xlsx_si_001_clean.xlsx")
    assert xlsx_res.status == ParserStatus.SUCCESS
    coords_xlsx = json.loads(xlsx_res.metadata["cell_coordinates"])
    for cell in coords_xlsx:
        # Each cell has clean value without artificial sheet headers or row tags
        assert "--- Sheet:" not in cell["value"]
        assert "sheet" in cell
        assert "coordinate" in cell
        assert "row" in cell
        assert "column" in cell

