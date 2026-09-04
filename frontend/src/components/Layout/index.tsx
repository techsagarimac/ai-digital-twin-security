import type { ComponentProps, ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { Activity, Settings as Cog, LayoutDashboard } from "lucide-react";

export function TopStats({
  people,
  active,
  camera,
  fps,
  events,
  device,
  mic,
  demo,
}: {
  people: number;
  active: number;
  camera: string;
  fps: number;
  events: number;
  device: string;
  mic: string;
  demo: boolean;
}) {
  const items = [
    ["People detected", String(people)],
    ["Active people", String(active)],
    ["Camera", camera],
    ["FPS", fps.toFixed(1)],
    ["Events today", String(events)],
    ["Device", device],
    ["Microphone", mic],
  ];
  return (
    <header className="border-b border-line bg-[#080d18]">
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
        <div>
          <p className="text-[10px] uppercase tracking-[0.25em] text-accent">Operations</p>
          <h1 className="text-lg font-semibold">AI 3D Digital Twin Security Camera</h1>
        </div>
        <nav className="flex flex-wrap gap-1 text-sm">
          <NavLink to="/" className={navCls}>
            <LayoutDashboard size={14} /> Dashboard
          </NavLink>
          <NavLink to="/analytics" className={navCls}>
            <Activity size={14} /> Analytics
          </NavLink>
          <NavLink to="/settings" className={navCls}>
            <Cog size={14} /> Settings
          </NavLink>
        </nav>
      </div>
      {demo && (
        <div className="bg-warn/15 px-4 py-1 text-center font-mono text-[11px] uppercase tracking-widest text-warn">
          Demo mode — simulated detections are labeled and are not live AI output
        </div>
      )}
      <div className="grid grid-cols-2 gap-px border-t border-line bg-line sm:grid-cols-4 lg:grid-cols-7">
        {items.map(([k, v]) => (
          <div key={k} className="bg-panel px-3 py-2">
            <div className="text-[10px] uppercase tracking-wider text-muted">{k}</div>
            <div className="font-mono text-sm text-accent">{v}</div>
          </div>
        ))}
      </div>
    </header>
  );
}

function navCls({ isActive }: { isActive: boolean }) {
  return `flex items-center gap-1.5 rounded-md px-3 py-1.5 ${isActive ? "bg-accent/15 text-accent" : "text-muted hover:text-slate-100"}`;
}

export function LayoutShell({ children, stats }: { children: ReactNode; stats: ComponentProps<typeof TopStats> }) {
  return (
    <div className="min-h-screen">
      <TopStats {...stats} />
      <main className="p-4">{children}</main>
    </div>
  );
}
