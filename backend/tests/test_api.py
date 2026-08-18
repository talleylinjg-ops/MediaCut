import io
import time

from fastapi.testclient import TestClient

from app import models
from app.database import Base, SessionLocal, engine
from app.main import app

client = TestClient(app)


def setup_module(module):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def register():
    resp = client.post("/api/v1/dev/register", json={"name": "demo", "email": "demo@test.com"})
    assert resp.status_code == 200
    return resp.json()["api_key"]


def make_image_bytes():
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (100, 60), (200, 100, 50)).save(buf, format="PNG")
    return buf.getvalue()


def make_wav_bytes(tmp_path=None):
    import subprocess
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
         "-acodec", "pcm_s16le", "/tmp/opencode/test.wav"],
        capture_output=True, check=True,
    )
    with open("/tmp/opencode/test.wav", "rb") as f:
        return f.read()


def test_register_returns_api_key():
    setup_module(None)
    key = register()
    assert len(key) == 32


def test_image_edit_with_valid_key():
    key = register()
    resp = client.post(
        "/api/v1/image/edit",
        headers={"Authorization": f"Bearer {key}"},
        files={"file": ("a.png", make_image_bytes(), "image/png")},
        data={"params": '{"filter": "gray", "output_format": "jpeg"}'},
    )
    assert resp.status_code == 200
    assert resp.content.startswith(b"\xff\xd8")
    assert "X-Remaining-Quota" in resp.headers


def test_image_edit_invalid_key():
    resp = client.post(
        "/api/v1/image/edit",
        headers={"Authorization": "Bearer invalid"},
        files={"file": ("a.png", make_image_bytes(), "image/png")},
        data={"params": "{}"},
    )
    assert resp.status_code == 401


def test_audio_edit_with_valid_key():
    key = register()
    resp = client.post(
        "/api/v1/audio/edit",
        headers={"Authorization": f"Bearer {key}"},
        files={"file": ("a.wav", make_wav_bytes(), "audio/wav")},
        data={"params": '{"crop": {"start": 0.1, "end": 0.8}}'},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("audio")


def test_ai_submit_and_poll(monkeypatch):
    from app.services import ai_service
    monkeypatch.setattr(
        "app.services.ai_service.run_ai_task",
        lambda *a, **kw: {"filename": "out.png", "kind": "image"},
    )
    key = register()
    resp = client.post(
        "/api/v1/ai/matting",
        headers={"Authorization": f"Bearer {key}"},
        files={"file": ("a.png", make_image_bytes(), "image/png")},
    )
    assert resp.status_code == 200
    task_id = resp.json()["task_id"]

    for _ in range(40):
        r = client.get(
            f"/api/v1/tasks/{task_id}",
            headers={"Authorization": f"Bearer {key}"},
        )
        if r.json()["status"] in ("succeeded", "failed"):
            break
        time.sleep(0.2)
    assert r.json()["status"] == "succeeded"
    assert r.json()["result_url"].endswith("out.png")


def test_ai_tts_requires_text():
    key = register()
    resp = client.post(
        "/api/v1/ai/tts",
        headers={"Authorization": f"Bearer {key}"},
        data={"text": ""},
    )
    assert resp.status_code == 400


def test_quota_exceeded_returns_429():
    key = register()
    db = SessionLocal()
    try:
        from app.core.security import hash_api_key
        dev = db.query(models.Developer).filter(models.Developer.api_key_hash == hash_api_key(key)).first()
        dev.quota_limit = 0
        db.commit()
    finally:
        db.close()
    resp = client.post(
        "/api/v1/image/edit",
        headers={"Authorization": f"Bearer {key}"},
        files={"file": ("a.png", make_image_bytes(), "image/png")},
        data={"params": "{}"},
    )
    assert resp.status_code == 429


def test_admin_login_and_developers():
    resp = client.post("/api/v1/admin/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200
    token = resp.json()["token"]

    resp = client.get("/api/v1/admin/developers", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_admin_requires_auth():
    resp = client.get("/api/v1/admin/developers")
    assert resp.status_code == 401
