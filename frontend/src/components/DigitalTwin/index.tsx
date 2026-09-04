import { Canvas, useThree } from "@react-three/fiber";
import { OrbitControls, Line } from "@react-three/drei";
import { useMemo } from "react";
import * as THREE from "three";
import type { Reconstruction } from "../../types";

export type TwinMode = "solid" | "wireframe" | "xray" | "landmarks" | "skeleton";

type Props = {
  reconstruction?: Reconstruction | null;
  mode: TwinMode;
};

type Vec = [number, number, number];

function normalize(recon: Reconstruction | null | undefined): { joints: Map<number, Vec>; face: Vec[] } {
  const pose = recon?.pose_landmarks || [];
  const joints = new Map<number, Vec>();
  if (!pose.length) return { joints, face: [] };
  const get = (id: number) => pose.find((p) => p.id === id);
  const hipL = get(23) || get(11);
  const hipR = get(24) || get(12);
  const shL = get(11) || get(5);
  const shR = get(12) || get(6);
  const originX = hipL && hipR ? (hipL.x + hipR.x) / 2 : pose[0].x;
  const originY = hipL && hipR ? (hipL.y + hipR.y) / 2 : pose[0].y;
  const span = shL && shR ? Math.max(Math.hypot(shR.x - shL.x, shR.y - shL.y), 40) : 80;
  pose.forEach((p) => {
    joints.set(p.id, [(p.x - originX) / span, -(p.y - originY) / span, (p.z || 0) * 2]);
  });
  const face: Vec[] = (recon?.face_landmarks || []).map((p) => [
    (p.x - originX) / span,
    -(p.y - originY) / span,
    0.15 + (p.z || 0),
  ]);
  return { joints, face };
}

function Figure({ reconstruction, mode }: Props) {
  const { joints, face } = useMemo(() => normalize(reconstruction), [reconstruction]);
  const edges = reconstruction?.skeleton_edges?.length
    ? reconstruction.skeleton_edges
    : [
        [5, 6], [5, 7], [7, 9], [6, 8], [8, 10], [5, 11], [6, 12], [11, 12], [11, 13], [13, 15], [12, 14], [14, 16],
      ];
  const points = [...joints.values()];
  const color = mode === "xray" ? "#7ef0ff" : "#3ee0c5";
  const transparent = mode === "xray" || mode === "wireframe";
  const showMesh = mode === "solid" || mode === "wireframe" || mode === "xray";
  const showSkel = mode === "skeleton" || mode === "xray" || mode === "solid";
  const showLm = mode === "landmarks" || mode === "xray";

  const torso = joints.get(11) && joints.get(12) && joints.get(5) && joints.get(6);

  return (
    <group>
      {showMesh && torso && (
        <mesh position={[0, 0.35, 0]}>
          <capsuleGeometry args={[0.28, 0.85, 6, 12]} />
          <meshStandardMaterial
            color={color}
            wireframe={mode === "wireframe"}
            transparent={transparent}
            opacity={mode === "xray" ? 0.22 : mode === "wireframe" ? 1 : 0.85}
            roughness={0.35}
            metalness={0.1}
          />
        </mesh>
      )}
      {showMesh && joints.get(0) && (
        <mesh position={joints.get(0)}>
          <sphereGeometry args={[0.16, 16, 16]} />
          <meshStandardMaterial
            color={color}
            wireframe={mode === "wireframe"}
            transparent={transparent}
            opacity={mode === "xray" ? 0.28 : 0.9}
          />
        </mesh>
      )}
      {showSkel &&
        edges.map(([a, b], i) => {
          const pa = joints.get(a);
          const pb = joints.get(b);
          if (!pa || !pb) return null;
          return <Line key={i} points={[pa, pb]} color={color} lineWidth={1.5} />;
        })}
      {showLm &&
        points.map((p, i) => (
          <mesh key={`j${i}`} position={p}>
            <sphereGeometry args={[0.035, 8, 8]} />
            <meshBasicMaterial color="#e8eef7" />
          </mesh>
        ))}
      {showLm &&
        face.map((p, i) => (
          <mesh key={`f${i}`} position={p}>
            <sphereGeometry args={[0.018, 6, 6]} />
            <meshBasicMaterial color="#6ea8fe" />
          </mesh>
        ))}
      {(reconstruction?.objects || []).map((obj, i) => (
        <mesh key={obj.object + i} position={[0.45, obj.object === "backpack" ? 0.4 : 0.7, obj.object === "backpack" ? -0.25 : 0.2]}>
          <boxGeometry args={[0.12, 0.16, 0.08]} />
          <meshStandardMaterial color="#f5a524" transparent opacity={0.8} />
        </mesh>
      ))}
    </group>
  );
}

