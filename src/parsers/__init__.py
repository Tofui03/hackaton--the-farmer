from __future__ import annotations

from pathlib import Path
from typing import Optional
from src.models.document import ParserResult, ParserStatus
from src.parsers.base import BaseParser, DocumentParseResult
from src.parsers.docai_adapter import DocumentAIAdapter
from src.parsers.docx_parser import DocxParser
from src.parsers.excel_parser import ExcelParser
from src.parsers.pdf_parser import PdfParser
from src.parsers.text_parser import TextParser
from src.parsers.usability_validator import UsabilityAssessment, assess_text_usability
from src.parsers.vision_adapter import (
    BaseVisionAdapter,
    MockVisionAdapter,
    normalize_pixel_box,
    recover_document_if_needed,
    validate_bounding_box,
)

_text_parser = TextParser()
_docx_parser = DocxParser()
_excel_parser = ExcelParser()
_pdf_parser = PdfParser()
_docai_adapter = DocumentAIAdapter()


def parse_document(file_path: Path, document_id: Optional[str] = None) -> ParserResult:
    """Canonical router: Route document to appropriate parser returning strict ParserResult."""
    doc_id = document_id or file_path.name
    if not file_path.exists():
        return ParserResult(
            document_id=doc_id,
            status=ParserStatus.UNREADABLE,
            text=None,
            usable_for_extraction=False,
            diagnostic_evidence_ids=[f"missing_file_{doc_id}"],
            attempt_ids=[f"att_{doc_id}_router"],
            error_message=f"File not found: {file_path}",
            metadata={"file_path": str(file_path)},
        )

    ext = file_path.suffix.lower()

    if ext == ".txt":
        return _text_parser.parse(file_path, document_id=doc_id)
    elif ext == ".docx":
        return _docx_parser.parse(file_path, document_id=doc_id)
    elif ext == ".xlsx":
        return _excel_parser.parse(file_path, document_id=doc_id)
    elif ext == ".pdf":
        return _pdf_parser.parse(file_path, document_id=doc_id)
    else:
        return ParserResult(
            document_id=doc_id,
            status=ParserStatus.UNSUPPORTED,
            text=None,
            usable_for_extraction=False,
            diagnostic_evidence_ids=[f"unsupported_ext_{ext}"],
            attempt_ids=[f"att_{doc_id}_router"],
            error_message=f"Unsupported attachment extension: {ext}",
            metadata={"file_extension": ext},
        )


def parse_attachment(file_path: Path) -> DocumentParseResult:
    """Legacy backward-compatibility wrapper returning DocumentParseResult."""
    parser_res = parse_document(file_path)
    res = DocumentParseResult.from_parser_result(parser_res)

    # Scanned PDF fallback if DocAI is configured
    if res.is_scanned and _docai_adapter.is_configured:
        recovered = _docai_adapter.recover_document(file_path)
        if recovered.usable_for_extraction and recovered.text:
            return DocumentParseResult.from_parser_result(recovered)

    return res


__all__ = [
    "BaseParser",
    "DocumentParseResult",
    "TextParser",
    "DocxParser",
    "ExcelParser",
    "PdfParser",
    "DocumentAIAdapter",
    "BaseVisionAdapter",
    "MockVisionAdapter",
    "recover_document_if_needed",
    "validate_bounding_box",
    "normalize_pixel_box",
    "parse_document",
    "parse_attachment",
    "UsabilityAssessment",
    "assess_text_usability",
]
