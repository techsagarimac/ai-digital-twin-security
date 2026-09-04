# Architecture

**AI 3D Digital Twin Security Camera** is a modular prototype that turns a
webcam or security video into tracked people, visible-attribute observations,
an estimated 3D digital twin, and a timeline-driven operations dashboard.

This document is the source of truth for how subsystems connect. Individual
AI models are swappable behind interfaces.

---

## 1. Design principles

1. **Visible evidence only.** RGB cameras cannot see through clothing or bodies.
   The “X-ray-style” view is a **visualization of AI-derived geometry**
   (landmarks, skeleton, transparent mesh). It is never a medical or physical scan.
2. **Graceful degradation.** Missing YOLO, MediaPipe, or Whisper must not crash
   the app. The UI reports `model unavailable` and continues with remaining stages.
3. **Explainability.** Every prediction carries a confidence. Below-threshold
   values become `UNKNOWN`, not facts.
4. **Privacy by default.** No race, health, emotion-as-fact, criminality, or
   external face-search. Temporary track IDs (`P001`) are not biometric identities.
   Optional identification is a separate module, **off by default**.
5. **Honest demo data.** Simulated detections are labeled `DEMO` / `SIMULATED`
   and never mixed with live inference without that label.

---

## 2. Pipeline

```
Camera adapter (webcam | video file | RTSP plugin)
        │
        ▼
   Frame sampler (PROCESS_EVERY_N_FRAMES, max inference width)
        │
        ▼
   Person detector (YOLO → HOG fallback → demo/empty)
        │
        ▼
   Multi-object tracker (IoU + velocity, timeout)
        │
        ├── Face mesh / landmarks (MediaPipe → Haar fallback)
        ├── Pose landmarks (MediaPipe → unavailable)
        ├── Accessory / object detector (same YOLO pass when possible)
        └── Visible attributes (region sampling from pose/bbox)
                │
                ▼
        Reconstruction fusion (view bins, coverage %, no hallucinated geometry)
                │
                ▼
        Event engine (enter/exit, zones, objects, pose, speech, reconstruction)
                │
                ▼
        SQLite / PostgreSQL  +  WebSocket /ws/live  +  REST API
                │
                ▼
        React dashboard (live view, 3D twin, timeline, analytics)
```

Optional branch:

```
Microphone (explicitly enabled)
  → VAD → segment → transcription adapter (Whisper / mock / unavailable)
  → audio_events + transcriptions
```

---

## 3. Layering

| Layer | Location | Responsibility |
| --- | --- | --- |
| Adapters | `backend/app/camera`, `vision/*`, `audio/*` | I/O and model implementations |
| Domain | `events`, `vision/tracker`, `vision/reconstruction`, `vision/zones` | Tracking, zones, fusion, event rules |
| Persistence | `database/` | SQLAlchemy models and repositories |
| Application | `services/` | Use-cases, retention, analytics, camera runtime |
| Transport | `api/`, `ws/` | REST + WebSocket, validation, OpenAPI |
| Presentation | `frontend/` | Dashboard, 3D viewer, charts |

Models never talk to HTTP. HTTP never talks to OpenCV directly.

---

## 4. Model abstractions

Replace implementations without changing APIs:

| Interface | Real | Fallback | Demo |
| --- | --- | --- | --- |
| `BaseDetector` | `YOLODetector` | `HOGDetector` | `MockDetector` |
| `BaseFaceProcessor` | `MediaPipeFaceProcessor` | `HaarFaceProcessor` | `MockFaceProcessor` |
| `BasePoseProcessor` | `MediaPipePoseProcessor` | none | `MockPoseProcessor` |
| `BaseSpeechProcessor` | `WhisperSpeechProcessor` | unavailable | `MockSpeechProcessor` |
| `BaseCameraSource` | `WebcamSource`, `VideoFileSource` | — | `DemoSource` |
| `RTSPSource` | plugin adapter | not connected unless configured | — |

Device selection: `MODEL_DEVICE=auto` prefers CUDA when `torch.cuda.is_available()`,
otherwise CPU. CUDA is never required.

---

## 5. 3D reconstruction (MVP)

The MVP does **not** run photogrammetry or NeRF.

1. Each processed frame stores pose/face landmarks with yaw/pitch/roll and a
   view bin: `front`, `left`, `right`, `back`.
2. Landmarks are stored in a normalized person-centric frame (shoulders as the
   lateral axis, mid-hip as origin).
3. Observations in the same bin are averaged (confidence-weighted).
4. Coverage is the fraction of bins with enough observations. Unseen bins stay
   empty and the UI shows **Insufficient observations** / **Back view unavailable**.
5. The frontend builds a Three.js figure from fused landmarks: skeleton,
   landmark points, and a transparent mesh. Label: **Estimated 3D Model** and
   **AI ESTIMATED 3D VIEW**.

If only one camera exists, the reconstruction is progressive as the person turns.
It is not a 360° scan.

---

## 6. Tracking and identity

Track IDs (`P001`, `P002`, …) are **session-local temporary IDs**.

A track is closed when it is unseen for `TRACKING_TIMEOUT` seconds. Duration is
`last_seen − first_seen` (UTC internally).

The identity package (`backend/app/identity`) is isolated. It refuses to run
unless `IDENTITY_MODULE_ENABLED=true` **and** an explicit consent flag is set
in settings. No face gallery or external search is implemented.

---

## 7. Zones

Zones are axis-aligned rectangles in **normalized frame coordinates** (0–1).
The bbox centroid selects the active zone. Entry, exit, dwell time, and visit
count are recorded as timeline events.

Default seed:

- Zone A — Entrance (left)
- Zone B — Reception (center)
- Zone C — Restricted Area (right)

---

## 8. Live transport

`/ws/live` sends JSON messages:

- `hello` — camera/model/device status
- `frame` — JPEG (base64), people, boxes, landmarks, objects, attributes,
  reconstruction coverage, FPS, events since last frame
- `status` — camera start/stop, microphone, model availability
- `error` — non-fatal pipeline errors

The UI draws overlays from structured data so the live image stays the
**actual camera image**, distinct from landmarks, mesh, and objects.

---

## 9. Frontend composition

```
App (router)
  Layout (top stats + nav)
    Dashboard
      CameraView | DigitalTwin | PersonCard list
      Timeline
    PersonDetails (large twin + history)
    Analytics (Recharts)
    Settings (camera, thresholds, audio, retention, zones)
```

React Three Fiber renders the twin. Modes: rotate, wireframe, solid, landmarks,
skeleton, transparent X-ray-style (no internal anatomy).

---

## 10. Data retention

`DATA_RETENTION_DAYS` (default 7) is enforced by a startup + periodic cleanup
job: expired detections, events, audio files, reconstructions, and recordings
are deleted. The prototype does not retain data indefinitely.

---

## 11. Future extension points

Interfaces already exist (or are stubbed) for multi-camera fusion, depth/LiDAR,
stereo, edge deployment, RBAC, audit logs, encrypted storage, and RTSP CCTV.
Do not pretend those features are complete in v1.

---

## 12. What this system is not

- Not an X-ray, millimeter-wave, or medical imaging device
- Not a biometric identification product (module off)
- Not a predictor of crime, health, race, emotion, or personality
- Not a perfect 360° body scanner from one RGB camera
