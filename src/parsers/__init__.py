from pathlib import Path
from src.parsers.base import BaseParser, DocumentParseResult
from src.parsers.docai_adapter import DocumentAIAdapter
from src.parsers.docx_parser import DocxParser
from src.parsers.excel_parser import ExcelParser
from src.parsers.pdf_parser import PdfParser
from src.parsers.text_parser import TextParser

_text_parser = TextParser()
_docx_parser = DocxParser()
_excel_parser = ExcelParser()
_pdf_parser = PdfParser()
_docai_adapter = DocumentAIAdapter()


def parse_attachment(file_path: Path) -> DocumentParseResult:
    """Route attachment to the appropriate parser based on file extension."""
    if not file_path.exists():
        return DocumentParseResult(
            success=False,
            error_message=f"File not found: {file_path}",
        )

    ext = file_path.suffix.lower()

    if ext == ".txt":
        return _text_parser.parse(file_path)
    elif ext == ".docx":
        return _docx_parser.parse(file_path)
    elif ext == ".xlsx":
        return _excel_parser.parse(file_path)
    elif ext == ".pdf":
        result = _pdf_parser.parse(file_path)
        # If PDF opened but has no text (scanned image) and DocAI is configured, try DocAI
        if result.success and result.is_scanned and _docai_adapter.is_configured:
            docai_res = _docai_adapter.parse(file_path)
            if docai_res.success and len(docai_res.text) > 20:
                return docai_res
        return result
    else:
        return DocumentParseResult(
            success=False,
            error_message=f"Unsupported attachment extension: {ext}",
        )


__all__ = [
    "BaseParser",
    "DocumentParseResult",
    "TextParser",
    "DocxParser",
    "ExcelParser",
    "PdfParser",
    "DocumentAIAdapter",
    "parse_attachment",
]
