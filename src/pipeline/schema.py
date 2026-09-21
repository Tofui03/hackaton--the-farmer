from typing import Any, List, Optional
from pydantic import BaseModel, Field

# Mapping between competition categories and Strict Output Contract categories
COMPETITION_TO_STRICT_CAT = {
    "BL_COMPARISON": "document_comparison",
    "SI_REQUEST": "new_si_request",
    "INVOICE_QUERY": "invoice_query",
    "GENERAL": "general_message",
    "SPAM": "spam",
}

STRICT_TO_COMPETITION_CAT = {v: k for k, v in COMPETITION_TO_STRICT_CAT.items()}


class Discrepancy(BaseModel):
    """Specific field discrepancy between SI and BL."""
    field: str
    si_value: Any
    bl_value: Any


class HITLEscalation(BaseModel):
    """Human-in-the-loop escalation details."""
    needed: bool = False
    reason: Optional[str] = None
    evidence: Optional[str] = None


class AuditOutputRecord(BaseModel):
    """Strict Output Contract for each email evaluation."""
    email_id: str
    category: str
    mismatch_detected: bool = False
    result_summary: str = "No mismatch detected"
    discrepancies: List[Discrepancy] = Field(default_factory=list)
    hitl_escalation: HITLEscalation = Field(default_factory=HITLEscalation)

    def to_competition_dict(self) -> dict:
        """Convert to official hackathon submission format."""
        comp_category = STRICT_TO_COMPETITION_CAT.get(self.category, "GENERAL")

        if self.hitl_escalation.needed:
            return {
                "category": comp_category,
                "status": "NEEDS_REVIEW",
                "review_reason": self.hitl_escalation.reason or "unreadable",
                "defect_fields": [],
                "has_defect": False,
            }
        elif self.mismatch_detected:
            return {
                "category": comp_category,
                "status": "MISMATCH",
                "review_reason": None,
                "defect_fields": [d.field for d in self.discrepancies],
                "has_defect": True,
            }
        else:
            return {
                "category": comp_category,
                "status": "OK",
                "review_reason": None,
                "defect_fields": [],
                "has_defect": False,
            }
