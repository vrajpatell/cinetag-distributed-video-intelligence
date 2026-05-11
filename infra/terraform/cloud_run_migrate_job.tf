resource "google_cloud_run_v2_job" "migrate" {
  name     = "cinetag-migrate"
  location = var.region

  template {
    template {
      service_account = google_service_account.api.email

      vpc_access {
        connector = google_vpc_access_connector.serverless.id
        egress    = "PRIVATE_RANGES_ONLY"
      }

      containers {
        image   = var.api_image
        command = ["python", "scripts/run_migrations.py"]

        env {
          name  = "APP_ENV"
          value = "gcp"
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
          name  = "GCP_PROJECT_ID"
          value = var.project_id
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
      }
    }
  }
}
