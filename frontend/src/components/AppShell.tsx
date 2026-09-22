import type { ReactNode } from 'react';
import { Link, NavLink } from 'react-router-dom';

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="sticky top-0 z-40 border-b border-slate-800 bg-slate-950/95 backdrop-blur">
        <div className="mx-auto flex max-w-[1600px] items-center justify-between gap-4 px-4 py-3 lg:px-6">
          <Link to="/cases" className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600 font-bold text-white">SD</div>
            <div>
              <div className="font-bold tracking-tight text-white">Shipping Document Verification</div>
              <div className="text-xs text-slate-500">Operational audit & human review console</div>
            </div>
          </Link>
          <nav className="flex items-center gap-2 text-sm">
            <NavLink to="/cases" className={({ isActive }) => isActive ? 'rounded-lg bg-slate-800 px-3 py-2 font-semibold text-white' : 'rounded-lg px-3 py-2 text-slate-400 hover:text-white'}>Cases</NavLink>
            <a href="/docs" className="rounded-lg px-3 py-2 text-slate-400 hover:text-white">API Docs</a>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-[1600px] px-4 py-6 lg:px-6">{children}</main>
    </div>
  );
}
