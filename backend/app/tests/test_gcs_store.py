from unittest.mock import MagicMock, patch

from app.storage.gcs_store import GCSStore


def test_upload_bytes_calls_blob_upload():
    with patch('app.storage.gcs_store.storage.Client') as client_cls:
        blob = MagicMock()
        bucket = MagicMock()
        bucket.blob.return_value = blob
        client_cls.return_value.bucket.return_value = bucket
        s = GCSStore('bucket')
        s.upload_bytes('x', b'1')
        blob.upload_from_string.assert_called_once()
