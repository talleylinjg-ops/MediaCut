from app import models
from app.core import channels
from app.database import Base, SessionLocal, engine


def setup_module(module):
    Base.metadata.create_all(bind=engine)
    _clear()


def teardown_module(module):
    _clear()


def _clear():
    db = SessionLocal()
    try:
        db.query(models.AppConfig).delete()
        db.commit()
    finally:
        db.close()


def test_save_and_get_roundtrip():
    _clear()
    channels.save_channels(
        [
            {
                "name": "didi_media",
                "base_url": "https://a.example.com/v1",
                "api_key": "k1",
                "model_id": "m1",
                "capabilities": ["t2i", "i2i"],
                "priority": 5,
                "is_free": True,
                "enabled": True,
            }
        ]
    )
    got = channels.get_channels()
    assert len(got) == 1
    assert got[0]["name"] == "didi_media"
    assert got[0]["api_key"] == "k1"
    assert got[0]["capabilities"] == ["t2i", "i2i"]


def test_invalid_entries_are_skipped():
    _clear()
    channels.save_channels(
        [
            {"name": "", "base_url": "https://x.example.com/v1"},
            {"name": "no_url", "base_url": ""},
            {"name": "ok", "base_url": "https://ok.example.com/v1", "capabilities": ["chat"]},
        ]
    )
    got = channels.get_channels()
    assert [c["name"] for c in got] == ["ok"]


def test_resolve_filters_and_orders_by_priority():
    _clear()
    channels.save_channels(
        [
            {"name": "b", "base_url": "https://b.example.com/v1", "capabilities": ["t2i"], "priority": 20},
            {"name": "a", "base_url": "https://a.example.com/v1", "capabilities": ["t2i"], "priority": 10},
            {"name": "c", "base_url": "https://c.example.com/v1", "capabilities": ["chat"], "priority": 1},
            {
                "name": "off",
                "base_url": "https://d.example.com/v1",
                "capabilities": ["t2i"],
                "priority": 0,
                "enabled": False,
            },
        ]
    )
    assert [c["name"] for c in channels.resolve("t2i")] == ["a", "b"]
    assert [c["name"] for c in channels.resolve("chat")] == ["c"]
    assert channels.resolve("i2i") == []


def test_has_free_reflects_enabled_free_channels():
    _clear()
    channels.save_channels(
        [{"name": "paid", "base_url": "https://p.example.com/v1", "capabilities": ["t2i"], "is_free": False}]
    )
    assert channels.has_free("t2i") is False
    assert channels.has_free() is False
    channels.save_channels(
        [
            {"name": "paid", "base_url": "https://p.example.com/v1", "capabilities": ["t2i"], "is_free": False},
            {"name": "free", "base_url": "https://f.example.com/v1", "capabilities": ["i2i"], "is_free": True},
        ]
    )
    assert channels.has_free("i2i") is True
    assert channels.has_free("t2i") is False
    assert channels.has_free() is True


def test_save_preserves_existing_key_when_blank():
    _clear()
    channels.save_channels(
        [{"name": "didi_media", "base_url": "https://a.example.com/v1", "api_key": "secret", "capabilities": ["t2i"]}]
    )
    channels.save_channels(
        [{"name": "didi_media", "base_url": "https://a.example.com/v1", "api_key": "", "capabilities": ["t2i"]}]
    )
    assert channels.get_channels()[0]["api_key"] == "secret"


def test_public_channels_masks_key():
    _clear()
    channels.save_channels(
        [{"name": "didi_media", "base_url": "https://a.example.com/v1", "api_key": "secret", "capabilities": ["t2i"]}]
    )
    pub = channels.public_channels()
    assert pub[0]["has_key"] is True
    assert "api_key" not in pub[0]


def test_env_seeding_when_config_empty(monkeypatch):
    _clear()
    monkeypatch.setenv("USER_DIDI_MEDIA_BASE_URL", "https://env.example.com/v1")
    monkeypatch.setenv("USER_DIDI_MEDIA_API_KEY", "envkey")
    monkeypatch.setenv("USER_DIDI_MEDIA_MODEL_ID", "envmodel")
    got = channels.get_channels()
    assert len(got) == 1
    assert got[0]["name"] == "didi_media"
    assert got[0]["model_id"] == "envmodel"
    assert got[0]["is_free"] is True
    assert channels.has_free("t2i") is True
