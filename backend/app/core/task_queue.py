import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

from app import models
from app.config import RESULT_DIR, TASK_TTL_HOURS
from app.core import storage
from app.database import SessionLocal
from app.services import ai_service, chat_service

_executor = ThreadPoolExecutor(max_workers=2)
_cleanup_interval = 30 * 60


def create_task(developer_id: int, task_type: str, params: dict) -> str:
    db = SessionLocal()
    try:
        task = models.Task(
            developer_id=developer_id,
            task_type=task_type,
            params=json.dumps(params),
            status="pending",
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        task_id = task.task_id
        row_id = task.id
    finally:
        db.close()
    _executor.submit(run_task, row_id)
    return task_id


def run_task(task_id: int) -> None:
    db = SessionLocal()
    try:
        task = db.get(models.Task, task_id)
        if task is None:
            return
        task.status = "running"
        db.commit()

        params = json.loads(task.params)
        task_dir = os.path.join(RESULT_DIR, task.task_id)
        os.makedirs(task_dir, exist_ok=True)

        if task.task_type == "chat":
            result = chat_service.run_chat(params, task_dir)
            task.status = "succeeded"
            task.result_kind = result.get("kind")
            task.result_text = result.get("text")
            if result.get("filename"):
                task.result_url = os.path.join(task.task_id, result["filename"])
            db.commit()
            storage.upload_result(task.task_id, task_dir)
            return

        result = ai_service.run_ai_task(task.task_type, params, task_dir)

        task.status = "succeeded"
        task.result_url = os.path.join(task.task_id, result["filename"])
        task.result_kind = result.get("kind")
        task.result_text = result.get("text")
        db.commit()
        storage.upload_result(task.task_id, task_dir)
    except Exception as exc:
        task = db.get(models.Task, task_id)
        if task is not None:
            task.status = "failed"
            task.error = str(exc)
            db.commit()
    finally:
        db.close()


def cleanup_expired_tasks() -> None:
    cutoff = datetime.utcnow() - timedelta(hours=TASK_TTL_HOURS)
    db = SessionLocal()
    try:
        stale = db.query(models.Task).filter(
            models.Task.created_at < cutoff,
            models.Task.status.in_(["succeeded", "failed"]),
        ).all()
        for task in stale:
            task_dir = os.path.join(RESULT_DIR, task.task_id)
            if os.path.isdir(task_dir):
                for f in os.listdir(task_dir):
                    try:
                        os.remove(os.path.join(task_dir, f))
                    except OSError:
                        pass
            storage.delete_result(task.task_id)
    finally:
        db.close()


def _cleanup_loop() -> None:
    while True:
        time.sleep(_cleanup_interval)
        try:
            cleanup_expired_tasks()
        except Exception:
            pass


_cleanup_thread = threading.Thread(target=_cleanup_loop, daemon=True)
_cleanup_thread.start()
