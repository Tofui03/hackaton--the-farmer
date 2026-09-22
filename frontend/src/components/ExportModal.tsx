import { Link } from 'react-router-dom';
import type { ErrorResponse } from '../types/api';

interface Props {
  open: boolean;
  blocked: ErrorResponse | null;
  onClose: () => void;
}

export function ExportModal({ open, blocked, onClose }: Props) {
  if (!open || !blocked) return null;
  const emails = blocked.blocking_emails ?? [];
  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/70 p-4" role="dialog" aria-modal="true" aria-label="Evaluation export blocked">
      <div className="w-full max-w-2xl rounded-xl border border-amber-700 bg-slate-950 p-6 shadow-2xl">
        <div className="text-xs font-semibold uppercase tracking-widest text-amber-400">Evaluation Export Blocked · DC-08</div>
        <h2 className="mt-2 text-xl font-bold text-white">Resolve all ambiguous cases before exporting.</h2>
        <p className="mt-3 text-sm text-slate-300">Official evaluation export requires complete, unambiguous records. The system will not guess missing defect or category values.</p>
        <div className="mt-5 rounded-lg border border-slate-800 bg-slate-900 p-4">
          <div className="text-sm font-semibold text-white">Cases requiring resolution: {emails.length}</div>
          <div className="mt-3 max-h-64 space-y-2 overflow-y-auto">
            {emails.map((emailId) => (
              <Link key={emailId} to={`/cases/${encodeURIComponent(emailId)}/review`} onClick={onClose} className="block rounded-md border border-slate-800 bg-slate-950 px-3 py-2 font-mono text-xs text-blue-300 hover:border-blue-600">
                {emailId} → Resolve in Review Workspace
              </Link>
            ))}
            {emails.length === 0 ? <div className="text-xs text-slate-500">{blocked.message}</div> : null}
          </div>
        </div>
        <div className="mt-6 flex justify-end"><button className="btn-secondary" onClick={onClose}>Close</button></div>
      </div>
    </div>
  );
}
