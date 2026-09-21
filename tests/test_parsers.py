from pathlib import Path
import pytest
from src.parsers import (
    DocxParser,
    ExcelParser,
    PdfParser,
    TextParser,
    parse_attachment,
)

BASE_DIR = Path(__file__).resolve().parent.parent / "sdoc-hackathon-bundle" / "attachments"


def test_text_parser():
    p = BASE_DIR / "email_001_SI.txt"
    if not p.exists():
        pytest.skip("Test file not found")
    res = TextParser().parse(p)
    assert res.success is True
    assert res.is_corrupted is False
    assert "SHIPPING INSTRUCTION" in res.text
    assert "APRIL FAR EAST" in res.text


def test_excel_parser():
    p = BASE_DIR / "email_005_SI.xlsx"
    if not p.exists():
        pytest.skip("Test file not found")
    res = ExcelParser().parse(p)
    assert res.success is True
    assert res.is_corrupted is False
    assert len(res.text) > 50


def test_docx_parser():
    docx_files = list(BASE_DIR.glob("*.docx"))
    if not docx_files:
        pytest.skip("No docx files found")
    res = DocxParser().parse(docx_files[0])
    assert res.success is True
    assert res.is_corrupted is False
    assert len(res.text) > 50


def test_pdf_parser_valid():
    p = BASE_DIR / "email_059_SI.pdf"
    if not p.exists():
        pytest.skip("Test file not found")
    res = PdfParser().parse(p)
    assert res.success is True
    assert res.is_corrupted is False
    assert len(res.text) > 100


def test_pdf_parser_corrupted():
    p = BASE_DIR / "email_511_BL.pdf"
    if not p.exists():
        pytest.skip("Test file not found")
    res = PdfParser().parse(p)
    assert res.success is False
    assert res.is_corrupted is True
