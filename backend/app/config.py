import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORAGE_DIR = os.path.join(BASE_DIR, "storage")
UPLOAD_DIR = os.path.join(STORAGE_DIR, "uploads")
RESULT_DIR = os.path.join(STORAGE_DIR, "results")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(RESULT_DIR, exist_ok=True)

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'media.db')}")

MODELSCOPE_API_TOKEN = os.getenv("MODELSCOPE_API_TOKEN", "")

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production-please-set-a-strong-secret")
JWT_EXPIRE_HOURS = 24

IMAGE_MAX_SIZE = 20 * 1024 * 1024
AUDIO_MAX_SIZE = 100 * 1024 * 1024
IMAGE_ALLOWED_FORMATS = {"image/png", "image/jpeg", "image/webp", "image/bmp"}
AUDIO_ALLOWED_FORMATS = {"audio/mpeg", "audio/wav", "audio/ogg", "audio/flac", "audio/x-wav", "application/octet-stream"}

DEFAULT_QUOTA_LIMIT = 1000
TASK_TTL_HOURS = 24
