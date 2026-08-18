from fastapi import HTTPException

from app.core import security
from app.database import SessionLocal, Base, engine


def setup_module(module):
    Base.metadata.create_all(bind=engine)


def teardown_module(module):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_generate_api_key_unique_and_length():
    keys = {security.generate_api_key() for _ in range(100)}
    assert len(keys) == 100
    for key in keys:
        assert len(key) == 32


def test_hash_api_key_consistent():
    key = "test-key-123"
    assert security.hash_api_key(key) == security.hash_api_key(key)
    assert security.hash_api_key(key) != security.hash_api_key(key + "x")


def test_admin_token_roundtrip():
    token = security.create_admin_token()
    assert security.verify_admin_token(token) is True


def test_verify_admin_token_rejects_garbage():
    assert security.verify_admin_token("not-a-token") is False


def test_authenticate_developer_rejects_invalid_key():
    from sqlalchemy.orm import Session
    db = SessionLocal()
    try:
        try:
            security.authenticate_developer(authorization="Bearer invalid-key", db=db)
            assert False, "should raise 401"
        except HTTPException as e:
            assert e.status_code == 401
    finally:
        db.close()
