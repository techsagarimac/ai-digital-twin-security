import { Link } from "react-router-dom";
import type { PersonLive } from "../../types";

function Row({ label, value, conf }: { label: string; value: string; conf?: number }) {
  const unknown = !value || value === "UNKNOWN";
  return (
    <div className="flex items-baseline justify-between gap-2 text-xs">
      <span className="text-muted">{label}</span>
      <span className={unknown ? "text-muted" : "text-slate-100"}>
        {unknown ? "UNKNOWN" : value}
        {conf != null && !unknown ? <span className="ml-1 font-mono text-[10px] text-muted">{Math.round(conf * 100)}%</span> : null}
      </span>
    </div>
  );
}

function fmt(ts?: string) {
  if (!ts) return "—";
  const d = new Date(ts);
  return d.toLocaleTimeString(undefined, { hour12: false });
}

export function PersonCard({ person, selected, onSelect }: { person: PersonLive; selected?: boolean; onSelect?: () => void }) {
  const a = person.attributes || ({} as PersonLive["attributes"]);
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`panel w-full p-3 text-left transition ${selected ? "ring-1 ring-accent" : "hover:border-accent/40"}`}
    >
      <div className="mb-2 flex items-center justify-between">
        <Link to={`/people/${person.person_id}`} className="font-mono text-sm text-accent hover:underline" onClick={(e) => e.stopPropagation()}>
          {person.person_id}
        </Link>
        {(person.demo || person.simulated) && (
          <span className="rounded bg-warn/20 px-1.5 py-0.5 font-mono text-[9px] uppercase text-warn">Simulated</span>
        )}
      </div>
      <div className="space-y-1">
        <Row label="First seen" value={fmt(person.first_seen)} />
        <Row label="Last seen" value={fmt(person.last_seen)} />
        <Row label="Duration" value={person.duration_label} />
        <Row label="Hair" value={a.hair_color} conf={a.hair_confidence} />
        <Row label="Top" value={a.top_label || a.top_color} conf={a.top_confidence} />
        <Row label="Bottom" value={a.bottom_label || a.bottom_color} conf={a.bottom_confidence} />
        <Row label="Glasses" value={a.glasses} conf={a.glasses_confidence} />
        <Row label="Backpack" value={a.backpack} conf={a.backpack_confidence} />
        <Row label="3D coverage" value={`${Math.round(person.reconstruction_coverage || 0)}%`} />
        <Row label="Confidence" value={`${Math.round((person.confidence || 0) * 100)}%`} />
      </div>
    </button>
  );
}
