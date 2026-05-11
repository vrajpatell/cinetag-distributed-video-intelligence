resource "google_cloud_run_v2_service" "api" {
  name     = "cinetag-api"
  location = var.region
  ingress  = var.api_ingress

  template {
    service_account = google_service_account.api.email
    timeout         = "900s"
    vpc_access {
      connector = google_vpc_access_connector.serverless.id
      egress    = "PRIVATE_RANGES_ONLY"
    }

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
        name  = "AUTH_ENABLED"
        value = var.auth_enabled ? "true" : "false"
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
        name = "ADMIN_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.admin_api_key.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "REVIEWER_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.reviewer_api_key.secret_id
            version = "latest"
          }
        }
      }

      ports {
        container_port = 8080
      }
    }
  }
}
