# AI 3D Digital Twin Security Camera

A modular security-camera prototype that observes a webcam or uploaded video, detects and tracks people, analyzes **visible** attributes and objects, builds an **estimated** 3D digital twin from landmarks, records a movement timeline, and presents everything on a professional operations dashboard.

This is a college / portfolio engineering project. It is **not** an X-ray, medical, or biometric identification product.

> RGB cameras cannot see through clothing or bodies. The “X-ray-style” view is a **visualization of AI-derived geometry** (transparent mesh, face landmarks, body skeleton). Unseen viewpoints are labeled **insufficient observations**, not invented.

---

## Architecture

```
Camera (webcam | video | RTSP adapter | demo)
  → person detection (YOLO → HOG → demo/empty)
  → tracking (IoU, P001…)
  → face landmarks / mesh (MediaPipe → Haar)
  → pose (MediaPipe)
  → accessories (YOLO COCO classes)
  → clothing / hair (bbox-band sampling)
  → 3D reconstruction fusion (view bins, coverage %)
  → event engine + SQLite
  → REST + WebSocket /ws/live
  → React dashboard + Three.js twin
```

Full design notes: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## Features

- Live webcam, uploaded video, Demo Mode, RTSP plugin adapter
- Person detection and multi-object tracking with session timeout
- Face landmarks, approximate yaw/pitch/roll, pose skeleton overlays
- Visible clothing/hair colour from **region sampling**, not full-frame guesses
- Accessory detections (backpack, bag, phone, glasses heuristic, …) with confidence
- Progressive **Estimated 3D Model** and coverage meter (front/left/right/back)
- Interactive 3D viewer: rotate, zoom, pan, wireframe, mesh, landmarks, skeleton, X-ray-style
- Timeline: enter/exit, zones, objects, pose, reconstruction, optional speech
- Default zones: Entrance, Reception, Restricted Area
- Analytics charts, search, CSV/JSON export (no raw audio/biometrics by default)
- Optional microphone path, **off by default**, UI shows `MICROPHONE: OFF|ON`
- Configurable retention (default 7 days)
- Identity module isolated and **off**
- Graceful fallbacks when YOLO / MediaPipe / Whisper are missing
- Demo Mode with **SIMULATED** labels — never mixed silently with live inference

**Not implemented (by design):** race/ethnicity, health, emotion-as-fact, criminality, personality, secret face search, internal anatomy.

---

## Technology stack

| Layer | Stack |
| --- | --- |
| Backend | Python 3.11+, FastAPI, OpenCV, NumPy, Pydantic, SQLAlchemy, SQLite |
| Frontend | React, TypeScript, Vite, Tailwind CSS, Three.js, React Three Fiber, Recharts |
| Optional AI | Ultralytics YOLO, MediaPipe, faster-whisper |
| Deploy | Docker Compose |

---

## Installation

### 1. Clone and environment

```bash
cd ai-digital-twin-security
cp .env.example .env
```

### 2. Backend (macOS / Linux)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Backend (Windows)

