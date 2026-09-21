from pathlib import Path
import docx
from src.parsers.base import BaseParser, DocumentParseResult


class DocxParser(BaseParser):
    """Parser for Microsoft Word (.docx) attachments."""

    def parse(self, file_path: Path) -> DocumentParseResult:
        if not file_path.exists():
            return DocumentParseResult(
                success=False,
                error_message=f"File not found: {file_path}",
            )

        try:
            doc = docx.Document(file_path)
            lines = []

            # 1. Extract paragraphs
            for p in doc.paragraphs:
                text = p.text.strip()
                if text:
                    lines.append(text)

            # 2. Extract tables
            for table in doc.tables:
                for row in table.rows:
                    row_cells = [cell.text.strip() for cell in row.cells]
                    # Filter out purely empty duplicate cells
                    row_str = " | ".join(row_cells)
                    if row_str.replace("|", "").strip():
                        lines.append(row_str)

            full_text = "\n".join(lines).strip()
            return DocumentParseResult(
                text=full_text,
                success=True,
                metadata={"paragraphs": len(doc.paragraphs), "tables": len(doc.tables)},
            )
        except Exception as e:
            return DocumentParseResult(
                success=False,
                is_corrupted=True,
                error_message=f"Failed to parse DOCX: {e}",
            )
