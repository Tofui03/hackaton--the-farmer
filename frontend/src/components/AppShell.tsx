import { useEffect, useState, type ReactNode } from 'react';
import { Link, NavLink } from 'react-router-dom';

export function AppShell({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('sdoc-theme');
      return saved === 'dark' ? 'dark' : 'light';
    }
    return 'light';
  });

  useEffect(() => {
    if (typeof document !== 'undefined') {
      document.documentElement.classList.remove('light', 'dark');
      document.documentElement.classList.add(theme);
      document.documentElement.setAttribute('data-theme', theme);
      localStorage.setItem('sdoc-theme', theme);
    }
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-carbon-950 text-slate-900 dark:text-slate-100 font-sans selection:bg-klein selection:text-white antialiased transition-colors duration-200">
      {/* Floating Capsule Header */}
      <header className="sticky top-0 z-50 border-b border-slate-200/80 dark:border-white/[0.06] bg-white/90 dark:bg-carbon-950/80 backdrop-blur-md transition-all duration-300">
        <div className="mx-auto flex max-w-[1600px] items-center justify-between gap-4 px-4 py-3 sm:px-6">
          {/* Brand Logo & Editorial Typography */}
          <Link to="/cases" className="group flex items-center gap-3.5 focus:outline-none">
            <div className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-klein-glow via-klein to-blue-900 font-display text-sm font-extrabold tracking-wider text-white shadow-[0_0_20px_-2px_rgba(37,99,235,0.4)] ring-1 ring-white/20 transition-transform duration-300 group-hover:scale-105">
              SD
            </div>
            <div className="flex flex-col">
              <div className="flex items-center gap-2">
                <span className="font-display text-base font-bold tracking-tight text-slate-900 dark:text-white transition group-hover:text-blue-600 dark:group-hover:text-blue-100">
                  Shipping Document Verification
                </span>
                <span className="hidden font-editorial italic text-xs text-slate-500 dark:text-slate-400 sm:inline">
                  Console
                </span>
              </div>
              <span className="text-xs text-slate-500 dark:text-slate-400">
                Operational audit & human review console
              </span>
            </div>
          </Link>

          {/* Emerald Engine Live Pulse Badge */}
          <div className="hidden items-center gap-2 rounded-full border border-emerald-500/20 bg-emerald-50 dark:bg-emerald-950/30 px-3 py-1 text-xs md:flex">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500"></span>
            </span>
            <span className="font-mono text-[11px] font-medium tracking-wide text-emerald-700 dark:text-emerald-400 uppercase">
              Engine Live <span className="text-emerald-600/70 dark:text-emerald-500/60 font-sans">| 307 Tests Active</span>
            </span>
          </div>

          {/* Navigation Capsules & Theme Switcher */}
          <nav className="flex items-center gap-3">
            {/* Theme Toggle Button (Light Mode by Default) */}
            <button
              type="button"
              onClick={toggleTheme}
              aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
              title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
              className="flex items-center gap-1.5 rounded-xl border border-slate-200 dark:border-white/[0.08] bg-white dark:bg-carbon-900/60 px-3 py-1.5 text-xs font-semibold text-slate-700 dark:text-slate-300 shadow-sm transition hover:bg-slate-100 dark:hover:bg-carbon-800"
            >
              <span>{theme === 'dark' ? '🌙' : '☀️'}</span>
              <span className="hidden sm:inline font-mono">{theme === 'dark' ? 'Dark' : 'Light'}</span>
            </button>

            <div className="flex items-center rounded-xl border border-slate-200 dark:border-white/[0.06] bg-slate-100/80 dark:bg-carbon-900/60 p-1 backdrop-blur">
              <NavLink
                to="/cases"
                className={({ isActive }) =>
                  `group relative flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition duration-200 ${
                    isActive
                      ? 'bg-white dark:bg-white/10 text-slate-900 dark:text-white shadow-sm ring-1 ring-slate-200 dark:ring-white/10'
                      : 'text-slate-600 dark:text-slate-400 hover:bg-slate-200/60 dark:hover:bg-white/[0.04] hover:text-slate-900 dark:hover:text-white'
                  }`
                }
              >
                <span>Cases</span>
                <span className="hidden rounded bg-slate-200/80 dark:bg-carbon-950/80 px-1 py-0.5 font-mono text-[10px] text-slate-600 dark:text-slate-400 border border-slate-300 dark:border-white/[0.06] lg:inline">
                  ⌘1
                </span>
              </NavLink>
              <a
                href="/docs"
                className="group flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold text-slate-600 dark:text-slate-400 transition duration-200 hover:bg-slate-200/60 dark:hover:bg-white/[0.04] hover:text-slate-900 dark:hover:text-white"
              >
                <span>API Docs</span>
                <span className="hidden rounded bg-slate-200/80 dark:bg-carbon-950/80 px-1 py-0.5 font-mono text-[10px] text-slate-600 dark:text-slate-400 border border-slate-300 dark:border-white/[0.06] lg:inline">
                  ⌘2
                </span>
              </a>
            </div>

            {/* Keyboard Shortcuts Hint Pill */}
            <div className="hidden items-center gap-1.5 rounded-lg border border-slate-200 dark:border-white/[0.06] bg-white dark:bg-carbon-900/40 px-2.5 py-1.5 font-mono text-[11px] text-slate-600 dark:text-slate-400 xl:flex shadow-sm">
              <span className="rounded bg-slate-100 dark:bg-carbon-950 px-1.5 py-0.5 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-white/[0.06]">⌘K</span>
              <span>Search</span>
              <span className="mx-1 text-slate-300 dark:text-carbon-700">|</span>
              <span className="rounded bg-slate-100 dark:bg-carbon-950 px-1 py-0.5 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-white/[0.06]">J</span>
              <span className="rounded bg-slate-100 dark:bg-carbon-950 px-1 py-0.5 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-white/[0.06]">K</span>
              <span>Navigate</span>
            </div>
          </nav>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="mx-auto max-w-[1600px] px-4 py-8 sm:px-6">{children}</main>
    </div>
  );
}
