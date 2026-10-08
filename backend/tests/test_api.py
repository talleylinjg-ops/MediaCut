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


def test_ai_submit_returns_503_when_local_model_missing(monkeypatch):
    """本地模型缺失时提交阶段即 503，调用方无需等待轮询才得知能力不可用。"""
    import sys

    from conftest import REAL_LOCAL_MODEL_MISSING
    from app.services import ai_service

    monkeypatch.setattr(ai_service, "local_model_missing", REAL_LOCAL_MODEL_MISSING)
    monkeypatch.setitem(sys.modules, "rembg", None)

    key, _ = register_charged()
    resp = client.post(
        "/api/v1/ai/matting",
        headers={"Authorization": f"Bearer {key}"},
        files={"file": ("a.png", make_image_bytes(), "image/png")},
    )
    assert resp.status_code == 503
    assert "本地模型" in resp.json()["detail"]


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
        "/api/v1/dev/client/recharge/order",
        headers={"Authorization": f"Bearer {token}"},
        json={"amount_yuan": 10, "payment_method": "alipay"},
    )
    assert resp.status_code == 400
    assert "支付渠道未配置" in resp.json()["detail"]

    resp = client.post(
        "/api/v1/dev/client/recharge/order",
        headers={"Authorization": f"Bearer {token}"},
        json={"amount_yuan": 0, "payment_method": "alipay"},
    )
    assert resp.status_code == 400

    resp = client.post("/api/v1/dev/client/recharge/order", json={"amount_yuan": 10, "payment_method": "alipay"})
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
        json={"recharge_yuan": 5},
    )
    assert resp.status_code == 200
    assert resp.json()["balance"] == billing.SIGNUP_BONUS + 500

    resp = client.get("/api/v1/admin/stats", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_admin_dashboard():
    token = client.post("/api/v1/admin/login", json={"username": "admin", "password": "admin123"}).json()["token"]
    resp = client.get("/api/v1/admin/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_developers"] >= 1
    assert body["total_revenue"] >= 0

    resp = client.get("/api/v1/admin/dashboard")
    assert resp.status_code == 401


def test_admin_change_password_and_restore():
    token = client.post("/api/v1/admin/login", json={"username": "admin", "password": "admin123"}).json()["token"]
    resp = client.put(
        "/api/v1/admin/password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": "admin123", "new_password": "newpass456"},
    )
    assert resp.status_code == 200

    resp = client.post("/api/v1/admin/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 401
    resp = client.post("/api/v1/admin/login", json={"username": "admin", "password": "newpass456"})
    assert resp.status_code == 200

    # 恢复默认密码，避免影响其他用例
    token2 = resp.json()["token"]
    resp = client.put(
        "/api/v1/admin/password",
        headers={"Authorization": f"Bearer {token2}"},
        json={"current_password": "newpass456", "new_password": "admin123"},
    )
    assert resp.status_code == 200


def test_admin_modelscope_config():
    token = client.post("/api/v1/admin/login", json={"username": "admin", "password": "admin123"}).json()["token"]
    resp = client.get("/api/v1/admin/config", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert "modelscope_configured" in resp.json()

    resp = client.put(
        "/api/v1/admin/config",
        headers={"Authorization": f"Bearer {token}"},
        json={"modelscope_api_token": "sk-test-token-123"},
    )
    assert resp.status_code == 200
    resp = client.get("/api/v1/admin/config", headers={"Authorization": f"Bearer {token}"})
    assert resp.json()["modelscope_configured"] is True

    resp = client.put(
        "/api/v1/admin/config",
        headers={"Authorization": f"Bearer {token}"},
        json={"modelscope_api_token": ""},
    )
    assert resp.status_code == 200
    resp = client.get("/api/v1/admin/config", headers={"Authorization": f"Bearer {token}"})
    assert resp.json()["modelscope_configured"] is False


def test_admin_requires_auth():
    resp = client.get("/api/v1/admin/developers")
    assert resp.status_code == 401


def test_admin_channel_config_roundtrip_masks_key():
    from app.core import channels

    token = client.post("/api/v1/admin/login", json={"username": "admin", "password": "admin123"}).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    try:
        resp = client.put(
            "/api/v1/admin/config",
            headers=headers,
            json={
                "channels": [
                    {
                        "name": "didi_media",
                        "base_url": "https://a.example.com/v1",
                        "api_key": "super-secret",
                        "model_id": "m1",
                        "capabilities": ["t2i", "i2i"],
                        "priority": 1,
                        "is_free": True,
                        "enabled": True,
                    }
                ]
            },
        )
        assert resp.status_code == 200

        resp = client.get("/api/v1/admin/config", headers=headers)
        assert resp.status_code == 200
        got = resp.json()["channels"]
        assert len(got) == 1
        assert got[0]["name"] == "didi_media"
        assert got[0]["has_key"] is True
        assert "api_key" not in got[0]

        resp = client.put(
            "/api/v1/admin/config",
            headers=headers,
            json={
                "channels": [
                    {
                        "name": "didi_media",
                        "base_url": "https://a.example.com/v1",
                        "api_key": "",
                        "model_id": "m1",
                        "capabilities": ["t2i", "i2i"],
                    }
                ]
            },
        )
        assert resp.status_code == 200
        assert channels.get_channels()[0]["api_key"] == "super-secret"
    finally:
        channels.save_channels([])


def test_chat_is_free_when_free_channel_configured():
    from app.core import channels

    channels.save_channels(
        [
            {
                "name": "didi_media",
                "base_url": "http://127.0.0.1:9/v1",
                "api_key": "k",
                "model_id": "m",
                "capabilities": ["chat", "t2i", "i2i"],
                "priority": 1,
                "is_free": True,
                "enabled": True,
            }
        ]
    )
    try:
        key, _ = register_charged(balance=0)
        resp = client.post(
            "/api/v1/ai/chat",
            headers={"Authorization": f"Bearer {key}"},
            data={"text": "你好"},
        )
        assert resp.status_code == 200
        db = SessionLocal()
        try:
            dev = db.query(models.Developer).filter(models.Developer.api_key_hash == hash_api_key(key)).first()
            assert dev.balance == 0
            assert dev.quota_used == 1
        finally:
            db.close()
    finally:
        channels.save_channels([])


def test_t2i_endpoint_submits_and_charges(monkeypatch):
    from app.core import task_queue

    calls = {}

    def fake_create(developer_id, task_type, params):
        calls["task_type"] = task_type
        calls["params"] = params
        return "fake-t2i-id"

    monkeypatch.setattr(task_queue, "create_task", fake_create)
    key, _ = register_charged(balance=100)
    resp = client.post(
        "/api/v1/ai/t2i",
        headers={"Authorization": f"Bearer {key}"},
        data={"prompt": "一只在草地上的猫", "width": 768, "height": 768},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["task_id"] == "fake-t2i-id"
    assert body["status_url"] == "/api/v1/tasks/fake-t2i-id"
    assert calls["task_type"] == "t2i"
    assert calls["params"]["width"] == 768
    db = SessionLocal()
    try:
        dev = db.query(models.Developer).filter(models.Developer.api_key_hash == hash_api_key(key)).first()
        assert dev.balance == 100 - billing.get_price("/api/v1/ai/t2i")
    finally:
        db.close()


def test_t2i_endpoint_requires_prompt(monkeypatch):
    from app.core import task_queue

    monkeypatch.setattr(task_queue, "create_task", lambda *a, **k: "x")
    key, _ = register_charged()
    resp = client.post("/api/v1/ai/t2i", headers={"Authorization": f"Bearer {key}"}, data={"prompt": "  "})
    assert resp.status_code == 400


def test_i2i_endpoint_submits_and_charges(monkeypatch):
    from app.core import task_queue

    calls = {}

    def fake_create(developer_id, task_type, params):
        calls["task_type"] = task_type
        calls["params"] = params
        return "fake-i2i-id"

    monkeypatch.setattr(task_queue, "create_task", fake_create)
    key, _ = register_charged(balance=100)
    resp = client.post(
        "/api/v1/ai/i2i",
        headers={"Authorization": f"Bearer {key}"},
        files={"file": ("a.png", make_image_bytes(), "image/png")},
        data={"prompt": "把背景换成海边"},
    )
    assert resp.status_code == 200
    assert resp.json()["task_id"] == "fake-i2i-id"
    assert calls["task_type"] == "i2i"
    assert calls["params"]["prompt"] == "把背景换成海边"
    assert calls["params"]["input_path"]
    db = SessionLocal()
    try:
        dev = db.query(models.Developer).filter(models.Developer.api_key_hash == hash_api_key(key)).first()
        assert dev.balance == 100 - billing.get_price("/api/v1/ai/i2i")
    finally:
        db.close()


def test_i2i_endpoint_requires_file(monkeypatch):
    from app.core import task_queue

    monkeypatch.setattr(task_queue, "create_task", lambda *a, **k: "x")
    key, _ = register_charged()
    resp = client.post(
        "/api/v1/ai/i2i",
        headers={"Authorization": f"Bearer {key}"},
        data={"prompt": "换成红色"},
    )
    assert resp.status_code == 422


def test_i2i_is_free_when_free_channel_configured(monkeypatch):
    from app.core import channels, task_queue

    monkeypatch.setattr(task_queue, "create_task", lambda *a, **k: "fake-i2i-id")
    channels.save_channels(
        [
            {
                "name": "didi_mediacut",
                "base_url": "http://127.0.0.1:9/v1",
                "api_key": "k",
                "model_id": "m",
                "capabilities": ["t2i", "i2i"],
                "priority": 1,
                "is_free": True,
                "enabled": True,
            }
        ]
    )
    try:
        key, _ = register_charged(balance=0)
        resp = client.post(
            "/api/v1/ai/i2i",
            headers={"Authorization": f"Bearer {key}"},
            files={"file": ("a.png", make_image_bytes(), "image/png")},
            data={"prompt": "把背景换成海边"},
        )
        assert resp.status_code == 200
        db = SessionLocal()
        try:
            dev = db.query(models.Developer).filter(models.Developer.api_key_hash == hash_api_key(key)).first()
            assert dev.balance == 0
            assert dev.quota_used == 1
        finally:
            db.close()
    finally:
        channels.save_channels([])


def test_video_endpoint_submits_and_charges(monkeypatch):
    from app.core import task_queue

    calls = {}

    def fake_create(developer_id, task_type, params):
        calls["task_type"] = task_type
        calls["params"] = params
        return "fake-video-id"

    monkeypatch.setattr(task_queue, "create_task", fake_create)
    key, _ = register_charged(balance=100)
    resp = client.post(
        "/api/v1/ai/video",
        headers={"Authorization": f"Bearer {key}"},
        data={"prompt": "海边日落", "duration": 8, "motion": "pan"},
    )
    assert resp.status_code == 200
    assert resp.json()["task_id"] == "fake-video-id"
    assert calls["task_type"] == "video"
    assert calls["params"]["duration"] == 8
    assert calls["params"]["motion"] == "pan"
    db = SessionLocal()
    try:
        dev = db.query(models.Developer).filter(models.Developer.api_key_hash == hash_api_key(key)).first()
        assert dev.balance == 100 - billing.get_price("/api/v1/ai/video")
    finally:
        db.close()


def test_video_endpoint_requires_prompt(monkeypatch):
    from app.core import task_queue

    monkeypatch.setattr(task_queue, "create_task", lambda *a, **k: "x")
    key, _ = register_charged()
    resp = client.post("/api/v1/ai/video", headers={"Authorization": f"Bearer {key}"}, data={"prompt": " "})
    assert resp.status_code == 400


def test_video_endpoint_normalizes_invalid_motion(monkeypatch):
    from app.core import task_queue

    calls = {}

    def fake_create(developer_id, task_type, params):
        calls["params"] = params
        return "fake-video-id"

    monkeypatch.setattr(task_queue, "create_task", fake_create)
    key, _ = register_charged()
    resp = client.post(
        "/api/v1/ai/video",
        headers={"Authorization": f"Bearer {key}"},
        data={"prompt": "雪山", "duration": 999, "motion": "spin"},
    )
    assert resp.status_code == 200
    assert calls["params"]["motion"] == "zoom"
    assert calls["params"]["duration"] == 120

