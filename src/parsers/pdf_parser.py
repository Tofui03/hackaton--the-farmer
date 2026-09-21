from __future__ import annotations

from pathlib import Path
from typing import Optional
from pypdf import PdfReader
from pypdf.errors import PdfReadError, PdfStreamError
from src.models.document import ParserResult, ParserStatus
from src.parsers.base import BaseParser
from src.parsers.usability_validator import assess_text_usability


class PdfParser(BaseParser):
    """Parser for PDF attachments (.pdf), detecting corruption and scanned pages."""

    def parse(self, file_path: Path, document_id: Optional[str] = None) -> ParserResult:
        doc_id = document_id or file_path.name
        if not file_path.exists():
            return ParserResult(
                document_id=doc_id,
                status=ParserStatus.UNREADABLE,
                text=None,
                usable_for_extraction=False,
                diagnostic_evidence_ids=[f"missing_file_{doc_id}"],
                attempt_ids=[f"att_{doc_id}_pdf"],
                error_message=f"File not found: {file_path}",
                metadata={"file_path": str(file_path)},
            )

        try:
            reader = PdfReader(str(file_path))
            pages_text = []

            for page in reader.pages:
                text = page.extract_text() or ""
                pages_text.append(text.strip())

            full_text = "\n".join(pages_text).strip()
            page_count = len(reader.pages)

            # Evaluate text usability via qualitative usability validator (T05-02, DEC-P02, REG-007)
            # Replaces arbitrary fixed-length heuristics (e.g. len < 20) with multi-signal evaluation
            assessment = assess_text_usability(full_text, is_pdf=True, page_count=page_count)

            if assessment.is_scanned:
                return ParserResult(
                    document_id=doc_id,
                    status=ParserStatus.UNREADABLE,
                    text=None,
                    usable_for_extraction=False,
                    diagnostic_evidence_ids=[f"diag_{doc_id}_scanned_pdf"],
                    attempt_ids=[f"att_{doc_id}_pdf"],
                    page_count=page_count,
                    is_scanned=True,
                    error_message="Scanned image-only PDF with no extractable text layer",
                    metadata={"num_pages": str(page_count), "is_scanned": "True"},
                )

            diag_ids = [f"diag_{doc_id}_{r}" for r in assessment.reasons] if assessment.reasons else (
                [f"diag_{doc_id}_unreadable"] if assessment.status == ParserStatus.UNREADABLE else []
            )

            return ParserResult(
                document_id=doc_id,
                status=assessment.status,
                text=assessment.clean_text if assessment.is_usable else None,
                usable_for_extraction=assessment.is_usable,
                diagnostic_evidence_ids=diag_ids,
                attempt_ids=[f"att_{doc_id}_pdf"],
                raw_text=full_text,
                clean_text=assessment.clean_text,
                page_count=page_count,
                is_scanned=False,
                error_message=None if assessment.is_usable else "; ".join(assessment.reasons),
                metadata={
                    "num_pages": str(page_count),
                    "garbage_count": str(assessment.garbage_count),
                    "garbage_ratio": f"{assessment.garbage_ratio:.4f}",
                },
            )

        except (PdfStreamError, PdfReadError, Exception) as e:
            # File is corrupted, incomplete stream, or unreadable PDF (NFR-003, PAR-PDF-002)
            return ParserResult(
                document_id=doc_id,
                status=ParserStatus.UNREADABLE,
                text=None,
                usable_for_extraction=False,
                diagnostic_evidence_ids=[f"diag_{doc_id}_corrupt_pdf"],
                attempt_ids=[f"att_{doc_id}_pdf"],
                is_scanned=False,
                error_message=f"Corrupt or unreadable PDF: {type(e).__name__}: {e}",
                metadata={"error_type": type(e).__name__},
            )
