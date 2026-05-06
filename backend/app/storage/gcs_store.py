import os
import urllib.request
from datetime import timedelta
from pathlib import Path
from typing import Any

import google.auth
from google.auth import iam
from google.auth.transport.requests import Request
from google.cloud import storage
from google.oauth2 import service_account


class GCSStore:
    """
    GCS object store for CineTag.

    Cloud Run default credentials only contain an access token, not a private key.
    For signed URLs, use IAMCredentials signing through google.auth.iam.Signer.
    """

    def __init__(self, bucket_name: str | None = None, project: str | None = None):
        self.bucket_name = (
            bucket_name
            or os.getenv("GCS_BUCKET_NAME")
            or os.getenv("MEDIA_BUCKET")
            or os.getenv("STORAGE_BUCKET")
            or os.getenv("BUCKET_NAME")
            or "cinetag-distributed-video-media"
        )
        self.project = project or os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.client = storage.Client(project=self.project)
        self.bucket = self.client.bucket(self.bucket_name)

    def _get_service_account_email(self, credentials: Any) -> str:
        env_email = os.getenv("GOOGLE_SERVICE_ACCOUNT_EMAIL")
        if env_email:
            return env_email

        credential_email = getattr(credentials, "service_account_email", None)
        if credential_email:
            return credential_email

        req = urllib.request.Request(
            "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/email",
            headers={"Metadata-Flavor": "Google"},
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.read().decode("utf-8")

    def _get_iam_signing_credentials(self):
        credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )

        auth_request = Request()
        credentials.refresh(auth_request)

        service_account_email = self._get_service_account_email(credentials)

        signer = iam.Signer(
            request=auth_request,
            credentials=credentials,
            service_account_email=service_account_email,
        )

        return service_account.Credentials(
            signer=signer,
            service_account_email=service_account_email,
            token_uri="https://oauth2.googleapis.com/token",
        )

    def generate_signed_upload_url(
        self,
        storage_key: str,
        content_type: str,
        expires_minutes: int = 15,
    ) -> str:
        signing_credentials = self._get_iam_signing_credentials()
        blob = self.bucket.blob(storage_key)

        return blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=expires_minutes),
            method="PUT",
            content_type=content_type,
            credentials=signing_credentials,
        )

    def generate_signed_url(
        self,
        storage_key: str,
        expires_minutes: int = 60,
        method: str = "GET",
    ) -> str:
        signing_credentials = self._get_iam_signing_credentials()
        blob = self.bucket.blob(storage_key)

        return blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=expires_minutes),
            method=method,
            credentials=signing_credentials,
        )

    def object_exists(self, storage_key: str) -> bool:
        return self.bucket.blob(storage_key).exists(client=self.client)

    def get_object_metadata(self, storage_key: str) -> dict:
        blob = self.bucket.blob(storage_key)
        blob.reload(client=self.client)
        return {
            "name": blob.name,
            "bucket": blob.bucket.name,
            "size": blob.size,
            "content_type": blob.content_type,
            "updated": blob.updated.isoformat() if blob.updated else None,
            "generation": blob.generation,
            "md5_hash": blob.md5_hash,
            "crc32c": blob.crc32c,
        }

    def upload_file(self, local_path: str, storage_key: str, content_type: str | None = None) -> str:
        blob = self.bucket.blob(storage_key)
        blob.upload_from_filename(local_path, content_type=content_type)
        return storage_key

    def upload_bytes(self, data: bytes, storage_key: str, content_type: str | None = None) -> str:
        blob = self.bucket.blob(storage_key)
        blob.upload_from_string(data, content_type=content_type)
        return storage_key

    def download_file(self, storage_key: str, local_path: str) -> str:
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        blob = self.bucket.blob(storage_key)
        blob.download_to_filename(local_path)
        return local_path

    def delete_object(self, storage_key: str) -> None:
        self.bucket.blob(storage_key).delete()
