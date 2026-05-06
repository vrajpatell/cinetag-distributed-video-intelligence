from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import quote

from app.core.config import settings


class UnsafeStorageKey(ValueError):
    """Raised when a caller-supplied key would escape the storage root."""


# Whitelist matches keys produced by the upload pipeline:
#   originals/<32 hex>/<filename>
#   videos/<filename>
# plus internal sub-paths (frames/, transcripts/, etc.). We forbid any path
# segment that could perform traversal.
_KEY_CHAR_OK = re.compile(r"^[A-Za-z0-9._/\-]+$")
_KEY_FORBIDDEN_SEGMENT = {"", ".", ".."}


class LocalStore:
    """Filesystem-backed object store used for local development.

    It mirrors the surface of :class:`app.storage.gcs_store.GCSStore` so the
    upload flow (signed URLs, object existence checks, metadata) keeps working
    end-to-end without GCS in dev environments.

    All caller-supplied keys go through :meth:`_resolve_safe` which:

    - rejects empty / absolute / traversal-laden paths up front,
    - resolves the result and asserts it is contained within
      :attr:`base` so even symlinked working directories cannot leak data
      outside the configured local store.
    """

    def __init__(self) -> None:
        self.base = Path(settings.local_storage_dir).resolve()
        self.base.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _validate_key(key: str) -> str:
        if not key or not isinstance(key, str):
            raise UnsafeStorageKey("storage key must be a non-empty string")
        # Reject Windows drive letters and any absolute path forms.
        if key.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:[\\/]", key):
            raise UnsafeStorageKey("storage key must be relative")
        if "\\" in key:
            raise UnsafeStorageKey("storage key must not contain backslashes")
        if not _KEY_CHAR_OK.match(key):
            raise UnsafeStorageKey("storage key contains unsupported characters")
        for seg in key.split("/"):
            if seg in _KEY_FORBIDDEN_SEGMENT:
                raise UnsafeStorageKey("storage key may not contain '.' or '..' segments")
        return key

    def _resolve_safe(self, key: str) -> Path:
        safe_key = self._validate_key(key)
        candidate = (self.base / safe_key).resolve()
        # Enforce containment even if a future codepath bypasses _validate_key.
        try:
            candidate.relative_to(self.base)
        except ValueError as exc:
            raise UnsafeStorageKey("resolved path escapes storage root") from exc
        return candidate

    def _path(self, key: str) -> Path:
        return self._resolve_safe(key)

    def put_bytes(self, key: str, data: bytes) -> str:
        p = self._resolve_safe(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return key

    def upload_bytes(
        self, object_name: str, data: bytes, content_type: str | None = None
    ) -> str:
        return self.put_bytes(object_name, data)

    def upload_file(self, local_path: str, object_name: str) -> str:
        data = Path(local_path).read_bytes()
        return self.put_bytes(object_name, data)

    def download_file(self, object_name: str, destination_path: str) -> str:
        src = self._resolve_safe(object_name)
        dst = Path(destination_path)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes())
        return destination_path

    def delete_object(self, object_name: str) -> None:
        p = self._resolve_safe(object_name)
        if p.exists():
            p.unlink()

    def object_exists(self, object_name: str) -> bool:
        try:
            return self._resolve_safe(object_name).exists()
        except UnsafeStorageKey:
            return False

    def get_object_metadata(self, object_name: str) -> dict:
        try:
            p = self._resolve_safe(object_name)
        except UnsafeStorageKey:
            return {}
        if not p.exists():
            return {}
        st = p.stat()
        return {
            "size": st.st_size,
            "content_type": None,
            "updated": None,
        }

    def generate_signed_url(
        self, object_name: str, expiration_seconds: int = 3600, method: str = "GET"
    ) -> str:
        # No real signing in local mode — return a deterministic local-storage URL.
        # Validate the key to keep the contract uniform.
        self._validate_key(object_name)
        return f"local-storage://{quote(object_name)}"

    def generate_signed_upload_url(
        self,
        storage_key: str,
        content_type: str,
        expires_minutes: int = 15,
    ) -> str:
        self._validate_key(storage_key)
        return (
            f"local-storage://{quote(storage_key)}"
            f"?upload=1&ct={quote(content_type)}"
        )

    def get_public_or_signed_url(
        self,
        object_name: str,
        use_signed_url: bool = True,
        expiration_seconds: int = 3600,
    ) -> str:
        return self.generate_signed_url(
            object_name, expiration_seconds=expiration_seconds
        )
