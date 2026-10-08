import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ApiError, getSubmission, listAudits } from '../api/client';
import { ExportModal } from '../components/ExportModal';
import { KPICard } from '../components/KPICard';
import { OutcomeBadge } from '../components/OutcomeBadge';
import { StatusBadge } from '../components/StatusBadge';
import type { AuditRecord, ErrorResponse } from '../types/api';

function downloadJson(data: unknown, filename: string) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export function CaseQueueView() {
  const [records, setRecords] = useState<AuditRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [stateFilter, setStateFilter] = useState('ALL');
  const [outcomeFilter, setOutcomeFilter] = useState('ALL');
  const [categoryFilter, setCategoryFilter] = useState('ALL');
  const [blocked, setBlocked] = useState<ErrorResponse | null>(null);
  const [exporting, setExporting] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setRecords(await listAudits());
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Unable to load cases');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const metrics = useMemo(
    () => ({
      total: records.length,
      complete: records.filter((r) => r.state === 'COMPLETE').length,
      review: records.filter((r) => r.state === 'NEEDS_REVIEW').length,
      mismatch: records.filter((r) => r.state === 'COMPLETE' && r.outcome === 'MISMATCH').length,
      match: records.filter((r) => r.state === 'COMPLETE' && r.outcome === 'MATCH').length,
      nonComparison: records.filter((r) => r.outcome === 'NOT_APPLICABLE').length,
    }),
    [records]
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return records.filter((r) => {
      if (stateFilter !== 'ALL' && r.state !== stateFilter) return false;
      if (outcomeFilter !== 'ALL' && r.outcome !== outcomeFilter) return false;
      if (categoryFilter === 'UNRESOLVED' && r.classification.category !== null) return false;
      if (
        categoryFilter !== 'ALL' &&
        categoryFilter !== 'UNRESOLVED' &&
        r.classification.category !== categoryFilter
      ) {
        return false;
      }
      if (!q) return true;
      return [
        r.email_id,
        r.email.sender,
        r.email.subject,
        r.classification.category ?? 'unresolved',
        r.result_summary,
      ].some((value) => value.toLowerCase().includes(q));
    });
  }, [records, query, stateFilter, outcomeFilter, categoryFilter]);

  const exportSubmission = async () => {
    setExporting(true);
    try {
      const submission = await getSubmission();
      downloadJson(submission, 'submission.json');
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 409 && cause.payload?.code === 'EXPORT_BLOCKED') {
        setBlocked(cause.payload);
      } else {
        setError(cause instanceof Error ? cause.message : 'Export failed');
      }
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Hero Header Section */}
      <div className="flex flex-col justify-between gap-6 lg:flex-row lg:items-end">
        <div>
          <div className="font-mono text-xs font-semibold uppercase tracking-[0.25em] text-blue-400">
            Operations Control · Data Horizon
          </div>
          <h1 className="mt-1 font-display text-3xl font-extrabold tracking-tight text-white sm:text-4xl">
            Verification Cases
          </h1>
          <p className="mt-2 text-sm text-slate-400">
            Live operational telemetry synthesized across inbound shipping document verification pipelines.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button className="btn-secondary" onClick={() => void load()}>
            Refresh
          </button>
          <button
            className="btn-primary shadow-[0_0_25px_-3px_rgba(37,99,235,0.4)]"
            disabled={exporting}
            onClick={() => void exportSubmission()}
          >
            {exporting ? 'Checking export…' : 'Export Official Submission'}
          </button>
        </div>
      </div>

      {/* Data Horizon Metrics Grid */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        <KPICard label="Total" value={metrics.total} hint="Loaded cases" glow="blue" />
        <KPICard label="Complete" value={metrics.complete} hint="Resolved workflow" glow="default" />
        <KPICard label="Needs Review" value={metrics.review} hint="Operator action required" glow="amber" />
        <KPICard label="Mismatches" value={metrics.mismatch} hint="Confirmed discrepancies" glow="rose" />
        <KPICard label="Clean Matches" value={metrics.match} hint="All 7 fields matched" glow="emerald" />
        <KPICard label="Non-Comparison" value={metrics.nonComparison} hint="Verification not applicable" glow="default" />
      </div>

      {/* Floating Filter Dock */}
      <div className="glass-panel grid gap-3 p-4 md:grid-cols-4">
        <div className="relative">
          <input
            className="input pr-12 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            aria-label="Search cases"
            placeholder="Search email ID, sender, subject…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <div className="pointer-events-none absolute inset-y-0 right-3 flex items-center">
            <span className="rounded border border-white/[0.08] bg-carbon-950 px-1.5 py-0.5 font-mono text-[10px] text-slate-400">
              ⌘K
            </span>
          </div>
        </div>

        <select
          className="input focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
          aria-label="Category filter"
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
        >
          <option value="ALL">All categories</option>
          <option value="document_comparison">document_comparison</option>
          <option value="new_shipping_instruction">new_shipping_instruction</option>
          <option value="invoice_query">invoice_query</option>
          <option value="general">general</option>
          <option value="spam">spam</option>
          <option value="UNRESOLVED">Unresolved Intent</option>
        </select>

        <select
          className="input focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
          aria-label="State filter"
          value={stateFilter}
          onChange={(e) => setStateFilter(e.target.value)}
        >
          <option value="ALL">All states</option>
          <option value="COMPLETE">COMPLETE</option>
          <option value="NEEDS_REVIEW">NEEDS_REVIEW</option>
        </select>

        <select
          className="input focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
          aria-label="Outcome filter"
          value={outcomeFilter}
          onChange={(e) => setOutcomeFilter(e.target.value)}
        >
          <option value="ALL">All outcomes</option>
          <option value="MATCH">MATCH</option>
          <option value="MISMATCH">MISMATCH</option>
          <option value="NOT_APPLICABLE">NOT_APPLICABLE</option>
        </select>
      </div>

      {/* Error Feedback */}
      {error && (
        <div className="glass-panel border-rose-500/30 bg-rose-950/20 p-4 text-sm text-rose-300">
          {error}
        </div>
      )}

      {/* Cinematic Audit Rows */}
      {loading ? (
        <div className="glass-panel animate-pulse p-12 text-center text-sm text-slate-400">
          Loading case queue telemetry…
        </div>
      ) : filtered.length === 0 ? (
        <div className="glass-panel p-12 text-center text-sm text-slate-400">
          No cases match the current filter criteria.
        </div>
      ) : (
        <div className="glass-panel overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-white/[0.06] bg-carbon-950/80 font-mono text-xs uppercase tracking-wider text-slate-400">
                <tr>
                  <th className="px-5 py-3.5">Email ID</th>
                  <th className="px-5 py-3.5">Subject / Sender</th>
                  <th className="px-5 py-3.5">Category</th>
                  <th className="px-5 py-3.5">State</th>
                  <th className="px-5 py-3.5">Outcome</th>
                  <th className="px-5 py-3.5">Summary</th>
                  <th className="px-5 py-3.5">Revision</th>
                  <th className="px-5 py-3.5 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {filtered.map((record) => (
                  <tr
                    key={record.email_id}
                    className="group transition duration-150 hover:bg-carbon-800/40 hover:shadow-[inset_2px_0_0_0_#2563eb]"
                  >
                    <td className="px-5 py-4 font-mono text-xs">
                      <Link
                        to={`/cases/${encodeURIComponent(record.email_id)}`}
                        className="font-bold text-white transition hover:text-blue-300"
                      >
                        {record.email_id}
                      </Link>
                    </td>
                    <td className="max-w-xs px-5 py-4">
                      <div className="font-medium text-slate-100 transition group-hover:text-white">
                        {record.email.subject || '(No subject)'}
                      </div>
                      <div className="mt-1 font-mono text-xs text-slate-400">
                        {record.email.sender}
                      </div>
                    </td>
                    <td className="px-5 py-4">
                      {record.classification.category ? (
                        <StatusBadge label={record.classification.category} tone="blue" />
                      ) : (
                        <StatusBadge label="Unresolved Classification" tone="amber" icon="◷" />
                      )}
                    </td>
                    <td className="px-5 py-4">
                      <StatusBadge
                        label={record.state}
                        tone={record.state === 'NEEDS_REVIEW' ? 'amber' : 'slate'}
                        icon={record.state === 'NEEDS_REVIEW' ? '◷' : '✓'}
                      />
                    </td>
                    <td className="px-5 py-4">
                      <OutcomeBadge record={record} />
                    </td>
                    <td className="max-w-sm px-5 py-4 text-xs text-slate-400 leading-relaxed">
                      {record.result_summary}
                    </td>
                    <td className="px-5 py-4 font-mono text-xs text-slate-400">
                      r{record.revision}
                    </td>
                    <td className="px-5 py-4 text-right">
                      <Link
                        className={record.state === 'NEEDS_REVIEW' ? 'btn-primary' : 'btn-secondary'}
                        to={
                          record.state === 'NEEDS_REVIEW'
                            ? `/cases/${encodeURIComponent(record.email_id)}/review`
                            : `/cases/${encodeURIComponent(record.email_id)}`
                        }
                      >
                        {record.state === 'NEEDS_REVIEW' ? 'Review Case' : 'Inspect'}
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Export Interception Modal */}
      <ExportModal open={blocked !== null} blocked={blocked} onClose={() => setBlocked(null)} />
    </div>
  );
}
