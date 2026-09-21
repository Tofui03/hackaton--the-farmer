from src.models.base import Contract, Text, require
from src.models.ingestion import (
    AttachmentReference,
    Category,
    ClassificationResult,
    EmailCategory,
    EmailRecord,
)
from src.models.document import (
    DocumentReference,
    DocumentRole,
    DocumentRoleType,
    ParserResult,
    ParserStatus,
    ParserStatusType,
    Role,
)
from src.models.evidence import (
    EvidenceKind,
    EvidenceKindType,
    EvidenceLocation,
    EvidenceSourceType,
    FieldEvidence,
)

__all__ = [
    # Base
    "Contract",
    "Text",
    "require",
    # Ingestion (T02-01)
    "EmailCategory",
    "Category",
    "AttachmentReference",
    "EmailRecord",
    "ClassificationResult",
    # Document (T02-02)
    "DocumentRole",
    "Role",
    "DocumentRoleType",
    "ParserStatus",
    "ParserStatusType",
    "DocumentReference",
    "ParserResult",
    # Evidence (T02-03)
    "EvidenceKind",
    "EvidenceKindType",
    "EvidenceSourceType",
    "EvidenceLocation",
    "FieldEvidence",
]