function ResetButton({ onReset }: { onReset: () => void }) {
  return (
    <button type="button" className="rounded border border-line px-2 py-1 text-[11px] uppercase text-muted hover:text-accent" onClick={onReset}>
      Reset
    </button>
  );
}

function ControlsBinder({ resetRef }: { resetRef: { current: (() => void) | null } }) {
  const { camera } = useThree();
  resetRef.current = () => {
    camera.position.set(0, 0.4, 3.2);
    camera.lookAt(0, 0.4, 0);
  };
  return (
    <OrbitControls enablePan enableRotate enableZoom makeDefault minDistance={1.2} maxDistance={8} />
  );
}

export function DigitalTwin({ reconstruction, mode }: Props) {
  const resetRef = useMemo(() => ({ current: null as (() => void) | null }), []);
  const coverage = reconstruction?.coverage ?? 0;
  const insufficient = reconstruction?.insufficient ?? ["Insufficient observations"];
  const hasGeo = (reconstruction?.pose_landmarks?.length || 0) > 0;

  return (
    <div className="panel flex h-full min-h-[320px] flex-col">
      <div className="flex items-center justify-between border-b border-line px-3 py-2 text-[11px] uppercase tracking-wider text-muted">
        <span>AI estimated 3D view</span>
        <span className="font-mono text-accent2">Estimated 3D Model</span>
      </div>
      <div className="relative min-h-[280px] flex-1 bg-[#05080f]">
        <Canvas camera={{ position: [0, 0.4, 3.2], fov: 45 }} gl={{ antialias: true }}>
          <color attach="background" args={["#05080f"]} />
          <ambientLight intensity={0.55} />
          <directionalLight position={[2, 3, 4]} intensity={1.1} />
          <gridHelper args={[6, 12, "#1e3a5f", "#132033"]} />
          {hasGeo ? <Figure reconstruction={reconstruction} mode={mode} /> : null}
          <ControlsBinder resetRef={resetRef} />
        </Canvas>
        {mode === "xray" && (
          <div className="pointer-events-none absolute left-3 top-3 rounded border border-accent/40 bg-ink/80 px-2 py-1 font-mono text-[10px] uppercase tracking-widest text-accent">
            AI ESTIMATED 3D VIEW
          </div>
        )}
        {!hasGeo && (
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center text-sm text-muted">
            Insufficient observations
          </div>
        )}
      </div>
      <div className="space-y-2 border-t border-line p-3">
        <div className="flex items-center justify-between text-[11px] uppercase text-muted">
          <span>3D reconstruction coverage</span>
          <span className="font-mono text-accent">{coverage.toFixed(0)}%</span>
        </div>
        <div className="h-2 overflow-hidden rounded bg-panel2">
          <div className="h-full bg-accent" style={{ width: `${Math.min(100, coverage)}%` }} />
        </div>
        <div className="flex flex-wrap gap-2 text-[10px] text-muted">
          {["front", "left", "right", "back"].map((v) => {
            const on = reconstruction?.views?.[v] || reconstruction?.views?.[`${v}_view`];
            return (
              <span key={v} className={on ? "text-accent" : "text-danger"}>
                {v}
                {on ? " ✓" : " unavailable"}
              </span>
            );
          })}
        </div>
        {insufficient.length > 0 && <p className="text-[10px] text-warn">{insufficient[0]}</p>}
        <div className="flex justify-end">
          <ResetButton onReset={() => resetRef.current?.()} />
        </div>
      </div>
    </div>
  );
}
