import type { DetectedObject } from "../../types";

export function ObjectPanel({ objects }: { objects?: DetectedObject[] }) {
  return (
    <div className="panel p-3">
      <h3 className="mb-2 text-[11px] uppercase tracking-wider text-muted">Detected objects</h3>
      {!objects?.length && <p className="text-xs text-muted">None above threshold</p>}
      <ul className="space-y-1 text-xs">
        {objects?.map((o, i) => (
          <li key={`${o.object}-${i}`} className="flex justify-between font-mono">
            <span>{o.object}</span>
            <span className="text-accent">{Math.round(o.confidence * 100)}%</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
