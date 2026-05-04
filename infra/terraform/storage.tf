resource "google_storage_bucket" "media" { name=var.bucket_name location=var.region uniform_bucket_level_access=true
 lifecycle_rule { action {type="Delete"} condition {age=30 matches_prefix=["tmp/"]} } }
