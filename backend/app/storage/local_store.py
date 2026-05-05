from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from app.core.config import settings


class LocalStore:
    """Filesystem-backed object store used for local development.

    It mirrors the surface of :class:`app.storage.gcs_store.GCSStore` so the
    upload flow (signed URLs, object existence checks, metadata) keeps working
    end-to-end without GCS in dev environments.
    """

    def __init__(self) -> None:
        self.base = Path(settings.local_storage_dir)
        self.base.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        return self.base / key

    def put_bytes(self, key: str, data: bytes) -> str:
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return key

    def upload_bytes(self, object_name: str, data: bytes, content_type: str | None = None) -> str:
        return self.put_bytes(object_name, data)

    def upload_file(self, local_path: str, object_name: str) -> str:
        data = Path(local_path).read_bytes()
        return self.put_bytes(object_name, data)

    def download_file(self, object_name: str, destination_path: str) -> str:
        src = self._path(object_name)
        dst = Path(destination_path)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes())
        return destination_path

    def delete_object(self, object_name: str) -> None:
        p = self._path(object_name)
        if p.exists():
            p.unlink()

    def object_exists(self, object_name: str) -> bool:
        return self._path(object_name).exists()

    def get_object_metadata(self, object_name: str) -> dict:
        p = self._path(object_name)
        if not p.exists():
            return {}
        st = p.stat()
        return {
            'size': st.st_size,
            'content_type': None,
            'updated': None,
        }

    def generate_signed_url(self, object_name: str, expiration_seconds: int = 3600, method: str = 'GET') -> str:
        # No real signing in local mode — return a deterministic local-storage URL.
        return f'local-storage://{quote(object_name)}'

    def generate_signed_upload_url(
        self,
        storage_key: str,
        content_type: str,
        expires_minutes: int = 15,
    ) -> str:
        return f'local-storage://{quote(storage_key)}?upload=1&ct={quote(content_type)}'

    def get_public_or_signed_url(self, object_name: str, use_signed_url: bool = True, expiration_seconds: int = 3600) -> str:
        return self.generate_signed_url(object_name, expiration_seconds=expiration_seconds)
