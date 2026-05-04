from pathlib import Path
from app.core.config import settings

class LocalStore:
    def __init__(self):
        self.base = Path(settings.local_storage_dir)
        self.base.mkdir(parents=True, exist_ok=True)
    def put_bytes(self, key: str, data: bytes) -> str:
        p = self.base / key
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return key
