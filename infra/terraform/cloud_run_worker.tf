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

      env {
        name  = "SECRET_MANAGER_ENABLED"
        value = var.secret_manager_enabled ? "true" : "false"
      }

      env {
        name  = "SEMANTIC_SEARCH_BACKEND"
        value = var.semantic_search_backend
      }

      env {
        name = "DATABASE_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.database_password.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "OPENAI_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.openai_api_key.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "SERVICE_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.service_api_key.secret_id
            version = "latest"
          }
        }
      }
    }
  }
}
