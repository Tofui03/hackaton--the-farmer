import { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { getAudit } from '../api/client';
import { ComparisonMatrix } from '../components/ComparisonMatrix';
import { EvidenceDrawer } from '../components/EvidenceDrawer';
import { OutcomeBadge } from '../components/OutcomeBadge';
import { StatusBadge } from '../components/StatusBadge';
import type { AuditRecord, FieldEvidence } from '../types/api';
import type { FieldName } from '../utils';

export function CaseDetailView() {
  const { emailId = '' } = useParams();
  const [record, setRecord] = useState<AuditRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [drawer, setDrawer] = useState<{ field: FieldName; evidence: FieldEvidence[] } | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setRecord(await getAudit(decodeURIComponent(emailId)));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Unable to load case');
    } finally {
      setLoading(false);
    }
  }, [emailId]);

  useEffect(() => { void load(); }, [load]);

  if (loading) return <div className="panel p-8 text-sm text-slate-400">Loading case detail…</div>;
  if (error || !record) return <div className="rounded-lg border border-rose-800 bg-rose-950/30 p-4 text-sm text-rose-200">{error ?? 'Case not found'}</div>;

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-start">
        <div>
          <div className="text-xs text-slate-500"><Link to="/cases" className="text-blue-400 hover:text-blue-300">Cases</Link> / {record.email_id}</div>
          <h1 className="mt-2 font-mono text-2xl font-bold text-white">{record.email_id}</h1>
          <div className="mt-1 text-sm text-slate-300">{record.email.subject || '(No subject)'}</div>
          <div className="mt-3 flex flex-wrap gap-2">
            {record.classification.category ? <StatusBadge label={record.classification.category} tone="blue" /> : <StatusBadge label="Unresolved Classification" tone="amber" />}
            <StatusBadge label={record.state} tone={record.state === 'NEEDS_REVIEW' ? 'amber' : 'slate'} />
            <OutcomeBadge record={record} />
            <StatusBadge label={`r${record.revision}${record.previous_revision ? ` ← r${record.previous_revision}` : ''}`} tone="slate" />
          </div>
        </div>
        <div className="flex gap-2">
          <button className="btn-secondary" onClick={() => void load()}>Refresh</button>
          {record.state === 'NEEDS_REVIEW' ? <Link className="btn-primary" to={`/cases/${encodeURIComponent(record.email_id)}/review`}>Open Review Workspace</Link> : null}
        </div>
      </div>

      <section className="panel p-5">
        <details open>
          <summary className="cursor-pointer font-semibold text-white">Email & Attachment Context</summary>
          <div className="mt-4 grid gap-4 lg:grid-cols-3">
            <div><div className="text-xs uppercase text-slate-500">Sender</div><div className="mt-1 text-sm text-slate-200">{record.email.sender}</div></div>
            <div className="lg:col-span-2"><div className="text-xs uppercase text-slate-500">Subject</div><div className="mt-1 text-sm text-slate-200">{record.email.subject || '(No subject)'}</div></div>
            <div className="lg:col-span-3"><div className="text-xs uppercase text-slate-500">Body</div><pre className="mt-2 max-h-56 overflow-auto whitespace-pre-wrap rounded-lg border border-slate-800 bg-slate-950 p-3 text-xs text-slate-300">{record.email.body}</pre></div>
          </div>
          <div className="mt-5 grid gap-3 md:grid-cols-2">
            {record.email.attachments.map((attachment) => {
              const parser = record.parsers.find((item) => item.document_id === attachment.document_id);
              return (
                <div key={attachment.document_id} className="rounded-lg border border-slate-800 bg-slate-950 p-3">
                  <div className="font-mono text-xs text-blue-300">{attachment.document_id}</div>
                  <div className="mt-1 text-xs text-slate-500">{attachment.path}</div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {parser ? <StatusBadge label={String(parser.status)} tone={parser.usable_for_extraction ? 'green' : 'amber'} /> : <StatusBadge label="NOT PARSED" tone="slate" />}
                    {parser?.is_scanned ? <StatusBadge label="SCANNED" tone="blue" /> : null}
                    {parser?.page_count ? <StatusBadge label={`${parser.page_count} page${parser.page_count === 1 ? '' : 's'}`} tone="slate" /> : null}
                  </div>
                </div>
              );
            })}
            {record.email.attachments.length === 0 ? <div className="text-sm text-slate-500">No attachments supplied.</div> : null}
          </div>
        </details>
      </section>

      <section className="panel p-5">
        <h2 className="font-semibold text-white">Document Role Resolution</h2>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          {(['SI', 'BL'] as const).map((role) => {
            const doc = record.documents.find((item) => item.role === role);
            return <div key={role} className="rounded-lg border border-slate-800 bg-slate-950 p-4"><div className="text-xs uppercase text-slate-500">{role === 'SI' ? 'Shipping Instruction (SI)' : 'Draft Bill of Lading (BL)'}</div><div className="mt-2 font-mono text-sm text-slate-200">{doc?.document_id ?? 'Unresolved'}</div>{doc ? <div className="mt-2 text-xs text-slate-500">Evidence: {doc.identification_evidence_ids.join(', ') || '—'}</div> : <div className="mt-2 text-xs text-amber-300">Document role has not been uniquely resolved.</div>}</div>;
          })}
        </div>
      </section>

      {record.classification.category === 'document_comparison' ? (
        <section>
          <div className="mb-3 flex items-end justify-between gap-4"><div><h2 className="text-lg font-semibold text-white">Comparison Matrix</h2><p className="mt-1 text-xs text-slate-500">All seven mandatory fields remain visible, including unresolved fields.</p></div></div>
          <ComparisonMatrix record={record} onEvidence={(field, evidence) => setDrawer({ field, evidence })} />
        </section>
      ) : (
        <section className="panel p-5"><h2 className="font-semibold text-white">Non-Comparison Case</h2><p className="mt-2 text-sm text-slate-400">{record.result_summary}</p></section>
      )}

      <section className="panel p-5">
        <details>
          <summary className="cursor-pointer font-semibold text-white">Audit lineage & processing metadata</summary>
          <div className="mt-4 grid gap-3 text-xs text-slate-400 md:grid-cols-3"><div>Revision: <span className="font-mono text-white">r{record.revision}</span></div><div>Technical limit: <span className="font-mono text-white">{record.processing.technical_attempt_limit}</span></div><div>Semantic limit: <span className="font-mono text-white">{record.processing.semantic_attempt_limit}</span></div></div>
          <div className="mt-4 space-y-2">{record.processing.attempts.map((attempt) => <div key={attempt.attempt_id} className="rounded-lg border border-slate-800 bg-slate-950 p-3 text-xs"><span className="font-mono text-blue-300">{attempt.attempt_id}</span><span className="ml-3 text-slate-400">{attempt.stage} · {attempt.kind} · {attempt.outcome}</span></div>)}</div>
        </details>
      </section>

      <EvidenceDrawer open={drawer !== null} field={drawer?.field ?? null} evidence={drawer?.evidence ?? []} onClose={() => setDrawer(null)} />
    </div>
  );
}
