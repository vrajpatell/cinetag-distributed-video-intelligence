resource "google_cloud_run_v2_service" "worker" {
  name     = "cinetag-worker"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_ONLY"

  template {
    service_account = google_service_account.worker.email

    containers {
      image   = var.worker_image
      command = ["python", "-m", "app.workers.worker_main"]

      env {
        name  = "APP_ENV"
        value = "gcp"
      }

      env {
        name  = "REDIS_URL"
        value = "redis://${google_redis_instance.main.host}:6379/0"
      }

      env {
        name  = "CLOUD_SQL_CONNECTION_NAME"
        value = google_sql_database_instance.postgres.connection_name
      }
    }
  }
}
