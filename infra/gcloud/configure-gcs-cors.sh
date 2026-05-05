#!/usr/bin/env bash
set -euo pipefail
BUCKET=gs://cinetag-distributed-video-media
FRONTEND_URL="${1:-$(gcloud run services describe cinetag-frontend --region us-central1 --format='value(status.url)')}"
cat > /tmp/cinetag-cors.json <<JSON
[{
  "origin": ["$FRONTEND_URL","http://localhost:3000","http://localhost:5173"],
  "method": ["GET","PUT","POST","OPTIONS"],
  "responseHeader": ["Content-Type","Authorization","x-goog-resumable","x-goog-content-length-range"],
  "maxAgeSeconds": 3600
}]
JSON
gsutil cors set /tmp/cinetag-cors.json "$BUCKET"
gsutil cors get "$BUCKET"
