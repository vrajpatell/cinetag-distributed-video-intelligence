resource "google_cloud_run_v2_service" "frontend" {
  name     = "cinetag-frontend"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    containers {
      image = var.frontend_image

      env {
        name  = "VITE_API_BASE_URL"
        value = google_cloud_run_v2_service.api.uri
      }

      ports {
        container_port = 8080
      }
    }
  }
}
