import type { Attributes } from "../../types";

export function AttributePanel({ attributes }: { attributes?: Attributes }) {
  const a = attributes;
  const rows = [
    ["Hair presence", a?.hair_presence, a?.hair_confidence],
    ["Hair colour", a?.hair_color, a?.hair_confidence],
    ["Hairstyle", a?.hair_style, a?.hair_confidence],
    ["Hair length", a?.hair_length, a?.hair_confidence],
    ["Top", a?.top_label, a?.top_confidence],
    ["Bottom", a?.bottom_label, a?.bottom_confidence],
    ["Shoes", a?.shoes_label, a?.shoes_confidence],
  ] as const;
  return (
    <div className="panel p-3">
      <h3 className="mb-2 text-[11px] uppercase tracking-wider text-muted">Visible attributes</h3>
      <p className="mb-3 text-[10px] text-muted">Predictions below the confidence threshold are shown as UNKNOWN. No health, race, or emotion inference.</p>
      <div className="space-y-1.5 text-xs">
        {rows.map(([label, value, conf]) => (
          <div key={label} className="flex justify-between">
            <span className="text-muted">{label}</span>
            <span>
              {value && value !== "UNKNOWN" ? value : "UNKNOWN"}
              {conf && value && value !== "UNKNOWN" ? <span className="ml-1 font-mono text-muted">{Math.round(conf * 100)}%</span> : null}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
