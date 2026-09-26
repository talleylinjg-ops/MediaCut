import json
import os

from app.core.settings import get_config_value, set_config_value

CHANNELS_CONFIG_KEY = "ai_channels"
CAPABILITIES = ("t2i", "i2i", "chat")

_ENV_CHANNEL_SPECS = (
    ("didi_media", "USER_DIDI_MEDIA"),
    ("didi_mediacut", "USER_DIDI_MEDIACUT"),
)


def _normalize(raw: dict) -> dict | None:
    if not isinstance(raw, dict):
        return None
    name = str(raw.get("name") or "").strip()
    base_url = str(raw.get("base_url") or "").strip()
    if not name or not base_url:
        return None
    caps = [c for c in (raw.get("capabilities") or []) if c in CAPABILITIES]
    if not caps:
        caps = list(CAPABILITIES)
    try:
        priority = int(raw.get("priority", 100))
    except (TypeError, ValueError):
        priority = 100
    return {
        "name": name,
        "base_url": base_url,
        "api_key": str(raw.get("api_key") or ""),
        "model_id": str(raw.get("model_id") or ""),
        "capabilities": caps,
        "priority": priority,
        "is_free": bool(raw.get("is_free", True)),
        "enabled": bool(raw.get("enabled", True)),
    }


def _from_env() -> list[dict]:
    result = []
    for name, prefix in _ENV_CHANNEL_SPECS:
        base_url = os.getenv(f"{prefix}_BASE_URL", "").strip()
        if not base_url:
            continue
        result.append(
            {
                "name": name,
                "base_url": base_url,
                "api_key": os.getenv(f"{prefix}_API_KEY", "").strip(),
                "model_id": os.getenv(f"{prefix}_MODEL_ID", "").strip(),
                "capabilities": list(CAPABILITIES),
                "priority": 10,
                "is_free": True,
                "enabled": True,
            }
        )
    return result


def get_channels() -> list[dict]:
    raw = get_config_value(CHANNELS_CONFIG_KEY)
    channels: list[dict] = []
    if raw:
        try:
            parsed = json.loads(raw)
        except (TypeError, ValueError):
            parsed = None
        if isinstance(parsed, list):
            for item in parsed:
                norm = _normalize(item)
                if norm is not None:
                    channels.append(norm)
    if not channels:
        channels = _from_env()
    return channels


def save_channels(entries: list[dict]) -> None:
    existing = {c["name"]: c for c in get_channels()}
    normalized = []
    for item in entries:
        norm = _normalize(item)
        if norm is None:
            continue
        if not norm["api_key"]:
            prev = existing.get(norm["name"])
            if prev is not None:
                norm["api_key"] = prev["api_key"]
        normalized.append(norm)
    set_config_value(CHANNELS_CONFIG_KEY, json.dumps(normalized, ensure_ascii=False))


def resolve(capability: str) -> list[dict]:
    items = [c for c in get_channels() if c["enabled"] and capability in c["capabilities"]]
    return sorted(items, key=lambda c: c["priority"])


def free_capabilities() -> set[str]:
    caps: set[str] = set()
    for c in get_channels():
        if c["enabled"] and c["is_free"]:
            caps.update(c["capabilities"])
    return caps


def has_free(capability: str | None = None) -> bool:
    caps = free_capabilities()
    if capability is None:
        return bool(caps)
    return capability in caps


def public_channels() -> list[dict]:
    return [
        {
            "name": c["name"],
            "base_url": c["base_url"],
            "model_id": c["model_id"],
            "capabilities": c["capabilities"],
            "priority": c["priority"],
            "is_free": c["is_free"],
            "enabled": c["enabled"],
            "has_key": bool(c["api_key"]),
        }
        for c in get_channels()
    ]
