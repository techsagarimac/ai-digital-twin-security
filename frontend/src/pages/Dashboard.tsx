import { useEffect, useMemo, useState } from "react";
import { CameraView } from "../components/CameraView";
import { DigitalTwin, type TwinMode } from "../components/DigitalTwin";
import { PersonCard } from "../components/PersonCard";
import { Timeline } from "../components/Timeline";
import { useLive } from "../context/LiveContext";
import { useBrowserCamera } from "../hooks/useBrowserCamera";
import { api } from "../services/api";
import type { Zone } from "../types";

const MODES: { id: TwinMode; label: string }[] = [
  { id: "solid", label: "Mesh" },
  { id: "wireframe", label: "Wireframe" },
  { id: "landmarks", label: "Landmarks" },
  { id: "skeleton", label: "Skeleton" },
  { id: "xray", label: "X-Ray View" },
];

export function Dashboard() {
  const { frame, people, events, recon, selectedId, setSelectedId, connected } = useLive();
  const [zones, setZones] = useState<Zone[]>([]);
  const [busy, setBusy] = useState("");
  const [mode, setMode] = useState<TwinMode>("xray");
  const browserCam = useBrowserCamera();

  useEffect(() => {
    api.zones().then(setZones).catch(() => undefined);
  }, []);

  const selected = useMemo(
    () => people.find((p) => p.person_id === selectedId) || people[0],
    [people, selectedId],
  );
  const twin = selected ? recon[selected.person_id] : undefined;

  const start = async (source: string, extra: Record<string, unknown> = {}) => {
    setBusy("Starting…");
    browserCam.stop();
    try {
      if (source === "webcam") {
        await api.startCamera({ source: "browser", demo_mode: false });
        try {
          await browserCam.start();
          setBusy("Look at the camera — face scan is live");
          return;
        } catch (err) {
          browserCam.stop();
          setBusy("Browser camera blocked — trying system webcam");
          await api.startCamera({ source: "webcam", demo_mode: false });
          setBusy("");
          return;
        }
      }
      await api.startCamera({ source, ...extra });
      setBusy("");
    } catch (e) {
      setBusy(String(e));
    }
  };

  const stop = async () => {
    browserCam.stop();
    await api.stopCamera();
    setBusy("");
  };

  const onUpload = async (file: File | undefined) => {
    if (!file) return;
    setBusy("Uploading…");
    try {
      const up = await api.uploadVideo(file);
      await api.startCamera({ source: "video", video_path: up.path, demo_mode: false });
      setBusy("");
    } catch (e) {
      setBusy(String(e));
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <button className="rounded border border-line px-3 py-1.5 text-sm hover:border-accent" onClick={() => start("webcam")}>
          Start webcam
        </button>
        <button className="rounded border border-warn/50 px-3 py-1.5 text-sm text-warn hover:border-warn" onClick={() => start("demo", { demo_mode: true })}>
          Demo mode
        </button>
        <label className="cursor-pointer rounded border border-line px-3 py-1.5 text-sm hover:border-accent">
          Upload video
          <input type="file" accept="video/*" className="hidden" onChange={(e) => onUpload(e.target.files?.[0])} />
        </label>
        <button className="rounded border border-line px-3 py-1.5 text-sm" onClick={() => void stop()}>
          Stop
        </button>
        <span className="font-mono text-[11px] text-muted">{connected ? "LIVE WS" : "WS DISCONNECTED"} {busy}</span>
      </div>

      <div className="flex flex-wrap gap-2">
        {MODES.map((m) => (
          <button
            key={m.id}
            type="button"
            onClick={() => setMode(m.id)}
            className={`rounded px-3 py-1 text-[11px] uppercase tracking-wider ${mode === m.id ? "bg-accent/20 text-accent" : "border border-line text-muted"}`}
          >
            {m.label}
          </button>
        ))}
      </div>

      <div className="grid items-stretch gap-4 xl:grid-cols-12">
        <div className="xl:col-span-4">
          <CameraView
            jpeg={frame?.jpeg_base64}
            people={people}
            fps={frame?.fps}
            demo={frame?.demo_mode}
            width={frame?.width}
            height={frame?.height}
            zones={zones}
          />
          {selected && (
            <div className="mt-3 panel p-3 text-xs">
              <div className="mb-1 text-[11px] uppercase text-muted">Head orientation</div>
              <div className="font-mono text-accent">
                Yaw {fmtDeg(selected.yaw)} · Pitch {fmtDeg(selected.pitch)} · Roll {fmtDeg(selected.roll)}
              </div>
              <div className="mt-2 h-16 w-16 rounded-full border border-line relative">
                <div
                  className="absolute left-1/2 top-1/2 h-6 w-0.5 origin-bottom bg-accent"
                  style={{ transform: `translate(-50%, -100%) rotate(${selected.yaw || 0}deg)` }}
                />
              </div>
              <p className="mt-2 text-[10px] text-muted">{selected.orientation}</p>
            </div>
          )}
        </div>
        <div className="xl:col-span-5">
          <DigitalTwin reconstruction={twin} mode={mode} />
        </div>
        <div className="flex max-h-[640px] flex-col gap-3 overflow-y-auto xl:col-span-3">
          {people.length === 0 && <p className="panel p-4 text-sm text-muted">No people in view</p>}
          {people.map((p) => (
            <PersonCard
              key={p.person_id}
              person={p}
              selected={selected?.person_id === p.person_id}
              onSelect={() => setSelectedId(p.person_id)}
            />
          ))}
        </div>
      </div>
      <Timeline events={events} />
      {frame?.model_status?.messages?.length ? (
        <ul className="text-xs text-warn">
          {frame.model_status.messages.map((m) => (
            <li key={m}>{m}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

function fmtDeg(v?: number | null) {
  if (v == null || Number.isNaN(v)) return "—";
  const sign = v > 0 ? "+" : "";
  return `${sign}${v.toFixed(0)}°`;
}
