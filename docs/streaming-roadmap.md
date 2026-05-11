# Streaming and delivery roadmap

## Current mode: signed original playback

The API returns short-lived signed GCS URLs (or local streaming endpoints in Docker) pointing at the **original** uploaded asset. The HTML5 `<video>` element uses HTTP Range requests against object storage, so seeking works without downloading the full file. Cloud Run does not proxy video bytes in production.

**Trade-offs:** simple pipeline, one object per asset, predictable storage cost. Egress is billed at GCS rates.

## Next mode: Cloud CDN in front of GCS

Terraform variable `enable_cloud_cdn` (default `false`) can provision a `google_compute_backend_bucket` with CDN enabled for the media bucket.

**Signed URL implications:** URLs must use cache-friendly TTLs and `Cache-Control` on objects where appropriate. Highly sensitive assets may still prefer short TTLs and no CDN caching.

## Future mode: HLS / ABR

For large audiences or variable network conditions, add transcoding (FFmpeg in the worker, or **Google Transcoder API**) to produce HLS (or DASH) with multiple renditions. Storage cost rises with variant count; latency to “ready to play” increases until transcoding completes.

**Feature-flag suggestion:** keep current MP4 path as default; add optional `TranscodedAsset` metadata and worker stages behind a config toggle before any schema change lands in production.

## Future mode: DRM

Not in scope for this repository; would require a separate license service and player stack.

## Cost / benefit summary

| Mode | Pros | Cons |
|------|------|------|
| Signed MP4 (current) | Minimal moving parts | Single bitrate; egress per byte |
| + Cloud CDN | Lower repeat-view latency | Cache/signed-URL design care |
| HLS / ABR | Adaptive quality | Transcode cost, storage multiplier |
| DRM | Controlled distribution | Complexity, vendor lock-in |
