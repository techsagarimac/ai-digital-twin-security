import { useEffect, useState } from "react";
import { AnalyticsCharts } from "../components/Analytics";
import { api } from "../services/api";
import type { Analytics } from "../types";

export function AnalyticsPage() {
  const [data, setData] = useState<Analytics | null>(null);
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<{ type: string; person_id?: string | null; timestamp: string }[]>([]);

  useEffect(() => {
    api.analytics().then(setData).catch(() => undefined);
  }, []);

  const search = async () => {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    const rows = await api.search(params);
    setHits(rows.slice(0, 40));
  };

  if (!data) return <p className="text-muted">Loading analytics…</p>;

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-4">
        <Stat label="People detected" value={data.people_detected} />
        <Stat label="Avg dwell (s)" value={data.average_dwell_seconds} />
        <Stat label="Speech events" value={data.speech_event_count} />
        <Stat label="Events today" value={data.events_today} />
      </div>
      <div className="panel flex flex-wrap gap-2 p-3">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search P001, zone, event type…"
          className="min-w-[220px] flex-1 rounded border border-line bg-ink px-3 py-1.5 text-sm"
        />
        <button type="button" onClick={search} className="rounded border border-line px-3 py-1.5 text-sm hover:border-accent">
          Search
        </button>
      </div>
      {hits.length > 0 && (
        <div className="panel max-h-48 overflow-auto p-2 text-xs">
          {hits.map((h, i) => (
            <div key={i} className="grid grid-cols-[160px_80px_1fr] gap-2 border-b border-line/50 py-1 font-mono">
              <span>{new Date(h.timestamp).toLocaleString()}</span>
              <span>{h.person_id}</span>
              <span>{h.type}</span>
            </div>
          ))}
        </div>
      )}
      <AnalyticsCharts data={data} />
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="panel p-3">
      <div className="text-[10px] uppercase text-muted">{label}</div>
      <div className="font-mono text-xl text-accent">{value}</div>
    </div>
  );
}
