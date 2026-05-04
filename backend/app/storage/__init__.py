from app.core.config import settings
from app.storage.local_store import LocalStore


def get_object_store():
    if settings.storage_backend == 'gcs':
        from app.storage.gcs_store import GCSStore

        return GCSStore(bucket_name=settings.gcs_bucket_name or '', project=settings.gcp_project_id)
    return LocalStore()
