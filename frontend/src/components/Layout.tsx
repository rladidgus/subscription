import { NavLink, Outlet } from "react-router-dom";
import { Search, Sparkles } from "lucide-react";

const nav = [
  { to: "/", label: "공고탐색", icon: Search },
  { to: "/predict", label: "지원 판단", icon: Sparkles },
];

export default function Layout() {
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 border-b border-slate-200/80 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4 sm:px-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-600 text-white shadow-lg shadow-brand-600/20">
              <Sparkles size={20} />
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight">청약 가점 예측</h1>
              <p className="text-xs text-slate-500">실제 공고 기반 지원 판단 서비스</p>
            </div>
          </div>
          <nav className="hidden gap-1 md:flex">
            {nav.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                end={to === "/"}
                className={({ isActive }) =>
                  `flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition ${
                    isActive
                      ? "bg-brand-50 text-brand-700"
                      : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                  }`
                }
              >
                <Icon size={16} />
                {label}
              </NavLink>
            ))}
          </nav>
        </div>
        <nav className="flex gap-1 overflow-x-auto border-t border-slate-100 px-4 py-2 md:hidden">
          {nav.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `whitespace-nowrap rounded-lg px-3 py-1.5 text-xs font-medium ${
                  isActive ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-600"
                }`
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
        <Outlet />
      </main>
      <footer className="border-t border-slate-200 py-6 text-center text-xs text-slate-500">
        ApplyHome 공공데이터 기반 · LightGBM Hybrid · 참고용 예측
      </footer>
    </div>
  );
}
