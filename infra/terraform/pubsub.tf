resource "google_pubsub_topic" "processing_jobs" {
  name = var.pubsub_topic_name
}

resource "google_pubsub_topic" "processing_jobs_dlq" {
  name = var.pubsub_dead_letter_topic_name
}

resource "google_pubsub_subscription" "processing_jobs" {
  name  = var.pubsub_subscription_name
  topic = google_pubsub_topic.processing_jobs.name

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.processing_jobs_dlq.id
    max_delivery_attempts = 5
  }
}

resource "google_pubsub_topic_iam_member" "api_publish" {
  topic  = google_pubsub_topic.processing_jobs.name
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:${google_service_account.api.email}"
}

resource "google_pubsub_subscription_iam_member" "worker_subscribe" {
  subscription = google_pubsub_subscription.processing_jobs.name
  role         = "roles/pubsub.subscriber"
  member       = "serviceAccount:${google_service_account.worker.email}"
}
