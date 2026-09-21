from __future__ import annotations

from decimal import Decimal
from enum import Enum
import re
from typing import Annotated, Literal, Self
from pydantic import Field, StrictInt, field_serializer, model_validator
from src.models.base import Contract, Text, require
from src.models.document import Role

FieldName = Literal[
    "shipper",
    "consignee",
    "notify_party",
    "port_of_loading",
    "port_of_discharge",
    "container_count",
    "gross_weight_kg",
]

FIELD_NAMES = (
    "shipper",
    "consignee",
    "notify_party",
    "port_of_loading",
    "port_of_discharge",
    "container_count",
    "gross_weight_kg",
)

Canonical = str | StrictInt | Decimal


def validate_canonical(field: str, value: object) -> None:
    """Validate canonical typed representation for comparison fields."""
    if field == "container_count":
        require(type(value) is int, "container_count must be an integer, not bool")
    elif field == "gross_weight_kg":
        if isinstance(value, Decimal):
            require(value.is_finite(), "weight must be a finite plain decimal")
        else:
            require(isinstance(value, str) and bool(value.strip()), "canonical text must be non-empty")
            require(
                re.fullmatch(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?", value) is not None,
                "weight must be a finite plain decimal string",
            )
    else:
        require(isinstance(value, str) and bool(value.strip()), "canonical text must be non-empty")


class NormalizedGrossWeight(Contract):
    """Canonical gross weight representation using exact Python Decimal (DC-04)."""

    canonical_kg: Decimal

    @model_validator(mode="after")
    def finite_check(self) -> Self:
        require(self.canonical_kg.is_finite(), "canonical_kg must be a finite decimal")
        return self

    @field_serializer("canonical_kg")
    def serialize_decimal(self, v: Decimal) -> str:
        return str(v)


class FieldReliability(str, Enum):
    """Reliability status assigned by the Reliability Gate."""

    NOT_PROCESSED = "NOT_PROCESSED"
    RELIABLE = "RELIABLE"
    MISSING = "MISSING"
    UNCERTAIN = "UNCERTAIN"
    CONFLICTING = "CONFLICTING"
    UNREADABLE = "UNREADABLE"


FieldStatus = FieldReliability


FieldReliabilityType = Literal[
    "NOT_PROCESSED",
    "RELIABLE",
    "MISSING",
    "UNCERTAIN",
    "CONFLICTING",
    "UNREADABLE",
]


class FieldCandidate(Contract):
    """Candidate field value extracted by parsers or AI adapters with supporting evidence."""

    raw_value: Text
    source_unit: str | None = None
    evidence_ids: list[Text]


class NormalizedField(Contract):
    """Deterministically normalized field value and associated rule version."""

    field: FieldName
    state: Literal["VALID", "INVALID", "NOT_ATTEMPTED"]
    value: Canonical | None
    rule_version: Text | None

    @model_validator(mode="after")
    def canonical(self) -> Self:
        if self.state == "VALID":
            require(
                self.value is not None and self.rule_version is not None,
                "valid normalization requires value and rules",
            )
            validate_canonical(self.field, self.value)
        else:
            require(self.value is None, "unsuccessful normalization has no trusted value")
        return self


class ExtractedField(Contract):
    """Field candidate tracking, reliability evaluation, and normalized value."""

    field: FieldName
    reliability: FieldReliability | FieldReliabilityType
    candidates: list[FieldCandidate]
    selected_candidate: Annotated[int, Field(ge=0)] | None
    normalized: NormalizedField | None
    explanation: Text

    @model_validator(mode="after")
    def reliability_gate(self) -> Self:
        if self.selected_candidate is not None:
            require(self.selected_candidate < len(self.candidates), "candidate index must exist")
        if self.normalized is not None:
            require(self.normalized.field == self.field, "normalization field differs")
        if self.reliability == "RELIABLE":
            require(self.selected_candidate is not None, "reliable field requires selection")
            require(
                bool(self.candidates[self.selected_candidate].evidence_ids),
                "reliable field requires evidence",
            )
            require(
                self.normalized is not None and self.normalized.state == "VALID",
                "reliable field requires valid normalization",
            )
        else:
            require(self.selected_candidate is None, "unresolved field must not select a trusted candidate")
        if self.reliability == "MISSING":
            require(not self.candidates, "missing field cannot have candidate values")
        if self.reliability == "CONFLICTING":
            require(len(self.candidates) >= 2, "conflict requires multiple candidates")
        return self


class DocumentExtraction(Contract):
    """Seven-field extraction mapping for a single identified document."""

    document_id: Text
    role: Role
    fields: dict[FieldName, ExtractedField]

    @model_validator(mode="after")
    def seven_fields(self) -> Self:
        require(set(self.fields) == set(FIELD_NAMES), "document field map must cover exactly seven fields")
        require(all(key == value.field for key, value in self.fields.items()), "field key mismatch")
        return self
