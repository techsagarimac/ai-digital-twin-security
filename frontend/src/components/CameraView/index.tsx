import { useEffect, useRef } from "react";
import type { PersonLive, Zone } from "../../types";

type Props = {
  jpeg?: string;
  people: PersonLive[];
  width?: number;
  height?: number;
  fps?: number;
  demo?: boolean;
  zones?: Zone[];
};

export function CameraView({ jpeg, people, width = 960, height = 540, fps = 0, demo, zones = [] }: Props) {
  const imgRef = useRef<HTMLImageElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const img = imgRef.current;
    if (!canvas || !img || !jpeg) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const draw = () => {
      canvas.width = img.naturalWidth || width;
      canvas.height = img.naturalHeight || height;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const sx = canvas.width;
      const sy = canvas.height;
      ctx.strokeStyle = "rgba(62,224,197,0.25)";
      ctx.lineWidth = 1;
      zones.forEach((z) => {
        ctx.strokeRect(z.x1 * sx, z.y1 * sy, (z.x2 - z.x1) * sx, (z.y2 - z.y1) * sy);
        ctx.fillStyle = "rgba(110,168,254,0.55)";
        ctx.font = "11px IBM Plex Mono";
        ctx.fillText(z.name, z.x1 * sx + 6, z.y1 * sy + 14);
      });
      people.forEach((p) => {
        const [x1, y1, x2, y2] = p.bbox;
        ctx.strokeStyle = p.simulated ? "#f5a524" : "#3ee0c5";
        ctx.lineWidth = 2;
        ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
        ctx.fillStyle = p.simulated ? "rgba(245,165,36,0.85)" : "rgba(13,21,36,0.85)";
        ctx.fillRect(x1, Math.max(0, y1 - 36), 148, 34);
        ctx.fillStyle = "#e8eef7";
        ctx.font = "12px IBM Plex Mono";
        ctx.fillText(`${p.person_id}  ${Math.round(p.confidence * 100)}%`, x1 + 6, y1 - 18);
        ctx.fillStyle = "#8ba0b5";
        ctx.fillText(p.zone_name || p.zone_id || "no zone", x1 + 6, y1 - 6);
        if (p.pose_landmarks?.length) {
          ctx.strokeStyle = "rgba(110,168,254,0.9)";
          ctx.lineWidth = 2;
          const byId = new Map(p.pose_landmarks.map((l) => [l.id, l]));
          const edges = [
            [5, 6], [5, 7], [7, 9], [6, 8], [8, 10], [5, 11], [6, 12], [11, 12], [11, 13], [13, 15], [12, 14], [14, 16],
          ];
          edges.forEach(([a, b]) => {
            const pa = byId.get(a);
            const pb = byId.get(b);
            if (!pa || !pb) return;
            ctx.beginPath();
            ctx.moveTo(pa.x, pa.y);
            ctx.lineTo(pb.x, pb.y);
            ctx.stroke();
          });
        }
        ctx.fillStyle = "#3ee0c5";
        p.face_landmarks?.forEach((lm) => {
          ctx.beginPath();
          ctx.arc(lm.x, lm.y, 1.6, 0, Math.PI * 2);
          ctx.fill();
        });
        p.objects?.forEach((obj) => {
          const [ox1, oy1, ox2, oy2] = obj.bbox;
          ctx.strokeStyle = "#f5a524";
          ctx.strokeRect(ox1, oy1, ox2 - ox1, oy2 - oy1);
          ctx.fillStyle = "#f5a524";
          ctx.font = "10px IBM Plex Mono";
          ctx.fillText(`${obj.object} ${Math.round(obj.confidence * 100)}%`, ox1, oy1 - 4);
        });
        const badges: string[] = [];
        if (p.attributes?.glasses === "Detected") badges.push("Glasses ✓");
        if (p.attributes?.backpack === "Detected") badges.push("Backpack ✓");
        badges.forEach((b, i) => {
          ctx.fillStyle = "rgba(62,224,197,0.15)";
          ctx.fillRect(x1, y2 + 4 + i * 16, 92, 14);
          ctx.fillStyle = "#3ee0c5";
          ctx.font = "10px IBM Plex Mono";
          ctx.fillText(b, x1 + 4, y2 + 14 + i * 16);
        });
      });
    };
    if (img.complete) draw();
    else img.onload = draw;
  }, [jpeg, people, width, height, zones]);

  return (
    <div className="panel relative overflow-hidden">
      <div className="flex items-center justify-between border-b border-line px-3 py-2 text-[11px] uppercase tracking-wider text-muted">
        <span>Live camera — actual image</span>
        <span className="font-mono text-accent">
          {fps.toFixed(1)} FPS {demo ? "· DEMO" : ""}
        </span>
      </div>
      <div className="relative bg-black scanlines">
        {jpeg ? (
          <>
            <img
              ref={imgRef}
              src={`data:image/jpeg;base64,${jpeg}`}
              alt="Live camera"
              className="block w-full"
            />
            <canvas ref={canvasRef} className="absolute inset-0 h-full w-full" />
          </>
        ) : (
          <div className="flex h-64 items-center justify-center text-sm text-muted">
            Camera idle — start webcam, upload video, or Demo Mode
          </div>
        )}
        {demo && (
          <div className="absolute left-3 top-3 rounded bg-warn/90 px-2 py-1 font-mono text-[10px] font-semibold uppercase text-ink">
            Simulated detections
          </div>
        )}
      </div>
    </div>
  );
}
