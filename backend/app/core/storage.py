"""结果文件的对象存储层。

本地文件系统仍然是第一存储（同步接口立即返回、本地开发不受影响），
R2 作为持久副本：容器重启/重建后任务结果仍可从 R2 取回。
凭据通过环境变量提供（CF_API_TOKEN / CF_ACCOUNT_ID / R2_RESULT_BUCKET），
未配置时所有函数静默降级为 no-op，本地 SQLite + 文件模式完全不受影响。
"""

import hashlib
import hmac
import logging
import os
import time
from urllib.parse import quote

import httpx

from app.config import (
    CF_ACCOUNT_ID,
    CF_API_TOKEN,
    FILE_SIGN_SECRET,
    PUBLIC_FILES_BASE,
    R2_RESULT_BUCKET,
    R2_RESULT_PREFIX,
)

logger = logging.getLogger("storage")

_ENABLED = bool(CF_API_TOKEN and CF_ACCOUNT_ID and R2_RESULT_BUCKET)
_BASE_URL = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/r2/buckets/{R2_RESULT_BUCKET}/objects"
_HEADERS = {"Authorization": f"Bearer {CF_API_TOKEN}"}
_TIMEOUT = httpx.Timeout(connect=5.0, read=60.0, write=120.0, pool=10.0)


def _object_url(task_id: str, filename: str | None = None) -> str:
    key = f"{R2_RESULT_PREFIX}/{task_id}"
    if filename:
        key = f"{key}/{filename}"
    return f"{_BASE_URL}/{quote(key, safe='')}"


def upload_result(task_id: str, task_dir: str) -> None:
    if not _ENABLED or not os.path.isdir(task_dir):
        return
    with httpx.Client(timeout=_TIMEOUT, headers=_HEADERS) as client:
        for name in sorted(os.listdir(task_dir)):
            path = os.path.join(task_dir, name)
            if not os.path.isfile(path):
                continue
            try:
                with open(path, "rb") as fh:
                    resp = client.put(_object_url(task_id, name), content=fh.read())
                if resp.status_code >= 400:
                    logger.warning("R2 upload failed %s/%s: %s", task_id, name, resp.status_code)
            except OSError as exc:
                logger.warning("R2 upload read error %s/%s: %s", task_id, name, exc)
            except httpx.HTTPError as exc:
                logger.warning("R2 upload network error %s/%s: %s", task_id, name, exc)


def fetch_result(task_id: str, filename: str) -> bytes | None:
    if not _ENABLED:
        return None
    try:
        resp = httpx.get(_object_url(task_id, filename), headers=_HEADERS, timeout=_TIMEOUT)
    except httpx.HTTPError as exc:
        logger.warning("R2 fetch network error %s/%s: %s", task_id, filename, exc)
        return None
    if resp.status_code == 200:
        return resp.content
    if resp.status_code != 404:
        logger.warning("R2 fetch failed %s/%s: %s", task_id, filename, resp.status_code)
    return None


def delete_result(task_id: str) -> None:
    if not _ENABLED:
        return
    try:
        httpx.delete(_object_url(task_id), headers=_HEADERS, timeout=_TIMEOUT)
    except httpx.HTTPError as exc:
        logger.warning("R2 delete network error %s: %s", task_id, exc)


def signed_file_url(task_id: str, filename: str, ttl_seconds: int = 3600) -> str | None:
    """生成经边缘校验的直链：客户端 302 后从 CF 边缘(R2)下载，绕开源站带宽。

    签名格式与 Worker 的 /files/ 校验逻辑保持一致：
      msg = "{prefix}/{task_id}/{filename}:{exp}"，sig = HMAC-SHA256 前 32 位十六进制。
    未启用 R2 或缺少签名密钥时返回 None，调用方回退为源站本地流式响应。
    """
    if not (_ENABLED and FILE_SIGN_SECRET and PUBLIC_FILES_BASE):
        return None
    exp = int(time.time()) + ttl_seconds
    message = f"{R2_RESULT_PREFIX}/{task_id}/{filename}:{exp}"
    signature = hmac.new(FILE_SIGN_SECRET.encode(), message.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{PUBLIC_FILES_BASE}/files/{task_id}/{quote(filename, safe='')}?exp={exp}&sig={signature}"
