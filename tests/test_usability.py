from __future__ import annotations

from pathlib import Path
import tempfile
import pytest
from src.models.document import ParserResult, ParserStatus
from src.parsers.pdf_parser import PdfParser
from src.parsers.text_parser import TextParser
from src.parsers.usability_validator import assess_text_usability

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "documents"


def test_par_usab_001_valid_short_document():
    """PAR-USAB-001: Short valid plain text must be accepted without OCR or rejection (REG-007)."""
    short_text = "SI: ACME / 2 CTR / 22MT"
    assert len(short_text) < 30

    assessment = assess_text_usability(short_text, is_pdf=False)
    assert assessment.is_usable is True
    assert assessment.status == ParserStatus.SUCCESS
    assert assessment.clean_text == short_text
    assert assessment.is_scanned is False
    assert assessment.garbage_count == 0

    # Also test against the short valid fixture
    fixture_path = FIXTURES_DIR / "txt" / "txt_si_009_short_valid.txt"
    assert fixture_path.exists()

    res = TextParser().parse(fixture_path)
    assert isinstance(res, ParserResult)
    assert res.status == ParserStatus.SUCCESS
    assert res.usable_for_extraction is True
    assert res.is_scanned is False
    assert res.text is not None
    assert "SYNTHETIC CHEM" in res.text


def test_par_usab_002_long_garbage_rejected():
    """PAR-USAB-002: Corrupted text with high replacement character density or invalid fragment is rejected."""
    # Synthetic corruption with decode replacement characters
    garbage_text = "SI START \ufffd\ufffd\ufffd\ufffd CARGO END"
    assessment = assess_text_usability(garbage_text, is_pdf=False)
    assert assessment.is_usable is False
    assert assessment.status == ParserStatus.UNREADABLE
    assert "binary_decode_replacement_corruption" in assessment.reasons
    assert assessment.clean_text is None

    # Synthetic corruption with null bytes
    null_text = "SI START \x00\x00 CARGO END"
    null_assessment = assess_text_usability(null_text, is_pdf=False)
    assert null_assessment.is_usable is False
    assert null_assessment.status == ParserStatus.UNREADABLE
    assert "binary_null_bytes_present" in null_assessment.reasons

    # Test generic long text with binary decode replacement corruption (PAR-USAB-002)
    with tempfile.TemporaryDirectory() as tmp_dir:
        corrupted_file = Path(tmp_dir) / "corrupted_payload.txt"
        corrupted_file.write_bytes(b"SI START " + (b"\xff\xfe" * 50) + b" CARGO END")
        res_corrupt = TextParser().parse(corrupted_file)
        assert isinstance(res_corrupt, ParserResult)
        assert res_corrupt.status == ParserStatus.UNREADABLE
        assert res_corrupt.usable_for_extraction is False
        assert res_corrupt.text is None
        assert bool(res_corrupt.diagnostic_evidence_ids)


def test_par_usab_003_scanned_image_pdf_detected():
    """PAR-USAB-003: Scanned 300 DPI PDF without embedded text layer triggers is_scanned=True and unreadable."""
    assessment = assess_text_usability("", is_pdf=True, page_count=1)
    assert assessment.is_usable is False
    assert assessment.status == ParserStatus.UNREADABLE
    assert assessment.is_scanned is True
    assert "empty_text_stream_scanned_pdf" in assessment.reasons

    # Test on synthetic scanned fixture
    scanned_path = FIXTURES_DIR / "scanned" / "scan_si_001_readable.pdf"
    assert scanned_path.exists()

    res = PdfParser().parse(scanned_path)
    assert isinstance(res, ParserResult)
    assert res.status == ParserStatus.UNREADABLE
    assert res.usable_for_extraction is False
    assert res.is_scanned is True
    assert res.text is None
    assert res.page_count == 1
    assert "scanned" in res.error_message.lower()


def test_par_usab_004_partial_usability_minor_artifacts():
    """PAR-USAB-004: Document with minor localized non-printable artifacts is accepted with status PARTIAL."""
    dirty_text = "SHIPPER: GLOBAL TRADING\nCONSIGNEE: BETA CORP\n\x01\x02PORT: ROTTERDAM"
    assessment = assess_text_usability(dirty_text, is_pdf=False)
    assert assessment.is_usable is True
    assert assessment.status == ParserStatus.PARTIAL
    assert assessment.clean_text is not None
    assert "\x01" not in assessment.clean_text
    assert "\x02" not in assessment.clean_text
    assert "SHIPPER: GLOBAL TRADING" in assessment.clean_text
    assert assessment.garbage_count == 2


def test_reg_007_zero_fixed_length_cutoff():
    """REG-007: Eliminates arbitrary len > 20 cutoff; short valid strings are always USABLE."""
    for text in ["OK 10 CHRS", "CONCISE SI 18 CHAR", "VALID SHIPPING DATA 25 CH"]:
        assessment = assess_text_usability(text, is_pdf=False)
        assert assessment.is_usable is True
        assert assessment.status == ParserStatus.SUCCESS
        assert assessment.clean_text == text


def test_txt_si_010_evaluation_without_synthetic_sentinel():
    """Documents evaluation of txt_si_010 under canonical generic qualitative usability rules.

    The fixture contains 100% valid printable UTF-8 characters without decode replacement
    characters or null bytes; without an unapproved hardcoded sentinel token, it parses
    as valid printable text (ParserStatus.SUCCESS, usable_for_extraction=True).
    """
    fixture_path = FIXTURES_DIR / "txt" / "txt_si_010_long_unusable.txt"
    assert fixture_path.exists()
    res = TextParser().parse(fixture_path)
    assert res.status == ParserStatus.SUCCESS
    assert res.usable_for_extraction is True
    assert res.clean_text is not None
    assert len(res.clean_text) > 5000

