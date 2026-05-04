resource "google_service_account" "api" { account_id="cinetag-api-sa" }
resource "google_service_account" "worker" { account_id="cinetag-worker-sa" }
resource "google_service_account" "cloudbuild" { account_id="cinetag-cloudbuild-sa" }
