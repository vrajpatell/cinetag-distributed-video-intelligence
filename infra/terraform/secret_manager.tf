resource "google_secret_manager_secret" "database_password" {
  secret_id = "DATABASE_PASSWORD"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "database_password" {
  secret      = google_secret_manager_secret.database_password.id
  secret_data = random_password.db.result
}

resource "google_secret_manager_secret" "openai_api_key" {
  secret_id = "OPENAI_API_KEY"

  replication {
    auto {}
  }
}

# Placeholder; replace in console or via `gcloud secrets versions add` before enabling OpenAI.
resource "google_secret_manager_secret_version" "openai_api_key" {
  secret      = google_secret_manager_secret.openai_api_key.id
  secret_data = "replace-me-openai-key"
}

resource "random_password" "admin_api_key" {
  length  = 32
  special = false
}

resource "google_secret_manager_secret" "admin_api_key" {
  secret_id = "ADMIN_API_KEY"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "admin_api_key" {
  secret      = google_secret_manager_secret.admin_api_key.id
  secret_data = random_password.admin_api_key.result
}

resource "random_password" "reviewer_api_key" {
  length  = 32
  special = false
}

resource "google_secret_manager_secret" "reviewer_api_key" {
  secret_id = "REVIEWER_API_KEY"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "reviewer_api_key" {
  secret      = google_secret_manager_secret.reviewer_api_key.id
  secret_data = random_password.reviewer_api_key.result
}

resource "random_password" "service_api_key" {
  length  = 32
  special = false
}

resource "google_secret_manager_secret" "service_api_key" {
  secret_id = "SERVICE_API_KEY"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "service_api_key" {
  secret      = google_secret_manager_secret.service_api_key.id
  secret_data = random_password.service_api_key.result
}
