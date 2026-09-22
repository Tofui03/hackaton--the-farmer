from __future__ import annotations

import logging
from typing import Optional
import uuid

from src.comparator.field_comparator import compare_seven_fields
from src.models.audit import AuditRecord
from src.models.document import DocumentReference, Role
from src.models.evidence import FieldEvidence
from src.models.comparison import PartialResult
from src.models.extraction import (
    FIELD_NAMES,
    DocumentExtraction,
    ExtractedField,
    FieldCandidate,
    FieldReliability,
)
from src.models.review import (
    FieldCorrection,
    ReviewAction,
    ReviewCase,
    ReviewIssue,
    ReviewUpdate,
    RoleCorrection,
    Stage,
)
from src.normalization.text_normalizer import normalize_text
from src.normalization.unit_normalizer import (
    normalize_container_count,
    normalize_gross_weight_kg,
)
from src.pipeline.stage3_extract import _parse_container_count_value
from src.store.audit_store import RevisionConflictError

logger = logging.getLogger(__name__)


class ReviewService:
    """Applies human review actions (confirm/correct) and recomputes canonical results (DC-07, FR-016)."""

    def apply_review(
        self,
        current_record: AuditRecord,
        update: ReviewUpdate,
    ) -> AuditRecord:
        """Process ReviewUpdate against current AuditRecord and produce new revision."""
        # 1. Concurrency Check (DC-07 / HITL-REV-006 / API-REV-002)
        if update.expected_revision != current_record.revision:
            raise RevisionConflictError(
                current_revision=current_record.revision,
                expected_revision=update.expected_revision,
            )

        # 2. Check Review Case
        if current_record.review is None or current_record.review.review_id != update.review_id:
            raise ValueError(
                f"Review ID mismatch: record has '{current_record.review.review_id if current_record.review else None}', "
                f"update specifies '{update.review_id}'"
            )

        new_revision = current_record.revision + 1
        email_id = current_record.email_id

        # Copy existing evidence and add any newly supplied evidence
        evidence_map = {e.evidence_id: e for e in current_record.evidence}
        for ev in update.added_evidence:
            evidence_map[ev.evidence_id] = ev

        # Add review action evidence
        rev_ev_id = f"ev_rev_{email_id}_r{new_revision}"
        if rev_ev_id not in evidence_map:
            rev_ev = FieldEvidence(
                evidence_id=rev_ev_id,
                source_type="email",
                source_id=email_id,
                kind="text_span",
                quote=f"Human review update: {update.action} by {update.actor_id}. Rationale: {update.rationale}",
            )
            evidence_map[rev_ev_id] = rev_ev

        # 3. Action = CONFIRM (HITL-REV-005)
        # CONFIRM records human assessment but CANNOT force unresolved fields into reliability.
        if update.action == ReviewAction.CONFIRM or update.action == "CONFIRM":
            if current_record.partial_result and current_record.partial_result.unresolved_fields:
                # Maintains NEEDS_REVIEW as mandated by HITL-REV-005
                return current_record.model_copy(
                    update={
                        "revision": new_revision,
                        "previous_revision": current_record.revision,
                        "evidence": list(evidence_map.values()),
                        "result_summary": f"Review confirmed by {update.actor_id}, remaining issues require resolution: {current_record.partial_result.unresolved_fields}",
                    }
                )
            updated_review = current_record.review.model_copy(update={"state": "RESOLVED"})
            return current_record.model_copy(
                update={
                    "revision": new_revision,
                    "previous_revision": current_record.revision,
                    "review": updated_review,
                    "evidence": list(evidence_map.values()),
                }
            )

        # 4. Action = CORRECT (HITL-REV-002, 003, 004)
        classification = current_record.classification.model_copy()
        documents = [d.model_copy() for d in current_record.documents]
        extractions = [e.model_copy(deep=True) for e in current_record.extractions]
        parsers = list(current_record.parsers)

        # A. Category Correction (HITL-REV-003)
        if update.category is not None:
            classification.category = update.category
            classification.state = "RESOLVED"
            classification.reason = f"Corrected by human reviewer {update.actor_id}: {update.rationale}"
            for evid in update.classification_evidence_ids:
                if evid not in classification.evidence_ids:
                    classification.evidence_ids.append(evid)

            if update.category != "document_comparison":
                updated_review = current_record.review.model_copy(update={"state": "RESOLVED"})
                return AuditRecord(
                    email_id=email_id,
                    revision=new_revision,
                    previous_revision=current_record.revision,
                    email=current_record.email,
                    classification=classification,
                    state="COMPLETE",
                    outcome="NOT_APPLICABLE",
                    mismatch_detected=None,
                    result_summary=f"Non-comparison category: {classification.category}",
                    documents=[],
                    parsers=[],
                    extractions=[],
                    evidence=list(evidence_map.values()),
                    partial_result=None,
                    discrepancies=[],
                    review=updated_review,
                    processing=current_record.processing,
                )

        # B. Role Corrections (HITL-REV-004)
        if update.role_corrections:
            doc_map = {d.document_id: d for d in documents}
            for rc in update.role_corrections:
                if rc.document_id in doc_map:
                    doc_map[rc.document_id].role = rc.assigned_role
                    for evid in rc.evidence_ids:
                        if evid not in doc_map[rc.document_id].identification_evidence_ids:
                            doc_map[rc.document_id].identification_evidence_ids.append(evid)
                else:
                    doc_ref = DocumentReference(
                        document_id=rc.document_id,
                        role=rc.assigned_role,
                        identification_evidence_ids=list(rc.evidence_ids),
                    )
                    documents.append(doc_ref)
                    doc_map[rc.document_id] = doc_ref

        # C. Field Corrections (HITL-REV-002)
        ext_by_doc = {e.document_id: e for e in extractions}

        for fc in update.corrections:
            if fc.document_id not in ext_by_doc:
                doc_role = "UNKNOWN"
                for d in documents:
                    if d.document_id == fc.document_id:
                        doc_role = d.role
                        break
                new_ext = DocumentExtraction(
                    document_id=fc.document_id,
                    role=doc_role if doc_role in ("SI", "BL") else "SI",
                    fields={},
                )
                extractions.append(new_ext)
                ext_by_doc[fc.document_id] = new_ext

            target_ext = ext_by_doc[fc.document_id]

            # Deterministic Normalization
            if fc.field == "container_count":
                _, parsed_int = _parse_container_count_value(fc.raw_value)
                norm_res = normalize_container_count(parsed_int)
            elif fc.field == "gross_weight_kg":
                norm_res = normalize_gross_weight_kg(fc.raw_value)
            else:
                norm_res = normalize_text(fc.field, fc.raw_value)

            fc_ev_id = f"ev_corr_{email_id}_{fc.field}_{uuid.uuid4().hex[:6]}"
            if fc_ev_id not in evidence_map:
                evidence_map[fc_ev_id] = FieldEvidence(
                    evidence_id=fc_ev_id,
                    source_type="document",
                    source_id=fc.document_id,
                    kind="text_span",
                    quote=fc.raw_value,
                )

            ev_ids = list(fc.evidence_ids)
            if fc_ev_id not in ev_ids:
                ev_ids.append(fc_ev_id)

            cand = FieldCandidate(
                raw_value=fc.raw_value,
                evidence_ids=ev_ids,
            )

            curr_f = target_ext.fields.get(fc.field)
            cand_list = list(curr_f.candidates) if curr_f else []
            cand_list.append(cand)

            target_ext.fields[fc.field] = ExtractedField(
                field=fc.field,
                reliability=FieldReliability.RELIABLE if norm_res.state == "VALID" else FieldReliability.UNCERTAIN,
                candidates=cand_list,
                selected_candidate=len(cand_list) - 1,
                normalized=norm_res if norm_res.state == "VALID" else None,
                explanation=f"Corrected by human operator: '{fc.raw_value}' (Rationale: {fc.rationale})",
            )

        # D. Re-run Deterministic 7-Field Comparison (HITL-REV-002)
        si_ext = None
        bl_ext = None
        for e in extractions:
            if e.role == "SI":
                si_ext = e
            elif e.role == "BL":
                bl_ext = e

        if si_ext is not None and bl_ext is not None:
            comp_res = compare_seven_fields(si_ext, bl_ext)
            partial_result = comp_res.partial_result
            discrepancies = comp_res.discrepancies

            if not comp_res.unresolved_fields:
                updated_review = current_record.review.model_copy(update={"state": "RESOLVED"})
                return AuditRecord(
                    email_id=email_id,
                    revision=new_revision,
                    previous_revision=current_record.revision,
                    email=current_record.email,
                    classification=classification,
                    state="COMPLETE",
                    outcome=comp_res.outcome,
                    mismatch_detected=comp_res.mismatch_detected,
                    result_summary=comp_res.result_summary,
                    documents=documents,
                    parsers=parsers,
                    extractions=extractions,
                    evidence=list(evidence_map.values()),
                    partial_result=partial_result,
                    discrepancies=discrepancies,
                    review=updated_review,
                    processing=current_record.processing,
                )
            else:
                return AuditRecord(
                    email_id=email_id,
                    revision=new_revision,
                    previous_revision=current_record.revision,
                    email=current_record.email,
                    classification=classification,
                    state="NEEDS_REVIEW",
                    outcome=None,
                    mismatch_detected=None,
                    result_summary=comp_res.result_summary,
                    documents=documents,
                    parsers=parsers,
                    extractions=extractions,
                    evidence=list(evidence_map.values()),
                    partial_result=partial_result,
                    discrepancies=discrepancies,
                    review=current_record.review,
                    processing=current_record.processing,
                )

        partial_res = current_record.partial_result
        if classification.category == "document_comparison" and partial_res is None:
            partial_res = PartialResult(comparisons=[], unresolved_fields=list(FIELD_NAMES))

        return current_record.model_copy(
            update={
                "revision": new_revision,
                "previous_revision": current_record.revision,
                "classification": classification,
                "documents": documents,
                "extractions": extractions,
                "evidence": list(evidence_map.values()),
                "partial_result": partial_res,
            }
        )
