resource "google_monitoring_alert_policy" "api_5xx" {
  display_name = "cinetag-api 5xx"
  combiner     = "OR"

  conditions {
    display_name = "5xx"

    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" AND resource.label.service_name=\"cinetag-api\""
      comparison      = "COMPARISON_GT"
      threshold_value = 0
      duration        = "300s"

      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }
}
