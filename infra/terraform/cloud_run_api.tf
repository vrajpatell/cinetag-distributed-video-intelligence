resource "google_cloud_run_v2_service" "api" {
  name     = "cinetag-api"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.api.email
    timeout         = "900s"

    containers {
      image = var.api_image

      env {
        name  = "APP_ENV"
        value = "gcp"
      }

      env {
        name  = "STORAGE_BACKEND"
        value = "gcs"
      }

      env {
        name  = "GCS_BUCKET_NAME"
        value = var.bucket_name
      }

      env {
        name  = "REDIS_URL"
        value = "redis://${google_redis_instance.main.host}:6379/0"
      }

      env {
        name  = "CLOUD_SQL_CONNECTION_NAME"
        value = google_sql_database_instance.postgres.connection_name
      }

      ports {
        container_port = 8080
      }
    }
  }
}
