import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
except ImportError:
    pass

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

CF_API_TOKEN = os.getenv("CF_API_TOKEN", "")
CF_ACCOUNT_ID = os.getenv("CF_ACCOUNT_ID", "")
R2_RESULT_BUCKET = os.getenv("R2_RESULT_BUCKET", "")
R2_RESULT_PREFIX = os.getenv("R2_RESULT_PREFIX", "results")
FILE_SIGN_SECRET = os.getenv("FILE_SIGN_SECRET", "")
PUBLIC_FILES_BASE = os.getenv("PUBLIC_FILES_BASE", "https://mediacut.chacha.asia")
