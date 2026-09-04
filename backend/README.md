# Backend

Python 3.11+ FastAPI service for the AI 3D Digital Twin Security Camera.

## Run

```bash
cd backend
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows
# .venv\Scripts\activate

pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API docs: http://127.0.0.1:8000/docs

Optional models:

```bash
pip install -r requirements-optional.txt
```

## Tests

```bash
cd backend
python -m pytest
```

## Layout

- `app/vision` — detectors, tracker, face/pose, attributes, reconstruction
- `app/camera` — webcam, video file, RTSP adapter, demo source
- `app/events` — timeline event engine
- `app/database` — SQLAlchemy models (SQLite default, PostgreSQL-ready)
- `app/api` — REST + `/ws/live`
- `app/identity` — biometric module stub, **off by default**