```bat
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API docs: http://127.0.0.1:8000/docs

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Dashboard: http://127.0.0.1:5173

### Optional models

```bash
cd backend
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-optional.txt
```

See [`models/README.md`](models/README.md). CUDA is **never** required. `MODEL_DEVICE=auto` uses GPU when PyTorch reports one.

---

## Camera setup

| Source | How |
| --- | --- |
| Webcam | Dashboard → **Start webcam** (`CAMERA_SOURCE=0`) |
| Uploaded video | **Upload video** (mp4/mov/mkv/webm/avi) |
| Demo | **Demo mode** — generated scene, labeled simulated |
| RTSP | `POST /api/cameras/start` with `{"source":"rtsp","rtsp_url":"rtsp://..."}` |

If the webcam cannot open (permissions, headless CI), the runtime falls back to Demo Mode and says so in the status message.

---

## Demo mode

If no detector weights are installed, start **Demo Mode**. A scripted person enters, is tracked as `P001`, gains face/pose overlays, clothing/object labels, walks through zones, turns so 3D coverage increases, and leaves. All of this is tagged **SIMULATED**.

Never treat demo boxes as live-camera AI.

---

## Configuration

Copy `.env.example`. Important keys:

| Variable | Default | Meaning |
| --- | --- | --- |
| `DETECTION_CONFIDENCE` | `0.5` | Person / attribute threshold |
| `TRACKING_TIMEOUT` | `5` | Seconds before a track closes |
| `PROCESS_EVERY_N_FRAMES` | `2` | Inference stride |
| `RECONSTRUCTION_ENABLED` | `true` | Landmark fusion |
| `AUDIO_ENABLED` | `false` | Microphone allowed |
| `DATA_RETENTION_DAYS` | `7` | Automatic cleanup |
| `DEMO_MODE` | `false` | Simulated pipeline |
| `MODEL_DEVICE` | `auto` | `auto` / `cpu` / `cuda` |
| `IDENTITY_MODULE_ENABLED` | `false` | Must stay off unless authorized |
| `AUTH_ENABLED` / `API_KEY` | off | Optional `X-API-Key` |

---

## Database

SQLite file at `data/twin_security.db` by default. SQLAlchemy URLs can point at PostgreSQL:

```
DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/twin_security
```

Tables include persons, sessions, detections, face/pose/clothing/object/reconstruction observations, timeline events, zones, audio events, transcriptions, camera sessions.

Timestamps are stored in **UTC** and converted in the UI.

---

## 3D reconstruction (honest limits)

The MVP fuses face and pose landmarks into view bins (front / left / right / back) as the person turns. Coverage is the fraction of bins with real observations. Missing bins show **Back view unavailable** (etc.). The mesh is an **Estimated 3D Model**, not a scan.

X-ray-style mode draws a semi-transparent mesh + landmarks + skeleton + detected objects. It does **not** draw organs, bones, or other hidden anatomy.

---

## Privacy

- Temporary IDs (`P001`) are tracking handles, not identities
- No race, health, emotion-as-fact, criminality, or personality inference
- No external face galleries
- Microphone off until the operator enables it
- Default retention 7 days
- Exports omit raw audio and biometric templates

---

## Tests

```bash
cd backend
source .venv/bin/activate
python -m pytest
```

---

## Docker

```bash
cp .env.example .env
docker compose up --build
```

UI: http://localhost:8080 · API: http://localhost:8000/docs

---

## Limitations

- Single RGB camera cannot produce a complete 360° body model
- HOG fallback is slower and less accurate than YOLO
- Haar face landmarks are approximate
- Clothing colour is a coarse visible estimate
- Glasses without YOLO rely on a low-confidence edge heuristic
- RTSP depends on OpenCV/FFmpeg on the host
- Speech needs `faster-whisper` (or stays unavailable)

---

## Future improvements

Multi-camera fusion, depth/LiDAR/stereo, higher-quality reconstruction, edge AI, RBAC, audit logs, encrypted storage, mobile dashboard, on-prem hardening.

---

## Troubleshooting

| Symptom | What to try |
| --- | --- |
| Webcam fails | Grant camera permission; or use Demo Mode / upload a video |
| Empty detections | Install `ultralytics`, lower `DETECTION_CONFIDENCE`, or use Demo Mode |
| “Face mesh model unavailable” | Install `mediapipe`; tracking still continues |
| “Speech transcription unavailable” | Install `faster-whisper`; keep mic off if unused |
| UI cannot reach API | Start uvicorn on port 8000; Vite proxies `/api` and `/ws` |
| Slow FPS | Increase `PROCESS_EVERY_N_FRAMES`, reduce `MAX_INFERENCE_WIDTH` |

---

## License

MIT — see `LICENSE`.
