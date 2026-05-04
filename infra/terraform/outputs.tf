output "api_url" { value=google_cloud_run_v2_service.api.uri }
output "frontend_url" { value=google_cloud_run_v2_service.frontend.uri }
output "bucket_name" { value=google_storage_bucket.media.name }
output "cloud_sql_connection_name" { value=google_sql_database_instance.postgres.connection_name }
output "redis_host" { value=google_redis_instance.main.host }
output "artifact_registry_repo" { value=google_artifact_registry_repository.containers.id }
