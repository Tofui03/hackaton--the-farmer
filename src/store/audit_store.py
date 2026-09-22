from __future__ import annotations

import json
import logging
from pathlib import Path
import threading
from typing import Any, Dict, List, Optional

from src.models.audit import AuditRecord

logger = logging.getLogger(__name__)


class RevisionConflictError(Exception):
    """Raised when an update specifies a stale revision (HTTP 409 / DC-07)."""

    def __init__(self, current_revision: int, expected_revision: int) -> None:
        super().__init__(
            f"Revision conflict: current revision is {current_revision}, but expected {expected_revision}"
        )
        self.current_revision = current_revision
        self.expected_revision = expected_revision


class AuditStore:
    """Thread-safe store for AuditRecord models with revision indexing and query capabilities."""

    def __init__(self, storage_file: Optional[Path] = None) -> None:
        self._lock = threading.RLock()
        self._records: Dict[str, AuditRecord] = {}
        self.storage_file = storage_file
        if storage_file and storage_file.exists():
            self.load_from_file(storage_file)

    def save(self, record: AuditRecord) -> AuditRecord:
        """Insert or update an audit record."""
        with self._lock:
            self._records[record.email_id] = record
            if self.storage_file:
                self.persist_to_file(self.storage_file)
            return record

    def get(self, email_id: str) -> Optional[AuditRecord]:
        """Retrieve record by email_id."""
        with self._lock:
            return self._records.get(email_id)

    def list(
        self,
        state: Optional[str] = None,
        category: Optional[str] = None,
        outcome: Optional[str] = None,
        has_discrepancy: Optional[bool] = None,
    ) -> List[AuditRecord]:
        """Query records with optional filtering (API-AUD-001)."""
        with self._lock:
            results = list(self._records.values())
            if state is not None:
                results = [r for r in results if r.state == state]
            if category is not None:
                results = [r for r in results if r.classification.category == category]
            if outcome is not None:
                results = [r for r in results if r.outcome == outcome]
            if has_discrepancy is not None:
                if has_discrepancy:
                    results = [r for r in results if bool(r.discrepancies)]
                else:
                    results = [r for r in results if not r.discrepancies]
            return results

    def count(self) -> int:
        """Total records in store."""
        with self._lock:
            return len(self._records)

    def get_summary(self) -> Dict[str, Any]:
        """Compute live aggregated metrics across all stored records (zero hardcoding, REG-003)."""
        with self._lock:
            records = list(self._records.values())
            total = len(records)
            states: Dict[str, int] = {}
            categories: Dict[str, int] = {}
            outcomes: Dict[str, int] = {}
            review_reasons: Dict[str, int] = {}
            discrepancy_count = 0

            for r in records:
                states[r.state] = states.get(r.state, 0) + 1
                cat = r.classification.category or "unclassified"
                categories[cat] = categories.get(cat, 0) + 1
                out = r.outcome or "unresolved"
                outcomes[out] = outcomes.get(out, 0) + 1

                if r.discrepancies:
                    discrepancy_count += 1

                if r.review:
                    for issue in r.review.issues:
                        reason = (
                            issue.logical_reason.value
                            if hasattr(issue.logical_reason, "value")
                            else str(issue.logical_reason)
                        )
                        review_reasons[reason] = review_reasons.get(reason, 0) + 1

            return {
                "total_records": total,
                "states": states,
                "categories": categories,
                "outcomes": outcomes,
                "discrepant_records": discrepancy_count,
                "review_reasons": review_reasons,
            }

    def clear(self) -> None:
        """Clear all records (primarily for test resets)."""
        with self._lock:
            self._records.clear()

    def persist_to_file(self, file_path: Path) -> None:
        """Dump records as JSON."""
        with self._lock:
            data = [json.loads(r.model_dump_json()) for r in self._records.values()]
            file_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def load_from_file(self, file_path: Path) -> None:
        """Load records from JSON file."""
        with self._lock:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            for item in data:
                rec = AuditRecord.model_validate(item)
                self._records[rec.email_id] = rec
