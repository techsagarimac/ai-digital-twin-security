import { useEffect, useState } from "react";
import { api } from "../../services/api";
import type { AppSettings, Zone } from "../../types";

export function SettingsPanel() {
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [zones, setZones] = useState<Zone[]>([]);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    api.settings().then(setSettings).catch((e) => setMsg(String(e)));
    api.zones().then(setZones).catch(() => undefined);
  }, []);

  if (!settings) return <p className="text-muted">Loading settings…</p>;

  const save = async (patch: Partial<AppSettings>) => {
    const next = await api.saveSettings(patch);
    setSettings(next);
    setMsg("Saved");
  };

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="panel space-y-3 p-4">
        <h2 className="text-sm uppercase tracking-wider text-muted">Detection</h2>
        <label className="block text-xs text-muted">
          Detection confidence ({settings.detection_confidence})
          <input
            type="range"
            min={0.1}
            max={0.95}
            step={0.05}
            value={settings.detection_confidence}
            onChange={(e) => save({ detection_confidence: Number(e.target.value) })}
            className="w-full"
          />
        </label>
        <label className="block text-xs text-muted">
          Object confidence ({settings.object_confidence})
          <input
            type="range"
            min={0.1}
            max={0.95}
            step={0.05}
            value={settings.object_confidence}
            onChange={(e) => save({ object_confidence: Number(e.target.value) })}
            className="w-full"
          />
        </label>
        <label className="block text-xs text-muted">
          Tracking timeout (s)
          <input
            type="number"
            className="mt-1 w-full rounded border border-line bg-ink px-2 py-1"
            value={settings.tracking_timeout}
            onChange={(e) => save({ tracking_timeout: Number(e.target.value) })}
          />
        </label>
        <label className="block text-xs text-muted">
          Process every N frames
          <input
            type="number"
            className="mt-1 w-full rounded border border-line bg-ink px-2 py-1"
            value={settings.process_every_n_frames}
            onChange={(e) => save({ process_every_n_frames: Number(e.target.value) })}
          />
        </label>
        <label className="block text-xs text-muted">
          Data retention (days)
          <input
            type="number"
            className="mt-1 w-full rounded border border-line bg-ink px-2 py-1"
            value={settings.data_retention_days}
            onChange={(e) => save({ data_retention_days: Number(e.target.value) })}
          />
        </label>
      </div>
      <div className="panel space-y-3 p-4">
        <h2 className="text-sm uppercase tracking-wider text-muted">Privacy & audio</h2>
        <p className="font-mono text-xs">
          MICROPHONE:{" "}
          <span className={settings.microphone === "ON" ? "text-danger" : "text-accent"}>{settings.microphone}</span>
        </p>
        <p className="text-[11px] text-muted">
          The microphone never starts secretly. Enable only when you intend to capture speech in this session.
        </p>
        <button
          type="button"
          className="rounded border border-line px-3 py-1.5 text-sm hover:border-accent"
          onClick={() => save({ audio_enabled: !settings.audio_enabled })}
        >
          {settings.audio_enabled ? "Disable microphone" : "Enable microphone"}
        </button>
        <p className="text-xs text-muted">
          Identity module: {settings.identity_module_enabled ? "ON" : "OFF"} (off by default; no external face search).
        </p>
        <p className="text-xs text-warn">{msg}</p>
        <a className="block text-xs text-accent underline" href="/api/export/timeline.csv">
          Export timeline CSV
        </a>
        <a className="block text-xs text-accent underline" href="/api/export/events.json">
          Export events JSON
        </a>
        <a className="block text-xs text-accent underline" href="/api/export/analytics.csv">
          Export analytics CSV
        </a>
      </div>
      <div className="panel space-y-3 p-4 lg:col-span-2">
        <h2 className="text-sm uppercase tracking-wider text-muted">Camera zones (normalized 0–1)</h2>
        <div className="grid gap-3 md:grid-cols-3">
          {zones.map((z) => (
            <div key={z.id} className="rounded border border-line p-2 text-xs">
              <div className="font-medium" style={{ color: z.color }}>
                {z.name}
              </div>
              <div className="font-mono text-muted">
                {z.x1.toFixed(2)},{z.y1.toFixed(2)} → {z.x2.toFixed(2)},{z.y2.toFixed(2)}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
