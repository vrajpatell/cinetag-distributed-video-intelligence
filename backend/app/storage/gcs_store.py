from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from google.cloud import storage


class GCSStore:
    def __init__(self, bucket_name: str, project: str | None = None):
        self.client = storage.Client(project=project)
        self.bucket = self.client.bucket(bucket_name)

    def upload_file(self, local_path: str, object_name: str) -> str:
        blob = self.bucket.blob(object_name)
        blob.upload_from_filename(local_path)
        return object_name

    def upload_bytes(self, object_name: str, data: bytes, content_type: str | None = None) -> str:
        blob = self.bucket.blob(object_name)
        blob.upload_from_string(data, content_type=content_type)
        return object_name

    def download_file(self, object_name: str, destination_path: str) -> str:
        Path(destination_path).parent.mkdir(parents=True, exist_ok=True)
        self.bucket.blob(object_name).download_to_filename(destination_path)
        return destination_path

    def generate_signed_url(self, object_name: str, expiration_seconds: int = 3600, method: str = 'GET') -> str:
        return self.bucket.blob(object_name).generate_signed_url(expiration=timedelta(seconds=expiration_seconds), method=method)

    def delete_object(self, object_name: str) -> None:
        self.bucket.blob(object_name).delete()

    def object_exists(self, object_name: str) -> bool:
        return self.bucket.blob(object_name).exists()

    def get_public_or_signed_url(self, object_name: str, use_signed_url: bool = True, expiration_seconds: int = 3600) -> str:
        if use_signed_url:
            return self.generate_signed_url(object_name, expiration_seconds=expiration_seconds)
        return f'https://storage.googleapis.com/{self.bucket.name}/{object_name}'
