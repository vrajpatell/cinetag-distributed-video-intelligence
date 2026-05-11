resource "google_pubsub_topic" "processing_jobs" {
  name   = var.pubsub_topic_name
  labels = { app = "cinetag", component = "processing" }
}

resource "google_pubsub_topic" "processing_jobs_dlq" {
  name   = var.pubsub_dead_letter_topic_name
  labels = { app = "cinetag", component = "processing-dlq" }
}

resource "google_pubsub_subscription" "processing_jobs" {
  name  = var.pubsub_subscription_name
  topic = google_pubsub_topic.processing_jobs.name

  ack_deadline_seconds       = 600
  message_retention_duration = "604800s"

  labels = { app = "cinetag", component = "processing-worker" }

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.processing_jobs_dlq.id
    max_delivery_attempts = 5
  }
}

# Pub/Sub service agent must publish to the DLQ topic for redelivery to work.
resource "google_pubsub_topic_iam_member" "dlq_publisher_pubsub_agent" {
  topic  = google_pubsub_topic.processing_jobs_dlq.id
  role   = "roles/pubsub.publisher"
  member = local.pubsub_service_agent
}
