from __future__ import annotations

from enum import Enum
from typing import Literal, Self
from pydantic import model_validator
from src.models.base import Contract, Text, require


class EmailCategory(str, Enum):
    """Canonical internal email category enumeration (5 approved categories)."""

    DOCUMENT_COMPARISON = "document_comparison"
    NEW_SHIPPING_INSTRUCTION = "new_shipping_instruction"
    INVOICE_QUERY = "invoice_query"
    GENERAL = "general"
    SPAM = "spam"


Category = Literal[
    "document_comparison",
    "new_shipping_instruction",
    "invoice_query",
    "general",
    "spam",
]


class AttachmentReference(Contract):
    """Reference to an attachment file associated with an email."""

    document_id: Text
    path: Text
    mime_type: str | None = None


class EmailRecord(Contract):
    """Ingested email message context and attachment references."""

    email_id: Text
    sender: str
    subject: str
    body: str
    attachments: list[AttachmentReference]


class ClassificationResult(Contract):
    """Validated intent classification result or proposed review state."""

    state: Literal["RESOLVED", "NEEDS_REVIEW"]
    category: EmailCategory | Category | None
    reason: Text
    evidence_ids: list[Text]
    confidence_indicator: Literal["HIGH", "MEDIUM", "LOW"] | None = None

    @model_validator(mode="after")
    def resolution(self) -> Self:
        require((self.category is not None) == (self.state == "RESOLVED"), "category exists only when resolved")
        if self.state == "RESOLVED":
            require(bool(self.evidence_ids), "resolved intent requires evidence")
        return self
