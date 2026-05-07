from __future__ import annotations

import logging
import os
from datetime import timedelta
from functools import lru_cache
from pathlib import Path

import google.auth
from google.auth import impersonated_credentials
from google.cloud import storage

logger = logging.getLogger(__name__)


# Scope required to call IAM Credentials' signBlob and to read GCS metadata.
# We keep the same scope on both source and target credentials so the token
# returned by the impersonation call can sign URLs and access the bucket.
_SIGNING_SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]


@lru_cache(maxsize=1)
def _signing_credentials() -> impersonated_credentials.Credentials:
    """Build credentials capable of signing v4 URLs without a JSON key.

    On Cloud Run the runtime service account exposes only an OAuth access
    token (``compute_engine.Credentials``), which lacks a private key, so
    ``blob.generate_signed_url`` cannot sign locally. To work around that
    we self-impersonate via the IAM Credentials API (``signBlob``):

    1. ``google.auth.default()`` gives us the runtime service account's
       short-lived token (the *source* credentials).
    2. ``impersonated_credentials.Credentials`` wraps it and exposes a
       ``sign_bytes`` method backed by IAM Credentials, which is exactly
       what ``generate_signed_url`` needs.

    Required IAM: the runtime SA must have
    ``roles/iam.serviceAccountTokenCreator`` on the target SA. When the
    runtime SA *is* the target SA (the common Cloud Run case) it must
    therefore have that role on itself.

    The result is cached for the process lifetime; the underlying access
    token auto-refreshes via the google-auth transport.
    """
    target_principal = os.environ.get("GOOGLE_SERVICE_ACCOUNT_EMAIL")
    if not target_principal:
        logger.error(
            "gcs_signing_misconfigured: GOOGLE_SERVICE_ACCOUNT_EMAIL is not set; "
            "signed URL generation requires the API runtime SA email so we can "
            "self-impersonate via IAM Credentials"
        )
        raise RuntimeError(
            "GOOGLE_SERVICE_ACCOUNT_EMAIL must be set to the API runtime "
            "service account email for signed URL generation"
        )

    source_credentials, _ = google.auth.default(scopes=_SIGNING_SCOPES)
    return impersonated_credentials.Credentials(
        source_credentials=source_credentials,
        target_principal=target_principal,
        target_scopes=_SIGNING_SCOPES,
        lifetime=3600,
    )


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
        # Sign with impersonated credentials so this works on Cloud Run where
        # the runtime credential has no private key. Same path as PUT signing
        # below; centralising it here means GET URLs never silently fall back
        # to the unsignable ADC.
        return self.bucket.blob(object_name).generate_signed_url(
            version="v4",
            expiration=timedelta(seconds=expiration_seconds),
            method=method,
            credentials=_signing_credentials(),
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
                credentials=_signing_credentials(),
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
