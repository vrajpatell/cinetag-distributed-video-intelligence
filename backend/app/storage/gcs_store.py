from __future__ import annotations

import logging
from datetime import timedelta
from pathlib import Path
from typing import Any

import google.auth
from google.auth import iam
from google.auth.transport.requests import Request
from google.cloud import storage

logger = logging.getLogger(__name__)


class GCSStore:
    """Thin Google Cloud Storage adapter used by the API and worker tier.

    Notes
    -----
    - Signed URL generation requires the runtime service account to have
      ``roles/iam.serviceAccountTokenCreator`` on itself when running on
      Cloud Run with workload identity.
    - We never log the generated signed URL — it grants write access until
      it expires.
    """

    def __init__(self, bucket_name: str, project: str | None = None):
        if not bucket_name:
            raise ValueError("GCSStore requires a non-empty bucket_name")
        self.client = storage.Client(project=project)
        self.bucket = self.client.bucket(bucket_name)

    # ------------------------------------------------------------------
    # Object operations
    # ------------------------------------------------------------------

    def upload_file(self, local_path: str, object_name: str) -> str:
        blob = self.bucket.blob(object_name)
        blob.upload_from_filename(local_path)
        return object_name

    def upload_bytes(
        self, object_name: str, data: bytes, content_type: str | None = None
    ) -> str:
        blob = self.bucket.blob(object_name)
        blob.upload_from_string(data, content_type=content_type)
        return object_name

    def download_file(self, object_name: str, destination_path: str) -> str:
        Path(destination_path).parent.mkdir(parents=True, exist_ok=True)
        self.bucket.blob(object_name).download_to_filename(destination_path)
        return destination_path

    def delete_object(self, object_name: str) -> None:
        self.bucket.blob(object_name).delete()

    def object_exists(self, storage_key: str) -> bool:
        return self.bucket.blob(storage_key).exists(client=self.client)

    def get_object_metadata(self, object_name: str) -> dict:
        blob = self.bucket.blob(object_name)
        if not blob.exists():
            return {}
        blob.reload()
        return {
            "size": blob.size,
            "content_type": blob.content_type,
            "updated": blob.updated.isoformat() if blob.updated else None,
        }

    # ------------------------------------------------------------------
    # Signed URL helpers
    # ------------------------------------------------------------------

    def generate_signed_url(
        self,
        object_name: str,
        expiration_seconds: int = 3600,
        method: str = "GET",
    ) -> str:
        return self.bucket.blob(object_name).generate_signed_url(
            version="v4",
            expiration=timedelta(seconds=expiration_seconds),
            method=method,
        )

    def generate_signed_upload_url(
        self,
        storage_key: str,
        content_type: str,
        expires_minutes: int = 15,
    ) -> str:
        """Generate a v4 signed PUT URL for a direct browser upload.

        The returned URL is sensitive — callers must not log it.
        """
        if not storage_key:
            raise ValueError("storage_key is required")
        if not content_type:
            raise ValueError("content_type is required")
        blob = self.bucket.blob(storage_key)
        try:
            return blob.generate_signed_url(
                version="v4",
                expiration=timedelta(minutes=expires_minutes),
                method="PUT",
                content_type=content_type,
            )
        except Exception:
            # Surface a generic message; the caller logs traceback context but
            # never the URL or signing-key contents.
            logger.exception(
                "gcs_signed_upload_url_failed bucket=%s storage_key=%s",
                self.bucket.name,
                storage_key,
            )
            raise

    def get_public_or_signed_url(
        self,
        object_name: str,
        use_signed_url: bool = True,
        expiration_seconds: int = 3600,
    ) -> str:
        if use_signed_url:
            return self.generate_signed_url(
                object_name, expiration_seconds=expiration_seconds
            )
        return f"https://storage.googleapis.com/{self.bucket.name}/{object_name}"
