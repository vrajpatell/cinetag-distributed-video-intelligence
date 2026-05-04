resource "google_cloud_run_v2_service" "worker" {
  name     = "cinetag-worker"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_ONLY"

  template {
    timeout = "3600s"

    service_account = google_service_account.worker.email

    scaling {
      min_instance_count = 1
    }

    containers {
      image   = var.worker_image
      command = ["python", "-m", "app.workers.worker_service_main"]

      resources {
        cpu_idle = false
        limits = {
          cpu    = "1"
          memory = "1Gi"
        }
      }

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
