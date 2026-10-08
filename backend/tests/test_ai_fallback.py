from io import BytesIO

import pytest
from PIL import Image
from fastapi import HTTPException

from app.services import ai_service


def _png_bytes() -> bytes:
    buf = BytesIO()
    Image.new("RGB", (8, 8), (10, 20, 30)).save(buf, "PNG")
    return buf.getvalue()


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_run_t2i_falls_back_to_smaller_size(monkeypatch, tmp_path):
    monkeypatch.setattr(ai_service.channels, "resolve", lambda cap: [])
    tried = []

    def fake_pollinations(prompt, width, height):
        tried.append((width, height))
        if (width, height) == (1024, 1024):
            raise RuntimeError("pollinations 500")
        return _png_bytes()

    def fail_modelscope(*args, **kwargs):
        raise AssertionError("不应回退到 ModelScope")

    monkeypatch.setattr(ai_service, "_t2i_pollinations", fake_pollinations)
    monkeypatch.setattr(ai_service, "_t2i_modelscope", fail_modelscope)

    filename = ai_service.run_t2i("赛博朋克城市夜景", str(tmp_path), 1024, 1024)

    assert (1024, 1024) in tried
    assert (512, 512) in tried
    assert filename.endswith(".png")
    assert (tmp_path / filename).exists()


def test_channel_image_bytes_raises_http_error_not_keyerror():
    with pytest.raises(HTTPException) as exc:
        ai_service._channel_image_bytes({"error": {"message": "quota exceeded"}})

    assert exc.value.status_code == 502
    assert "quota exceeded" in exc.value.detail


def test_t2i_modelscope_supports_async_task_id(monkeypatch):
    monkeypatch.setattr("app.core.settings.get_modelscope_token", lambda: "token-abc")
    monkeypatch.setattr("httpx.post", lambda *a, **k: _FakeResponse({"task_id": "task-1"}))
    monkeypatch.setattr(ai_service, "_modelscope_poll_image", lambda headers, task_id, label: _png_bytes())

    data = ai_service._t2i_modelscope("一只猫", 768, 768)

    assert data == _png_bytes()


def test_local_model_missing_reports_uninstalled_dependency(monkeypatch):
    from conftest import REAL_LOCAL_MODEL_MISSING

    monkeypatch.setattr(ai_service, "local_model_missing", REAL_LOCAL_MODEL_MISSING)
    # 模拟依赖未安装：sys.modules 中置 None 会让 __import__ 抛 ImportError
    import sys

    monkeypatch.setitem(sys.modules, "rembg", None)
    monkeypatch.setitem(sys.modules, "faster_whisper", None)

    assert ai_service.local_model_missing("matting") is not None
    assert "人像抠图" in ai_service.local_model_missing("matting")
    assert "画质增强" in ai_service.local_model_missing("enhance")
    assert "语音识别" in ai_service.local_model_missing("asr")
    assert ai_service.local_model_missing("t2i") is None
    assert ai_service.local_model_missing("unknown") is None


def test_local_model_missing_returns_none_when_installed(monkeypatch):
    from conftest import REAL_LOCAL_MODEL_MISSING

    import sys
    import types

    monkeypatch.setattr(ai_service, "local_model_missing", REAL_LOCAL_MODEL_MISSING)
    monkeypatch.setitem(sys.modules, "rembg", types.ModuleType("rembg"))
    assert ai_service.local_model_missing("matting") is None
