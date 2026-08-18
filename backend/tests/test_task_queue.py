import time

from app import models
from app.core import task_queue
from app.core.security import generate_api_key, hash_api_key
from app.database import Base, SessionLocal, engine


def setup_module(module):
    Base.metadata.create_all(bind=engine)


def teardown_module(module):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def make_developer(db):
    dev = models.Developer(name="tester", email="t@example.com", api_key_hash=hash_api_key(generate_api_key()))
    db.add(dev)
    db.commit()
    db.refresh(dev)
    return dev


def wait_for_status(task_id, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        poll = SessionLocal()
        try:
            task = poll.query(models.Task).filter(models.Task.task_id == task_id).first()
            if task and task.status in ("succeeded", "failed"):
                return task
        finally:
            poll.close()
        time.sleep(0.2)
    raise TimeoutError("task did not finish")


def test_task_succeeds(monkeypatch):
    monkeypatch.setattr(
        "app.services.ai_service.run_ai_task",
        lambda *a, **kw: {"filename": "out.png", "kind": "image"},
    )
    db = SessionLocal()
    try:
        dev = make_developer(db)
        task_id = task_queue.create_task(dev.id, "matting", {"input_path": "/tmp/x.png"})
        task = wait_for_status(task_id)
        assert task.status == "succeeded"
        assert task.result_url.endswith("out.png")
    finally:
        db.close()


def test_task_failure_records_error(monkeypatch):
    def boom(*a, **kw):
        raise RuntimeError("model crashed")

    monkeypatch.setattr("app.services.ai_service.run_ai_task", boom)
    db = SessionLocal()
    try:
        dev = make_developer(db)
        task_id = task_queue.create_task(dev.id, "asr", {"input_path": "/tmp/x.wav"})
        task = wait_for_status(task_id)
        assert task.status == "failed"
        assert "model crashed" in task.error
    finally:
        db.close()
