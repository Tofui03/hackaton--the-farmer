from __future__ import annotations

import json
from pathlib import Path
from typing import Optional
import docx
from src.models.document import ParserResult, ParserStatus
from src.parsers.base import BaseParser
from src.parsers.usability_validator import assess_text_usability


class DocxParser(BaseParser):
    """Parser for Microsoft Word (.docx) attachments.

    Textual Representation:
    - `text`, `raw_text`, and `clean_text` represent a source-derived textual serialization
      flattening paragraphs and multi-column tables.
    - Delimiter ' | ' between table cells is parser-generated serialization syntax, NOT verbatim source text.
    - Table, row, and column cell coordinates are preserved in `metadata['cell_coordinates']` (FR-007, PAR-DOCX-001).
    - Downstream evidence grounding for table cells must validate against actual cell content and
      metadata coordinates (table, row, column), NOT against the synthetic delimiter ' | '.
    """

    def parse(self, file_path: Path, document_id: Optional[str] = None) -> ParserResult:
        doc_id = document_id or file_path.name
        if not file_path.exists():
            return ParserResult(
                document_id=doc_id,
                status=ParserStatus.UNREADABLE,
                text=None,
                usable_for_extraction=False,
                diagnostic_evidence_ids=[f"missing_file_{doc_id}"],
                attempt_ids=[f"att_{doc_id}_docx"],
                error_message=f"File not found: {file_path}",
                metadata={"file_path": str(file_path)},
            )

        try:
            doc = docx.Document(file_path)
            lines: list[str] = []
            cell_coordinates: list[dict[str, int | str]] = []

            # 1. Extract verbatim paragraphs
            for p in doc.paragraphs:
                text = p.text.strip()
                if text:
                    lines.append(text)

            # 2. Extract table structures:
            # - Source content: cell texts joined into row strings without artificial label prefixes
            # - Structural provenance: exact table, row, and column cell-level coordinates
            for t_idx, table in enumerate(doc.tables):
                for r_idx, row in enumerate(table.rows):
                    row_cells: list[str] = []
                    for c_idx, cell in enumerate(row.cells):
                        c_text = cell.text.strip()
                        row_cells.append(c_text)
                        if c_text:
                            cell_coordinates.append({
                                "table": t_idx,
                                "row": r_idx,
                                "column": c_idx,
                                "text": c_text,
                            })

                    row_content = " | ".join(row_cells)
                    if row_content.replace("|", "").strip():
                        lines.append(row_content)

            full_text = "\n".join(lines).strip()
            table_count = len(doc.tables)

            assessment = assess_text_usability(full_text, is_pdf=False)

            diag_ids = [f"diag_{doc_id}_{r}" for r in assessment.reasons] if assessment.reasons else (
                [f"diag_{doc_id}_unreadable"] if assessment.status == ParserStatus.UNREADABLE else []
            )

            return ParserResult(
                document_id=doc_id,
                status=assessment.status,
                text=assessment.clean_text if assessment.is_usable else None,
                usable_for_extraction=assessment.is_usable,
                diagnostic_evidence_ids=diag_ids,
                attempt_ids=[f"att_{doc_id}_docx"],
                raw_text=full_text,
                clean_text=assessment.clean_text,
                table_count=table_count,
                is_scanned=False,
                error_message=None if assessment.is_usable else "; ".join(assessment.reasons),
                metadata={
                    "paragraphs": str(len(doc.paragraphs)),
                    "tables": str(table_count),
                    "cell_coordinates": json.dumps(cell_coordinates),
                    "garbage_count": str(assessment.garbage_count),
                    "garbage_ratio": f"{assessment.garbage_ratio:.4f}",
                },
            )

        except Exception as e:
            return ParserResult(
                document_id=doc_id,
                status=ParserStatus.UNREADABLE,
                text=None,
                usable_for_extraction=False,
                diagnostic_evidence_ids=[f"diag_{doc_id}_corrupt_docx"],
                attempt_ids=[f"att_{doc_id}_docx"],
                is_scanned=False,
                error_message=f"Failed to parse DOCX: {type(e).__name__}: {e}",
                metadata={"error_type": type(e).__name__},
            )
