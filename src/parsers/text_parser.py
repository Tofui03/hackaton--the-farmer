from pathlib import Path
from src.parsers.base import BaseParser, DocumentParseResult


class TextParser(BaseParser):
    """Parser for plain text attachments (.txt)."""

    def parse(self, file_path: Path) -> DocumentParseResult:
        if not file_path.exists():
            return DocumentParseResult(
                success=False,
                error_message=f"File not found: {file_path}",
            )

        encodings = ["utf-8", "latin-1", "cp1252"]
        raw_bytes = file_path.read_bytes()
        text = ""

        for enc in encodings:
            try:
                text = raw_bytes.decode(enc)
                break
            except UnicodeDecodeError:
                continue

        if not text and len(raw_bytes) > 0:
            text = raw_bytes.decode("utf-8", errors="replace")

        return DocumentParseResult(
            text=text.strip(),
            success=True,
            metadata={"file_size": len(raw_bytes), "encoding": enc},
        )
