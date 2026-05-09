resource "google_cloud_run_v2_service" "worker" {
  name     = "cinetag-worker"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_ONLY"

  template {
    timeout = "3600s"
    vpc_access {
      connector = google_vpc_access_connector.serverless.id
      egress    = "PRIVATE_RANGES_ONLY"
    }

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
        name  = "QUEUE_BACKEND"
        value = var.queue_backend
      }
      env {
        name  = "PUBSUB_TOPIC_NAME"
        value = var.pubsub_topic_name
      }
      env {
        name  = "PUBSUB_SUBSCRIPTION_NAME"
        value = var.pubsub_subscription_name
      }
      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "GCP_REGION"
        value = var.region
      }

      env {
        name  = "CLOUD_SQL_CONNECTION_NAME"
        value = google_sql_database_instance.postgres.connection_name
      }
    }
  }
}
