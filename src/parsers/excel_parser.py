from pathlib import Path
import openpyxl
from src.parsers.base import BaseParser, DocumentParseResult


class ExcelParser(BaseParser):
    """Parser for Excel (.xlsx) attachments."""

    def parse(self, file_path: Path) -> DocumentParseResult:
        if not file_path.exists():
            return DocumentParseResult(
                success=False,
                error_message=f"File not found: {file_path}",
            )

        try:
            wb = openpyxl.load_workbook(file_path, data_only=True)
            lines = []

            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                lines.append(f"--- Sheet: {sheet_name} ---")
                for row in ws.iter_rows(values_only=True):
                    # Filter out empty rows
                    if any(cell is not None and str(cell).strip() for cell in row):
                        row_strs = [str(c).strip() if c is not None else "" for c in row]
                        lines.append(" | ".join(row_strs))

            full_text = "\n".join(lines).strip()
            return DocumentParseResult(
                text=full_text,
                success=True,
                metadata={"sheets": wb.sheetnames},
            )
        except Exception as e:
            return DocumentParseResult(
                success=False,
                is_corrupted=True,
                error_message=f"Failed to parse XLSX: {e}",
            )
