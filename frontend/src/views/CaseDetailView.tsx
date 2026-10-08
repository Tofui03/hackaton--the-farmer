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

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) {
    return (
      <div className="glass-panel animate-pulse p-12 text-center text-sm text-slate-400">
        Loading case detail telemetry…
      </div>
    );
  }

  if (error || !record) {
    return (
      <div className="glass-panel border-rose-500/30 bg-rose-950/20 p-6 text-sm text-rose-300">
        {error ?? 'Case not found'}
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Hero Document Identity Section */}
      <div className="flex flex-col justify-between gap-6 lg:flex-row lg:items-start">
        <div>
          <div className="text-xs text-slate-600 dark:text-slate-400">
            <Link to="/cases" className="text-blue-700 dark:text-blue-400 hover:underline">
              Cases
            </Link>{' '}
            / <span className="font-mono text-slate-700 dark:text-slate-300">{record.email_id}</span>
          </div>
          <h1 className="mt-2 font-mono text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white sm:text-4xl">
            {record.email_id}
          </h1>
          <div className="mt-1 font-editorial italic text-lg text-slate-700 dark:text-slate-300">
            {record.email.subject || '(No subject)'}
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-2">
            {record.classification.category ? (
              <StatusBadge label={record.classification.category} tone="blue" />
            ) : (
              <StatusBadge label="Unresolved Classification" tone="amber" />
            )}
            <StatusBadge
              label={record.state}
              tone={record.state === 'NEEDS_REVIEW' ? 'amber' : 'slate'}
            />
            <OutcomeBadge record={record} />
            <StatusBadge
              label={`r${record.revision}${
                record.previous_revision ? ` ← r${record.previous_revision}` : ''
              }`}
              tone="slate"
            />
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button className="btn-secondary" onClick={() => void load()}>
            Refresh
          </button>
          {record.state === 'NEEDS_REVIEW' ? (
            <Link
              className="btn-primary shadow-[0_0_25px_-3px_rgba(37,99,235,0.4)]"
              to={`/cases/${encodeURIComponent(record.email_id)}/review`}
            >
              Open Review Workspace
            </Link>
          ) : null}
        </div>
      </div>

      {/* Context Panel (Email & Attachments) */}
      <section className="glass-panel p-6">
        <details open className="group">
          <summary className="flex cursor-pointer items-center justify-between font-display text-base font-bold text-slate-900 dark:text-white">
            <span>Email & Attachment Context</span>
            <span className="font-mono text-xs text-slate-500 group-open:rotate-180 transition-transform">
              ▼
            </span>
          </summary>
          <div className="mt-5 grid gap-4 lg:grid-cols-3">
            <div>
              <div className="font-mono text-xs uppercase tracking-wider text-slate-600 dark:text-slate-400">
                Sender
              </div>
              <div className="mt-1 font-mono text-sm text-slate-900 dark:text-slate-200">
                {record.email.sender}
              </div>
            </div>
            <div className="lg:col-span-2">
              <div className="font-mono text-xs uppercase tracking-wider text-slate-600 dark:text-slate-400">
                Subject
              </div>
              <div className="mt-1 text-sm font-medium text-slate-900 dark:text-slate-200">
                {record.email.subject || '(No subject)'}
              </div>
            </div>
            <div className="lg:col-span-3">
              <div className="font-mono text-xs uppercase tracking-wider text-slate-600 dark:text-slate-400">
                Inbound Email Body
              </div>
              <pre className="mt-2 max-h-56 overflow-auto whitespace-pre-wrap rounded-xl border border-slate-200 dark:border-white/[0.06] bg-slate-50 dark:bg-carbon-950 p-4 font-mono text-xs text-slate-800 dark:text-slate-300 leading-relaxed">
                {record.email.body}
              </pre>
            </div>
          </div>

          <div className="mt-6 border-t border-slate-200 dark:border-white/[0.06] pt-5">
            <div className="font-mono text-xs uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-3">
              Attachment Ingestion & Parsers
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              {record.email.attachments.map((attachment) => {
                const parser = record.parsers.find(
                  (item) => item.document_id === attachment.document_id
                );
                return (
                  <div
                    key={attachment.document_id}
                    className="spotlight-border rounded-xl border border-slate-200 dark:border-white/[0.08] bg-slate-50 dark:bg-carbon-950/80 p-4"
                  >
                    <div className="font-mono text-xs font-semibold text-blue-700 dark:text-blue-300">
                      {attachment.document_id}
                    </div>
                    <div className="mt-1 font-mono text-xs text-slate-600 dark:text-slate-500">
                      {attachment.path}
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {parser ? (
                        <StatusBadge
                          label={String(parser.status)}
                          tone={parser.usable_for_extraction ? 'green' : 'amber'}
                        />
                      ) : (
                        <StatusBadge label="NOT PARSED" tone="slate" />
                      )}
                      {parser?.is_scanned ? (
                        <StatusBadge label="SCANNED" tone="blue" />
                      ) : null}
                      {parser?.page_count ? (
                        <StatusBadge
                          label={`${parser.page_count} page${
                            parser.page_count === 1 ? '' : 's'
                          }`}
                          tone="slate"
                        />
                      ) : null}
                    </div>
                  </div>
                );
              })}
              {record.email.attachments.length === 0 ? (
                <div className="text-sm text-slate-600 dark:text-slate-500">No attachments supplied.</div>
              ) : null}
            </div>
          </div>
        </details>
      </section>

      {/* Document Role Resolution Panel */}
      <section className="glass-panel p-6">
        <h2 className="font-display text-lg font-bold text-slate-900 dark:text-white">
          Document Role Resolution
        </h2>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          {(['SI', 'BL'] as const).map((role) => {
            const doc = record.documents.find((item) => item.role === role);
            return (
              <div
                key={role}
                className="spotlight-border rounded-xl border border-slate-200 dark:border-white/[0.08] bg-slate-50 dark:bg-carbon-950/80 p-5"
              >
                <div className="font-mono text-xs uppercase tracking-wider text-blue-700 dark:text-blue-400 font-semibold">
                  {role === 'SI' ? 'Shipping Instruction (SI)' : 'Draft Bill of Lading (BL)'}
                </div>
                <div className="mt-2 font-mono text-base font-bold text-slate-900 dark:text-white">
                  {doc?.document_id ?? 'Unresolved'}
                </div>
                {doc ? (
                  <div className="mt-2 font-mono text-xs text-slate-600 dark:text-slate-400">
                    Evidence ID:{' '}
                    <span className="text-slate-800 dark:text-slate-300 font-semibold">
                      {doc.identification_evidence_ids.join(', ') || '—'}
                    </span>
                  </div>
                ) : (
                  <div className="mt-2 text-xs text-amber-700 dark:text-amber-300 font-medium">
                    Document role has not been uniquely resolved.
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </section>

      {/* Dual-Axis Comparison Cinema Stage */}
      {record.classification.category === 'document_comparison' ? (
        <section className="space-y-4">
          <div className="flex flex-col justify-between gap-1 sm:flex-row sm:items-end">
            <div>
              <h2 className="font-display text-xl font-bold tracking-tight text-slate-900 dark:text-white">
                Deterministic 7-Field Cinema Stage
              </h2>
              <p className="mt-1 font-editorial italic text-xs text-slate-600 dark:text-slate-400">
                Deterministic 7-Field Cinema Stage · Source Integrity Guaranteed
              </p>
            </div>
          </div>
          <ComparisonMatrix
            record={record}
            onEvidence={(field, evidence) => setDrawer({ field, evidence })}
          />
        </section>
      ) : (
        <section className="glass-panel p-6">
          <h2 className="font-display text-lg font-bold text-slate-900 dark:text-white">
            Non-Comparison Case
          </h2>
          <p className="mt-2 text-sm text-slate-700 dark:text-slate-400">{record.result_summary}</p>
        </section>
      )}

      {/* Audit Lineage & Processing Metadata */}
      <section className="glass-panel p-6">
        <details className="group">
          <summary className="flex cursor-pointer items-center justify-between font-display text-base font-bold text-slate-900 dark:text-white">
            <span>Audit lineage & processing metadata</span>
            <span className="font-mono text-xs text-slate-500 group-open:rotate-180 transition-transform">
              ▼
            </span>
          </summary>
          <div className="mt-5 grid gap-4 text-xs text-slate-600 dark:text-slate-400 md:grid-cols-3">
            <div className="rounded-lg bg-slate-50 dark:bg-carbon-950 p-3 border border-slate-200 dark:border-white/[0.04]">
              Revision: <span className="font-mono font-bold text-slate-900 dark:text-white">r{record.revision}</span>
            </div>
            <div className="rounded-lg bg-slate-50 dark:bg-carbon-950 p-3 border border-slate-200 dark:border-white/[0.04]">
              Technical limit:{' '}
              <span className="font-mono font-bold text-slate-900 dark:text-white">
                {record.processing.technical_attempt_limit}
              </span>
            </div>
            <div className="rounded-lg bg-slate-50 dark:bg-carbon-950 p-3 border border-slate-200 dark:border-white/[0.04]">
              Semantic limit:{' '}
              <span className="font-mono font-bold text-slate-900 dark:text-white">
                {record.processing.semantic_attempt_limit}
              </span>
            </div>
          </div>
          <div className="mt-4 space-y-2">
            {record.processing.attempts.map((attempt) => (
              <div
                key={attempt.attempt_id}
                className="flex items-center justify-between rounded-lg border border-slate-200 dark:border-white/[0.04] bg-slate-50 dark:bg-carbon-950 p-3 font-mono text-xs"
              >
                <span className="text-blue-700 dark:text-blue-300 font-semibold">{attempt.attempt_id}</span>
                <span className="text-slate-600 dark:text-slate-400 font-medium">
                  {attempt.stage} · {attempt.kind} · {attempt.outcome}
                </span>
              </div>
            ))}
          </div>
        </details>
      </section>

      {/* Slide-out Source Evidence Drawer */}
      <EvidenceDrawer
        open={drawer !== null}
        field={drawer?.field ?? null}
        evidence={drawer?.evidence ?? []}
        onClose={() => setDrawer(null)}
      />
    </div>
  );
}
