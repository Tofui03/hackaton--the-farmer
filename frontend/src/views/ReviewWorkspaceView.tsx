import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { ApiError, getAudit, submitReview } from '../api/client';
import { ComparisonMatrix } from '../components/ComparisonMatrix';
import { ConflictModal } from '../components/ConflictModal';
import { EvidenceDrawer } from '../components/EvidenceDrawer';
import { ReviewControls, type ReviewDraft } from '../components/ReviewControls';
import type { AuditRecord, FieldEvidence, ReviewUpdate } from '../types/api';
import type { FieldName } from '../utils';

const EMPTY_DRAFT: ReviewDraft = {
  actorId: '',
  rationale: '',
  category: '',
  siDocument: '',
  blDocument: '',
  fieldDocument: '',
  field: 'shipper',
  rawValue: '',
  evidenceId: '',
  correctionRationale: '',
};

export function ReviewWorkspaceView() {
  const { emailId = '' } = useParams();
  const navigate = useNavigate();
  const [record, setRecord] = useState<AuditRecord | null>(null);
  const [draft, setDraft] = useState<ReviewDraft>(EMPTY_DRAFT);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conflict, setConflict] = useState<string | null>(null);
  const [drawer, setDrawer] = useState<{ field: FieldName; evidence: FieldEvidence[] } | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setRecord(await getAudit(decodeURIComponent(emailId)));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Unable to load review case');
    } finally {
      setLoading(false);
    }
  }, [emailId]);

  useEffect(() => { void load(); }, [load]);

  const submit = async (payload: ReviewUpdate) => {
    setSubmitting(true);
    setError(null);
    try {
      const updated = await submitReview(decodeURIComponent(emailId), payload);
      navigate(`/cases/${encodeURIComponent(updated.email_id)}`, { replace: true });
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 409) {
        setConflict(cause.payload?.message ?? 'This case was updated while you were editing.');
      } else {
        setError(cause instanceof Error ? cause.message : 'Review submission failed');
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <div className="panel p-8 text-sm text-slate-400">Loading review workspace…</div>;
  if (error && !record) return <div className="rounded-lg border border-rose-800 bg-rose-950/30 p-4 text-sm text-rose-200">{error}</div>;
  if (!record) return null;

  return (
    <div className="space-y-5">
      <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
        <div><div className="text-xs text-slate-500"><Link to="/cases" className="text-blue-400">Cases</Link> / <Link to={`/cases/${encodeURIComponent(record.email_id)}`} className="text-blue-400">{record.email_id}</Link> / review</div><h1 className="mt-2 text-2xl font-bold text-white">Human Review Workspace</h1><p className="mt-1 text-sm text-slate-400">Revision r{record.revision}. Reliable work stays visible while you correct only the unresolved source information.</p></div>
        <Link className="btn-secondary" to={`/cases/${encodeURIComponent(record.email_id)}`}>Back to Case Detail</Link>
      </div>

      {record.state !== 'NEEDS_REVIEW' ? <div className="rounded-lg border border-emerald-800 bg-emerald-950/20 p-4 text-sm text-emerald-200">This case is already complete. Review submission is not required.</div> : null}
      {error ? <div className="rounded-lg border border-rose-800 bg-rose-950/30 p-4 text-sm text-rose-200">{error}</div> : null}

      <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1.5fr)_minmax(360px,0.8fr)]">
        <div className="space-y-4">
          <section className="panel p-4"><div className="text-xs uppercase tracking-widest text-slate-500">Source context</div><div className="mt-2 font-semibold text-white">{record.email.subject || '(No subject)'}</div><div className="mt-1 text-xs text-slate-400">{record.email.sender} · {record.email.attachments.length} attachment(s)</div></section>
          {record.classification.category === 'document_comparison' ? <ComparisonMatrix record={record} onEvidence={(field, evidence) => setDrawer({ field, evidence })} /> : <section className="panel p-5 text-sm text-slate-400">Classification is unresolved or non-comparison. Use the correction controls to confirm the source-level intent.</section>}
        </div>
        <ReviewControls record={record} draft={draft} onChange={setDraft} onSubmit={(payload) => void submit(payload)} submitting={submitting} />
      </div>

      <EvidenceDrawer open={drawer !== null} field={drawer?.field ?? null} evidence={drawer?.evidence ?? []} onClose={() => setDrawer(null)} />
      <ConflictModal
        open={conflict !== null}
        message={conflict ?? ''}
        onClose={() => setConflict(null)}
        onReload={() => { setConflict(null); void load(); }}
        onReviewDifferences={() => { window.open(`/cases/${encodeURIComponent(record.email_id)}`, '_blank', 'noopener,noreferrer'); }}
      />
    </div>
  );
}
