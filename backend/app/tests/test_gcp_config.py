from app.core.config import Settings, build_cloudsql_database_url


def test_gcp_mode_config():
    s = Settings(app_env='gcp', storage_backend='gcs', gcs_bucket_name='bucket')
    assert s.app_env == 'gcp'
    assert s.storage_backend == 'gcs'


def test_cloudsql_url_builder():
    url = build_cloudsql_database_url('p', 'us-central1', 'i', 'db', 'u', 'pw')
    assert '/cloudsql/p:us-central1:i' in url
