import os
import tempfile

os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(tempfile.gettempdir(), 'test_media.db')}"
