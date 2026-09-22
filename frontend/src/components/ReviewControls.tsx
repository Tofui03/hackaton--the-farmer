import type { AuditRecord, ReviewUpdate, RoleCorrection, FieldCorrection } from '../types/api';
import { CATEGORY_OPTIONS, FIELD_NAMES, humanizeReason, type FieldName } from '../utils';

export interface ReviewDraft {
  actorId: string;
  rationale: string;
  category: string;
  siDocument: string;
  blDocument: string;
  fieldDocument: string;
  field: FieldName;
  rawValue: string;
  evidenceId: string;
  correctionRationale: string;
}

interface Props {
  record: AuditRecord;
  draft: ReviewDraft;
  onChange: (next: ReviewDraft) => void;
  onSubmit: (payload: ReviewUpdate) => void;
  submitting: boolean;
}

export function buildReviewUpdate(record: AuditRecord, draft: ReviewDraft): ReviewUpdate {
  const category = draft.category || undefined;
  const roleCorrections: RoleCorrection[] = [];
  if (draft.siDocument && draft.evidenceId) roleCorrections.push({ document_id: draft.siDocument, assigned_role: 'SI', evidence_ids: [draft.evidenceId], rationale: draft.rationale });
  if (draft.blDocument && draft.evidenceId) roleCorrections.push({ document_id: draft.blDocument, assigned_role: 'BL', evidence_ids: [draft.evidenceId], rationale: draft.rationale });

  const corrections: FieldCorrection[] = [];
  if (draft.fieldDocument && draft.rawValue.trim() && draft.evidenceId) {
    corrections.push({
      document_id: draft.fieldDocument,
      field: draft.field,
      raw_value: draft.rawValue.trim(),
      evidence_ids: [draft.evidenceId],
      rationale: draft.correctionRationale || draft.rationale,
    });
  }

  return {
    review_id: record.review?.review_id ?? `review-${record.email_id}`,
    expected_revision: record.revision,
    actor_id: draft.actorId.trim(),
    action: category || roleCorrections.length || corrections.length ? 'CORRECT' : 'CONFIRM',
    rationale: draft.rationale.trim(),
    ...(category ? { category: category as ReviewUpdate['category'] } : {}),
    ...(category && record.classification.evidence_ids.length ? { classification_evidence_ids: record.classification.evidence_ids } : {}),
    ...(roleCorrections.length ? { role_corrections: roleCorrections } : {}),
    ...(corrections.length ? { corrections } : {}),
  };
}

export function ReviewControls({ record, draft, onChange, onSubmit, submitting }: Props) {
  const attachments = record.email.attachments;
  const issues = record.review?.issues ?? [];
  const update = (patch: Partial<ReviewDraft>) => onChange({ ...draft, ...patch });
  const requiresEvidence = Boolean(draft.siDocument || draft.blDocument || (draft.fieldDocument && draft.rawValue.trim()));
  const canSubmit = Boolean(draft.actorId.trim() && draft.rationale.trim() && (!requiresEvidence || draft.evidenceId));

  return (
    <div className="space-y-5">
      <section className="panel p-4">
        <div className="text-xs font-semibold uppercase tracking-widest text-amber-400">Active Review Issues</div>
        <div className="mt-3 space-y-3">
          {issues.map((issue) => (
            <div key={issue.issue_id} className="rounded-lg border border-amber-900/70 bg-amber-950/20 p-3">
              <div className="font-semibold text-amber-200">{humanizeReason(String(issue.logical_reason))}</div>
              <div className="mt-1 text-xs text-slate-400">{issue.suggested_action}</div>
              <div className="mt-1 text-[11px] font-mono text-slate-600">{String(issue.logical_reason)}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="panel p-4">
        <h3 className="font-semibold text-white">Operator & rationale</h3>
        <div className="mt-3 grid gap-3">
          <label className="text-xs text-slate-400">Operator ID<input className="input mt-1" value={draft.actorId} onChange={(e) => update({ actorId: e.target.value })} placeholder="operator-01" /></label>
          <label className="text-xs text-slate-400">Review rationale<textarea className="input mt-1 min-h-20" value={draft.rationale} onChange={(e) => update({ rationale: e.target.value })} placeholder="Explain the source-level decision" /></label>
        </div>
      </section>

      <section className="panel p-4">
        <h3 className="font-semibold text-white">Classification correction</h3>
        <select className="input mt-3" value={draft.category} onChange={(e) => update({ category: e.target.value })}>
          <option value="">Keep current classification</option>
          {CATEGORY_OPTIONS.map((category) => <option key={category} value={category}>{category}</option>)}
        </select>
      </section>

      <section className="panel p-4">
        <h3 className="font-semibold text-white">Document role assignment</h3>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <label className="text-xs text-slate-400">Shipping Instruction<select className="input mt-1" value={draft.siDocument} onChange={(e) => update({ siDocument: e.target.value })}><option value="">No change</option>{attachments.map((a) => <option key={a.document_id} value={a.document_id}>{a.document_id}</option>)}</select></label>
          <label className="text-xs text-slate-400">Draft Bill of Lading<select className="input mt-1" value={draft.blDocument} onChange={(e) => update({ blDocument: e.target.value })}><option value="">No change</option>{attachments.map((a) => <option key={a.document_id} value={a.document_id} disabled={a.document_id === draft.siDocument}>{a.document_id}</option>)}</select></label>
        </div>
      </section>

      <section className="panel p-4">
        <h3 className="font-semibold text-white">Field candidate correction</h3>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <label className="text-xs text-slate-400">Target document<select className="input mt-1" value={draft.fieldDocument} onChange={(e) => update({ fieldDocument: e.target.value })}><option value="">No field correction</option>{attachments.map((a) => <option key={a.document_id} value={a.document_id}>{a.document_id}</option>)}</select></label>
          <label className="text-xs text-slate-400">Field<select className="input mt-1" value={draft.field} onChange={(e) => update({ field: e.target.value as FieldName })}>{FIELD_NAMES.map((field) => <option key={field} value={field}>{field}</option>)}</select></label>
          <label className="text-xs text-slate-400 sm:col-span-2">Correct raw value<input className="input mt-1" value={draft.rawValue} onChange={(e) => update({ rawValue: e.target.value })} /></label>
          <label className="text-xs text-slate-400">Evidence citation<select className="input mt-1" value={draft.evidenceId} onChange={(e) => update({ evidenceId: e.target.value })}><option value="">Select grounded evidence</option>{record.evidence.map((evidence) => <option key={evidence.evidence_id} value={evidence.evidence_id}>{evidence.evidence_id} · {evidence.source_id}</option>)}</select></label>
          <label className="text-xs text-slate-400">Correction rationale<input className="input mt-1" value={draft.correctionRationale} onChange={(e) => update({ correctionRationale: e.target.value })} /></label>
        </div>
      </section>

      <div className="sticky bottom-4 flex items-center justify-between rounded-xl border border-slate-700 bg-slate-950/95 p-4 shadow-xl backdrop-blur">
        <div className="text-xs text-slate-400">Submitting against revision <span className="font-mono text-white">r{record.revision}</span>. Match booleans cannot be edited.</div>
        <button className="btn-primary" disabled={!canSubmit || submitting} onClick={() => onSubmit(buildReviewUpdate(record, draft))}>{submitting ? 'Recomputing deterministic comparisons…' : 'Submit ReviewUpdate'}</button>
      </div>
    </div>
  );
}
