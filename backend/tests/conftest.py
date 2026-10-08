import os
import tempfile

os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(tempfile.gettempdir(), 'test_media.db')}"

import pytest

from app.services import ai_service

# 真实实现（fixture patch 前保存），供需要验证降级行为的用例恢复
REAL_LOCAL_MODEL_MISSING = ai_service.local_model_missing


@pytest.fixture(autouse=True)
def local_models_available(monkeypatch):
    """默认视为本地模型可用，避免测试环境缺 rembg/faster_whisper 时提交被 503。

    需要验证降级行为的用例请用 REAL_LOCAL_MODEL_MISSING 恢复真实实现。
    """
    monkeypatch.setattr(ai_service, "local_model_missing", lambda task_type: None)
