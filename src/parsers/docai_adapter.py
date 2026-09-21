import logging
from pathlib import Path
from src.config import (
    DOCAI_LOCATION,
    DOCAI_PROCESSOR_ID,
    DOCAI_PROJECT_ID,
    is_docai_available,
)
from src.models.document import ParserResult, ParserStatus
from src.parsers.base import BaseParser, DocumentParseResult
from src.parsers.vision_adapter import BaseVisionAdapter

logger = logging.getLogger(__name__)


class DocumentAIAdapter(BaseParser, BaseVisionAdapter):
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

    def recover_document(
        self,
        file_path: Path,
        document_id: str | None = None,
    ) -> ParserResult:
        """Recover document text using Google Cloud Document AI returning strict ParserResult."""
        doc_id = document_id or file_path.name
        if not self.is_configured or not self.client:
            return ParserResult(
                document_id=doc_id,
                status=ParserStatus.UNREADABLE,
                text=None,
                usable_for_extraction=False,
                diagnostic_evidence_ids=[f"docai_not_configured_{doc_id}"],
                attempt_ids=[f"att_docai_{doc_id}_1"],
                error_message="Google Cloud Document AI is not configured or available.",
                is_scanned=True,
                metadata={"recovery_method": "docai", "adapter": "DocumentAIAdapter"},
            )

        legacy_res = self.parse(file_path)
        if legacy_res.success and legacy_res.text and legacy_res.text.strip():
            return ParserResult(
                document_id=doc_id,
                status=ParserStatus.SUCCESS,
                text=legacy_res.text,
                clean_text=legacy_res.text,
                raw_text=legacy_res.text,
                usable_for_extraction=True,
                page_count=int(legacy_res.metadata.get("pages", 1)),
                diagnostic_evidence_ids=[f"docai_success_{doc_id}"],
                attempt_ids=[f"att_docai_{doc_id}_1"],
                is_scanned=True,
                metadata={
                    "recovery_method": "docai",
                    "adapter": "DocumentAIAdapter",
                    "entities": str(legacy_res.metadata.get("entities", 0)),
                    "pages": str(legacy_res.metadata.get("pages", 1)),
                },
            )
        else:
            return ParserResult(
                document_id=doc_id,
                status=ParserStatus.UNREADABLE,
                text=None,
                usable_for_extraction=False,
                diagnostic_evidence_ids=[f"docai_failure_{doc_id}"],
                attempt_ids=[f"att_docai_{doc_id}_1"],
                error_message=legacy_res.error_message or "DocAI processing failure",
                is_scanned=True,
                metadata={"recovery_method": "docai", "adapter": "DocumentAIAdapter"},
            )

