from pathlib import Path
from pypdf import PdfReader
from pypdf.errors import PdfStreamError, PdfReadError
from src.parsers.base import BaseParser, DocumentParseResult


class PdfParser(BaseParser):
    """Parser for PDF attachments (.pdf), detecting corruption and scanned pages."""

    def parse(self, file_path: Path) -> DocumentParseResult:
        if not file_path.exists():
            return DocumentParseResult(
                success=False,
                error_message=f"File not found: {file_path}",
            )

        try:
            reader = PdfReader(str(file_path))
            pages_text = []

            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                pages_text.append(text.strip())

            full_text = "\n".join(pages_text).strip()

            # If the PDF opened, but text is empty, it's an image/scanned PDF
            is_scanned = len(full_text) < 20

            return DocumentParseResult(
                text=full_text,
                success=True,
                is_corrupted=False,
                is_scanned=is_scanned,
                metadata={"num_pages": len(reader.pages)},
            )
        except (PdfStreamError, PdfReadError, Exception) as e:
            # File is corrupted, incomplete stream, or unreadable PDF
            return DocumentParseResult(
                text="",
                success=False,
                is_corrupted=True,
                is_scanned=False,
                error_message=f"Corrupt or unreadable PDF: {type(e).__name__}: {e}",
            )
