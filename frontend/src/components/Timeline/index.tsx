import type { TimelineEvent } from "../../types";

const LABELS: Record<string, string> = {
  PERSON_ENTERED: "Person detected",
  PERSON_EXITED: "Person left camera",
  ZONE_ENTERED: "Entered zone",
  ZONE_EXITED: "Left zone",
  FACE_DETECTED: "Face detected",
  OBJECT_DETECTED: "Object detected",
  POSE_CHANGED: "Pose changed",
  VIEW_ANGLE_UPDATED: "View angle updated",
  SPEECH_DETECTED: "Speech detected",
  RECONSTRUCTION_UPDATED: "Reconstruction updated",
  CAMERA_STARTED: "Camera started",
  CAMERA_STOPPED: "Camera stopped",
  TRACKING_STARTED: "Tracking started",
  TRACKING_ENDED: "Tracking ended",
};

function fmt(ts: string) {
  return new Date(ts).toLocaleTimeString(undefined, { hour12: false });
}

export function Timeline({ events }: { events: TimelineEvent[] }) {
  return (
    <div className="panel h-full overflow-hidden">
      <div className="border-b border-line px-3 py-2 text-[11px] uppercase tracking-wider text-muted">Timeline</div>
      <div className="max-h-52 overflow-y-auto p-2">
        {events.length === 0 && <p className="px-2 py-6 text-center text-xs text-muted">No events yet</p>}
        {events.map((ev, i) => {
          const label = (ev.metadata?.label as string) || LABELS[ev.type] || ev.type;
          return (
            <div key={ev.id || `${ev.type}-${ev.timestamp}-${i}`} className="grid grid-cols-[88px_72px_1fr] gap-2 border-b border-line/60 px-2 py-1.5 text-xs">
              <span className="font-mono text-accent2">{fmt(ev.timestamp)}</span>
              <span className="font-mono text-muted">{ev.person_id || "—"}</span>
              <span>
                {label}
                {ev.demo ? <span className="ml-2 text-[10px] uppercase text-warn">demo</span> : null}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
