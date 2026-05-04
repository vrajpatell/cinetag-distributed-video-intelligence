locals { api_roles=["roles/cloudsql.client","roles/storage.objectAdmin","roles/secretmanager.secretAccessor","roles/logging.logWriter","roles/monitoring.metricWriter"] }
resource "google_project_iam_member" "api" { for_each=toset(local.api_roles) project=var.project_id role=each.value member="serviceAccount:${google_service_account.api.email}" }
resource "google_project_iam_member" "worker" { for_each=toset(local.api_roles) project=var.project_id role=each.value member="serviceAccount:${google_service_account.worker.email}" }
