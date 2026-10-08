interface Props {
  label: string;
  value: number;
  hint: string;
  glow?: 'blue' | 'rose' | 'emerald' | 'amber' | 'default';
}

const GLOW_CONFIG = {
  blue: {
    border: 'hover:border-blue-500/40',
    shadow: 'hover:shadow-[0_0_35px_-5px_rgba(37,99,235,0.3)]',
    indicator: 'bg-blue-500 shadow-[0_0_8px_rgba(37,99,235,0.8)]',
    blob: 'bg-blue-600/10',
  },
  rose: {
    border: 'hover:border-rose-500/40',
    shadow: 'hover:shadow-[0_0_35px_-5px_rgba(244,63,94,0.3)]',
    indicator: 'bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.8)]',
    blob: 'bg-rose-600/10',
  },
  emerald: {
    border: 'hover:border-emerald-500/40',
    shadow: 'hover:shadow-[0_0_35px_-5px_rgba(16,185,129,0.3)]',
    indicator: 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)]',
    blob: 'bg-emerald-600/10',
  },
  amber: {
    border: 'hover:border-amber-500/40',
    shadow: 'hover:shadow-[0_0_35px_-5px_rgba(245,158,11,0.3)]',
    indicator: 'bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.8)]',
    blob: 'bg-amber-600/10',
  },
  default: {
    border: 'hover:border-white/20',
    shadow: 'hover:shadow-[0_0_30px_-5px_rgba(255,255,255,0.06)]',
    indicator: 'bg-slate-400',
    blob: 'bg-white/5',
  },
};

export function KPICard({ label, value, hint, glow = 'default' }: Props) {
  const cfg = GLOW_CONFIG[glow] || GLOW_CONFIG.default;

  return (
    <div
      className={`spotlight-border group relative overflow-hidden rounded-2xl bg-white dark:bg-carbon-900/70 p-5 backdrop-blur-xl border border-slate-200/90 dark:border-white/[0.08] shadow-[0_4px_20px_-2px_rgba(15,23,42,0.06)] dark:shadow-none transition-all duration-300 hover:-translate-y-1 ${cfg.border} ${cfg.shadow}`}
    >
      {/* Background Soft Glow Blob */}
      <div
        className={`pointer-events-none absolute -right-6 -top-6 h-24 w-24 rounded-full blur-2xl transition duration-500 group-hover:scale-125 ${cfg.blob}`}
      />
      {/* Tiny Status Indicator Light */}
      <span className={`absolute right-4 top-4 h-1.5 w-1.5 rounded-full ${cfg.indicator}`} />

      {/* Label, Value, and Hint */}
      <div className="text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400 font-sans">
        {label}
      </div>
      <div className="mt-3 font-mono text-3xl font-bold tracking-tight text-slate-900 dark:text-white">
        {value}
      </div>
      <div className="mt-1 font-sans text-xs text-slate-500 dark:text-slate-400 font-medium">
        {hint}
      </div>
    </div>
  );
}
