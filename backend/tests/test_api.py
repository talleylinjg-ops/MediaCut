import io
import time
import uuid

from fastapi.testclient import TestClient

from app import models
from app.core import billing
from app.core.security import hash_api_key
from app.database import Base, SessionLocal, engine
from app.main import app

client = TestClient(app)


def setup_module(module):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def register(email=None):
    email = email or f"demo{uuid.uuid4().hex[:8]}@test.com"
    resp = client.post("/api/v1/dev/register", json={"name": "demo", "email": email, "password": "secret123"})
    assert resp.status_code == 200
    return resp.json()["api_key"], email


def register_charged(balance=1000):
    key, email = register()
    db = SessionLocal()
    try:
        dev = db.query(models.Developer).filter(models.Developer.api_key_hash == hash_api_key(key)).first()
        dev.balance = balance
        db.commit()
    finally:
        db.close()
    return key, email


def make_image_bytes():
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (100, 60), (200, 100, 50)).save(buf, format="PNG")
    return buf.getvalue()


def make_wav_bytes():
    import subprocess
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
         "-acodec", "pcm_s16le", "/tmp/opencode/test.wav"],
        capture_output=True, check=True,
    )
    with open("/tmp/opencode/test.wav", "rb") as f:
        return f.read()


def test_register_requires_password():
    resp = client.post("/api/v1/dev/register", json={"name": "x", "email": "x@x.com", "password": "123"})
    assert resp.status_code == 400


def test_register_duplicate_email_rejected():
    register()
    _, email = register()
    resp = client.post("/api/v1/dev/register", json={"name": "x", "email": email, "password": "secret123"})
    assert resp.status_code == 409


def test_image_edit_with_valid_key():
    key, _ = register_charged()
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
    key, _ = register_charged()
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
    key, _ = register_charged()
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
    key, _ = register_charged()
    resp = client.post(
        "/api/v1/ai/tts",
        headers={"Authorization": f"Bearer {key}"},
        data={"text": ""},
    )
    assert resp.status_code == 400


def test_quota_exceeded_returns_429():
    key, _ = register()
    db = SessionLocal()
    try:
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


def test_external_charged_and_insufficient_balance():
    key, _ = register()
    price = billing.get_price("/api/v1/image/edit")

    db = SessionLocal()
    try:
        dev = db.query(models.Developer).filter(models.Developer.api_key_hash == hash_api_key(key)).first()
        assert dev.balance == billing.SIGNUP_BONUS
        dev.balance = 0
        db.commit()
    finally:
        db.close()
    resp = client.post(
        "/api/v1/image/edit",
        headers={"Authorization": f"Bearer {key}"},
        files={"file": ("a.png", make_image_bytes(), "image/png")},
        data={"params": "{}"},
    )
    assert resp.status_code == 402  # 余额为 0，低于价格

    db = SessionLocal()
    try:
        dev = db.query(models.Developer).filter(models.Developer.api_key_hash == hash_api_key(key)).first()
        dev.balance = 100
        db.commit()
    finally:
        db.close()
    resp = client.post(
        "/api/v1/image/edit",
        headers={"Authorization": f"Bearer {key}"},
        files={"file": ("a.png", make_image_bytes(), "image/png")},
        data={"params": "{}"},
    )
    assert resp.status_code == 200
    db = SessionLocal()
    try:
        dev = db.query(models.Developer).filter(models.Developer.api_key_hash == hash_api_key(key)).first()
        assert dev.balance == 100 - price
    finally:
        db.close()


def test_internal_developer_free(monkeypatch):
    key, _ = register()
    db = SessionLocal()
    try:
        dev = db.query(models.Developer).filter(models.Developer.api_key_hash == hash_api_key(key)).first()
        dev.billing_type = "internal"
        dev.balance = 0
        db.commit()
    finally:
        db.close()
    resp = client.post(
        "/api/v1/image/edit",
        headers={"Authorization": f"Bearer {key}"},
        files={"file": ("a.png", make_image_bytes(), "image/png")},
        data={"params": "{}"},
    )
    assert resp.status_code == 200
    db = SessionLocal()
    try:
        dev = db.query(models.Developer).filter(models.Developer.api_key_hash == hash_api_key(key)).first()
        assert dev.balance == 0
    finally:
        db.close()


def test_client_login_and_me():
    key, email = register()
    resp = client.post("/api/v1/dev/client/login", json={"email": email, "password": "secret123"})
    assert resp.status_code == 200
    token = resp.json()["token"]

    resp = client.get("/api/v1/dev/client/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    me = resp.json()
    assert me["billing_type"] == "external"
    assert me["balance"] == billing.SIGNUP_BONUS

    resp = client.post("/api/v1/dev/client/login", json={"email": email, "password": "wrong"})
    assert resp.status_code == 401


def test_client_self_recharge():
    key, email = register()
    resp = client.post("/api/v1/dev/client/login", json={"email": email, "password": "secret123"})
    token = resp.json()["token"]

    resp = client.post(
        "/api/v1/dev/client/recharge",
        headers={"Authorization": f"Bearer {token}"},
        json={"amount": 300},
    )
    assert resp.status_code == 200
    assert resp.json()["balance"] == billing.SIGNUP_BONUS + 300

    resp = client.post(
        "/api/v1/dev/client/recharge",
        headers={"Authorization": f"Bearer {token}"},
        json={"amount": 0},
    )
    assert resp.status_code == 400

    resp = client.post("/api/v1/dev/client/recharge", json={"amount": 100})
    assert resp.status_code == 401


def test_client_reset_key():
    key, email = register()
    resp = client.post("/api/v1/dev/client/login", json={"email": email, "password": "secret123"})
    token = resp.json()["token"]
    resp = client.post("/api/v1/dev/client/reset-key", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    new_key = resp.json()["api_key"]
    assert new_key != key

    old_resp = client.post(
        "/api/v1/image/edit",
        headers={"Authorization": f"Bearer {key}"},
        files={"file": ("a.png", make_image_bytes(), "image/png")},
        data={"params": "{}"},
    )
    assert old_resp.status_code == 401


def test_admin_login_and_developers():
    resp = client.post("/api/v1/admin/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200
    token = resp.json()["token"]

    resp = client.get("/api/v1/admin/developers", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_admin_recharge_and_stats():
    key, _ = register()
    token = client.post("/api/v1/admin/login", json={"username": "admin", "password": "admin123"}).json()["token"]
    db = SessionLocal()
    try:
        dev = db.query(models.Developer).filter(models.Developer.api_key_hash == hash_api_key(key)).first()
        dev_id = dev.id
    finally:
        db.close()
    resp = client.put(
        f"/api/v1/admin/developers/{dev_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"recharge": 500},
    )
    assert resp.status_code == 200
    assert resp.json()["balance"] == billing.SIGNUP_BONUS + 500

    resp = client.get("/api/v1/admin/stats", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_admin_requires_auth():
    resp = client.get("/api/v1/admin/developers")
    assert resp.status_code == 401
