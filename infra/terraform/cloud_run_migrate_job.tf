resource "google_cloud_run_v2_job" "migrate" {
  name     = "cinetag-migrate"
  location = var.region

  template {
    template {
      service_account = google_service_account.api.email

      containers {
        image   = var.api_image
        command = ["python", "scripts/run_migrations.py"]
      }
    }
  }
}
