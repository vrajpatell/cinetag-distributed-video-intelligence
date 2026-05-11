# Optional Cloud CDN in front of the media bucket. Playback still uses signed URLs;
# CDN can cache GETs when objects are publicly readable or when using signed URLs
# with cache-friendly TTLs — see docs/streaming-roadmap.md.

resource "google_compute_backend_bucket" "media_cdn" {
  count = var.enable_cloud_cdn ? 1 : 0

  name        = "${var.bucket_name}-cdn-backend"
  bucket_name = google_storage_bucket.media.name
  enable_cdn  = true

  cdn_policy {
    cache_mode        = "CACHE_ALL_STATIC"
    default_ttl       = 3600
    max_ttl           = 86400
    client_ttl        = 3600
    negative_caching  = true
    serve_while_stale = 86400
  }
}
