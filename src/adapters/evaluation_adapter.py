"""T13 evaluation boundary: deterministic serialization, never shipment inference."""
from collections import Counter
from collections.abc import Iterable, Mapping
from types import MappingProxyType
from typing import Any

from pydantic import ValidationError

from src.models.audit import AuditRecord, SubmissionRecord


class ExportBlockedException(Exception):
    """A whole submission cannot be represented safely under DC-08."""

    code = "EXPORT_BLOCKED"
    message = "Cannot export submission while cases remain in NEEDS_REVIEW"

    def __init__(self, blocking_emails: Iterable[str]) -> None:
        self.blocking_emails = sorted(set(blocking_emails))
        super().__init__(self.message)


class EvaluationAdapter:
    """Convert validated, resolved AuditRecords to the existing external schema."""

    CATEGORY_MAPPING = MappingProxyType({
        "document_comparison": "BL_COMPARISON",
        "new_shipping_instruction": "SI_REQUEST",
        "invoice_query": "INVOICE_QUERY",
        "general": "GENERAL",
        "spam": "SPAM",
    })

    @staticmethod
    def assert_exportable(record: AuditRecord) -> None:
        """Inspect decided workflow state; do not re-run any upstream stage."""
        category = record.classification.category
        if (
            record.state != "COMPLETE"
            or record.classification.state != "RESOLVED"
            or category not in EvaluationAdapter.CATEGORY_MAPPING
            or (record.review is not None and record.review.state == "OPEN")
            or (record.partial_result is not None and record.partial_result.unresolved_fields)
        ):
            raise ExportBlockedException([record.email_id])
        allowed_outcomes = ("MATCH", "MISMATCH") if category == "document_comparison" else ("NOT_APPLICABLE",)
        if record.outcome not in allowed_outcomes:
            raise ExportBlockedException([record.email_id])

    def to_submission_record(self, record: AuditRecord) -> SubmissionRecord:
        """Map completed decisions, preserving every confirmed defect identifier."""
        self.assert_exportable(record)
        mismatch = record.outcome == "MISMATCH"
        # AuditRecord guarantees discrepancies originate from its deterministic
        # comparison results. No raw values are inspected or compared here.
        fields = sorted(item.field for item in record.discrepancies)
        if bool(fields) != mismatch:
            raise ExportBlockedException([record.email_id])
        try:
            return SubmissionRecord(
                category=self.CATEGORY_MAPPING[record.classification.category],
                status="MISMATCH" if mismatch else "OK",
                review_reason=None,
                has_defect=mismatch,
                defect_fields=fields,
            )
        except ValidationError as error:
            raise ExportBlockedException([record.email_id]) from error

    @staticmethod
    def validate_submission_dict(
        submission: Mapping[str, Any], expected_email_ids: Iterable[str]
    ) -> tuple[bool, list[str]]:
        """Validate serialized shape/coverage, not correctness against answer keys."""
        errors: list[str] = []
        expected, actual = set(expected_email_ids), set(submission)
        if expected - actual:
            errors.append(f"Missing email IDs: {sorted(expected - actual)}")
        if actual - expected:
            errors.append(f"Extra email IDs: {sorted(actual - expected)}")
        official_fields = set(SubmissionRecord.model_fields)
        for email_id, payload in submission.items():
            if not isinstance(payload, dict) or set(payload) != official_fields:
                errors.append(f"{email_id}: expected exactly {sorted(official_fields)}")
                continue
            try:
                item = SubmissionRecord.model_validate(payload)
                if item.status == "NEEDS_REVIEW":
                    errors.append(f"{email_id}: unresolved export is blocked under DC-08")
                if item.defect_fields != sorted(item.defect_fields):
                    errors.append(f"{email_id}: defect_fields must be sorted")
            except ValidationError as error:
                errors.append(f"{email_id}: {error}")
        return not errors, errors


class ExportService:
    """All-or-nothing export of a canonical run; no HTTP or file side effects."""

    def __init__(self, adapter: EvaluationAdapter | None = None) -> None:
        self.adapter = adapter if adapter is not None else EvaluationAdapter()

    def export(
        self,
        records: Iterable[AuditRecord],
        *,
        expected_email_ids: Iterable[str] | None = None,
    ) -> dict[str, dict[str, Any]]:
        """Return the complete official payload or raise ExportBlockedException.

        API callers pass the full store snapshot. Batch runners additionally
        pass the ingested ID set so a limited run cannot masquerade as complete.
        """
        snapshot = list(records)
        counts = Counter(record.email_id for record in snapshot)
        blocked = {email_id for email_id, count in counts.items() if count != 1}
        if expected_email_ids is not None:
            blocked.update(set(expected_email_ids).symmetric_difference(counts))
        for record in snapshot:
            try:
                self.adapter.assert_exportable(record)
            except ExportBlockedException as error:
                blocked.update(error.blocking_emails)
        if blocked:
            raise ExportBlockedException(blocked)

        # Build privately. A mapping error can never return a partial dictionary.
        submission = {}
        for record in sorted(snapshot, key=lambda item: item.email_id):
            try:
                submission[record.email_id] = self.adapter.to_submission_record(record).model_dump(mode="json")
            except ExportBlockedException as error:
                blocked.update(error.blocking_emails)
        if blocked:
            raise ExportBlockedException(blocked)
        return submission
