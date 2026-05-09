resource "google_redis_instance" "main" {
  name               = var.redis_name
  region             = var.region
  tier               = "BASIC"
  memory_size_gb     = 1
  redis_version      = "REDIS_7_0"
  authorized_network = google_compute_network.main.id
}
