from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health() -> None:
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["identity_module"] == "OFF"
    assert body["microphone"] in {"ON", "OFF"}


def test_cameras_and_zones() -> None:
    res = client.get("/api/cameras")
    assert res.status_code == 200
    zones = client.get("/api/zones")
    assert zones.status_code == 200
    assert len(zones.json()) >= 3


def test_start_demo_and_people_endpoint() -> None:
    res = client.post("/api/cameras/start", json={"source": "demo", "demo_mode": True})
    assert res.status_code == 200
    body = res.json()
    assert body["status"] in {"running", "error"}
    people = client.get("/api/people")
    assert people.status_code == 200
    events = client.get("/api/events")
    assert events.status_code == 200
    analytics = client.get("/api/analytics")
    assert analytics.status_code == 200
    client.post("/api/cameras/stop")


def test_settings_and_export() -> None:
    res = client.get("/api/settings")
    assert res.status_code == 200
    csv = client.get("/api/export/timeline.csv")
    assert csv.status_code == 200
    assert "timestamp" in csv.text


def test_docs() -> None:
    res = client.get("/docs")
    assert res.status_code == 200
