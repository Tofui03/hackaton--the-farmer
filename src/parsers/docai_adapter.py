from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from src.config import (
    DOCAI_LOCATION,
    DOCAI_PROCESSOR_ID,
    DOCAI_PROJECT_ID,
    is_docai_available,
)
from src.models.document import ParserResult, ParserStatus
from src.parsers.base import DocumentParseResult
from src.parsers.vision_adapter import BaseVisionAdapter

logger = logging.getLogger(__name__)


class DocumentAIAdapter(BaseVisionAdapter):
    """Pluggable Google Cloud Document AI client adapter for OCR recovery."""

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

    def recover_document(
        self,
        file_path: Path,
        document_id: Optional[str] = None,
    ) -> ParserResult:
        """Canonical recovery method returning strict ParserResult."""
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

        try:
            from google.cloud import documentai

            with open(file_path, "rb") as image:
                image_content = image.read()

            mime_type = "application/pdf" if file_path.suffix.lower() == ".pdf" else "image/png"
            raw_document = documentai.RawDocument(content=image_content, mime_type=mime_type)
            request = documentai.ProcessRequest(name=self.name, raw_document=raw_document)
            result = self.client.process_document(request=request)
            document = result.document

            recovered_text = document.text or ""
            if recovered_text.strip():
                return ParserResult(
                    document_id=doc_id,
                    status=ParserStatus.SUCCESS,
                    text=recovered_text,
                    clean_text=recovered_text,
                    raw_text=recovered_text,
                    usable_for_extraction=True,
                    page_count=len(document.pages),
                    diagnostic_evidence_ids=[f"docai_success_{doc_id}"],
                    attempt_ids=[f"att_docai_{doc_id}_1"],
                    is_scanned=True,
                    metadata={
                        "recovery_method": "docai",
                        "adapter": "DocumentAIAdapter",
                        "entities": str(len(document.entities)),
                        "pages": str(len(document.pages)),
                    },
                )
            else:
                return ParserResult(
                    document_id=doc_id,
                    status=ParserStatus.UNREADABLE,
                    text=None,
                    usable_for_extraction=False,
                    diagnostic_evidence_ids=[f"docai_empty_text_{doc_id}"],
                    attempt_ids=[f"att_docai_{doc_id}_1"],
                    error_message="DocAI returned empty text",
                    is_scanned=True,
                    metadata={"recovery_method": "docai", "adapter": "DocumentAIAdapter"},
                )
        except Exception as e:
            logger.error("DocAI extraction failed for %s: %s", file_path, e)
            return ParserResult(
                document_id=doc_id,
                status=ParserStatus.UNREADABLE,
                text=None,
                usable_for_extraction=False,
                diagnostic_evidence_ids=[f"docai_error_{doc_id}"],
                attempt_ids=[f"att_docai_{doc_id}_1"],
                error_message=f"DocAI processing error: {e}",
                is_scanned=True,
                metadata={"recovery_method": "docai", "adapter": "DocumentAIAdapter"},
            )

    def parse(self, file_path: Path, document_id: Optional[str] = None) -> ParserResult:
        """Parse alias delegating to recover_document, strictly returning ParserResult."""
        return self.recover_document(file_path, document_id=document_id)

    def parse_legacy(self, file_path: Path) -> DocumentParseResult:
        """Explicit legacy compatibility wrapper returning DocumentParseResult."""
        res = self.recover_document(file_path)
        return DocumentParseResult.from_parser_result(res)
