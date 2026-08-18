from datetime import date

import pytest
from fastapi import HTTPException

from app import models
from app.core import quota
from app.core.security import generate_api_key, hash_api_key
from app.database import Base, SessionLocal, engine


def setup_module(module):
    Base.metadata.create_all(bind=engine)


def teardown_module(module):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def make_developer(db, quota_limit=3):
    dev = models.Developer(
        name="tester",
        email="t@example.com",
        api_key_hash=hash_api_key(generate_api_key()),
        quota_limit=quota_limit,
    )
    db.add(dev)
    db.commit()
    db.refresh(dev)
    return dev


def test_consume_quota_increments_used():
    db = SessionLocal()
    try:
        dev = make_developer(db, quota_limit=3)
        quota.consume_quota(db, dev)
        assert dev.quota_used == 1
    finally:
        db.close()


def test_quota_exceeded_raises_429():
    db = SessionLocal()
    try:
        dev = make_developer(db, quota_limit=1)
        quota.consume_quota(db, dev)
        with pytest.raises(HTTPException) as exc:
            quota.consume_quota(db, dev)
        assert exc.value.status_code == 429
    finally:
        db.close()


def test_quota_reset_on_new_day():
    db = SessionLocal()
    try:
        dev = make_developer(db, quota_limit=2)
        dev.quota_used = 2
        dev.quota_date = date(2000, 1, 1)
        db.commit()
        quota.check_quota(db, dev)
        assert dev.quota_date == date.today()
        assert dev.quota_used == 0
    finally:
        db.close()


def test_remaining_quota_never_negative():
    db = SessionLocal()
    try:
        dev = make_developer(db, quota_limit=5)
        dev.quota_used = 10
        assert quota.remaining_quota(dev) == 0
    finally:
        db.close()
