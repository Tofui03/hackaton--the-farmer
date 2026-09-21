import logging
from pathlib import Path
from src.config import (
    DOCAI_LOCATION,
    DOCAI_PROCESSOR_ID,
    DOCAI_PROJECT_ID,
    is_docai_available,
)
from src.parsers.base import BaseParser, DocumentParseResult

logger = logging.getLogger(__name__)


class DocumentAIAdapter(BaseParser):
    """Pluggable Google Cloud Document AI client adapter."""

    def __init__(self):
        self.is_configured = is_docai_available()
        self.client = None
        if self.is_configured:
            try:
                from google.cloud import documentai

                self.client = documentai.DocumentProcessorServiceClient()
                self.name = self.client.processor_path(
                    DOCAI_PROJECT_ID, DOCAI_LOCATION, DOCAI_PROCESSOR_ID
                )
            except Exception as e:
                logger.warning("Could not initialize Google Cloud Document AI: %s", e)
                self.is_configured = False

    def parse(self, file_path: Path) -> DocumentParseResult:
        if not self.is_configured or not self.client:
            return DocumentParseResult(
                success=False,
                error_message="Google Cloud Document AI is not configured or available.",
            )

        try:
            from google.cloud import documentai

            with open(file_path, "rb") as image:
                image_content = image.read()

            mime_type = "application/pdf" if file_path.suffix.lower() == ".pdf" else "image/png"
            raw_document = documentai.RawDocument(content=image_content, mime_type=mime_type)
            request = documentai.ProcessRequest(name=self.name, raw_document=raw_document)
            result = self.client.process_document(request=request)
            document = result.document

            return DocumentParseResult(
                text=document.text,
                success=True,
                metadata={"entities": len(document.entities), "pages": len(document.pages)},
            )
        except Exception as e:
            logger.error("DocAI extraction failed for %s: %s", file_path, e)
            return DocumentParseResult(
                success=False,
                error_message=f"DocAI processing error: {e}",
            )
