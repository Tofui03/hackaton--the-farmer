from __future__ import annotations

from pathlib import Path
from typing import Optional
from src.models.document import ParserResult, ParserStatus
from src.parsers.base import BaseParser
from src.parsers.usability_validator import assess_text_usability


class TextParser(BaseParser):
    """Parser for plain text attachments (.txt) reading BOM-safe UTF-8."""

    def parse(self, file_path: Path, document_id: Optional[str] = None) -> ParserResult:
        doc_id = document_id or file_path.name
        if not file_path.exists():
            return ParserResult(
                document_id=doc_id,
                status=ParserStatus.UNREADABLE,
                text=None,
                usable_for_extraction=False,
                diagnostic_evidence_ids=[f"missing_file_{doc_id}"],
                attempt_ids=[f"att_{doc_id}_txt"],
                error_message=f"File not found: {file_path}",
                metadata={"file_path": str(file_path)},
            )

        raw_bytes = file_path.read_bytes()

        # Canonical BOM-safe UTF-8 reader per T05-01 / Wave 0 migration disposition.
        # Automatic Latin-1 / CP1252 fallback is strictly removed to prevent silent reinterpretation
        # of arbitrary or corrupted binary data.
        try:
            raw_text = raw_bytes.decode("utf-8-sig")
            encoding_status = "utf-8"
        except UnicodeDecodeError as e:
            # Decode with replacement characters to truthfully represent malformed non-UTF-8 bytes
            raw_text = raw_bytes.decode("utf-8-sig", errors="replace")
            encoding_status = f"utf-8-decode-error: {e}"

        # Evaluate text usability via qualitative usability validator (T05-02)
        assessment = assess_text_usability(raw_text, is_pdf=False)

        diag_ids = [f"diag_{doc_id}_{r}" for r in assessment.reasons] if assessment.reasons else (
            [f"diag_{doc_id}_unreadable"] if assessment.status == ParserStatus.UNREADABLE else []
        )

        return ParserResult(
            document_id=doc_id,
            status=assessment.status,
            text=assessment.clean_text if assessment.is_usable else None,
            usable_for_extraction=assessment.is_usable,
            diagnostic_evidence_ids=diag_ids,
            attempt_ids=[f"att_{doc_id}_txt"],
            raw_text=raw_text,
            clean_text=assessment.clean_text,
            is_scanned=False,
            error_message=None if assessment.is_usable else "; ".join(assessment.reasons),
            metadata={
                "file_size": str(len(raw_bytes)),
                "encoding": encoding_status,
                "garbage_count": str(assessment.garbage_count),
                "garbage_ratio": f"{assessment.garbage_ratio:.4f}",
            },
        )
