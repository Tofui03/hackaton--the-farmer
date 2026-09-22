interface Props {
  open: boolean;
  message: string;
  onReload: () => void;
  onReviewDifferences: () => void;
  onClose: () => void;
}

export function ConflictModal({ open, message, onReload, onReviewDifferences, onClose }: Props) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/70 p-4" role="alertdialog" aria-modal="true" aria-label="Revision conflict">
      <div className="w-full max-w-lg rounded-xl border border-amber-700 bg-slate-950 p-6 shadow-2xl">
        <div className="text-xs font-semibold uppercase tracking-widest text-amber-400">Revision Conflict Detected</div>
        <h2 className="mt-2 text-xl font-bold text-white">Another operator saved changes first.</h2>
        <p className="mt-3 text-sm text-slate-300">{message}</p>
        <p className="mt-2 text-xs text-slate-500">Your unsubmitted form values are still preserved in this browser session.</p>
        <div className="mt-6 flex flex-wrap justify-end gap-2">
          <button className="btn-secondary" onClick={onClose}>Keep Editing</button>
          <button className="btn-secondary" onClick={onReviewDifferences}>Review Differences</button>
          <button className="btn-primary" onClick={onReload}>Reload Latest Server Version</button>
        </div>
      </div>
    </div>
  );
}
