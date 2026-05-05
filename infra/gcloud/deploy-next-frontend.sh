#!/usr/bin/env bash
set -euo pipefail
PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project)}"
REGION="${REGION:-us-central1}"
REPO="${REPO:-cinetag}"
API_URL="$(gcloud run services describe cinetag-api --region "$REGION" --format='value(status.url)')"
IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/$REPO/cinetag-frontend:$(date +%Y%m%d-%H%M%S)"
gcloud builds submit frontend --tag "$IMAGE" --substitutions=_NEXT_PUBLIC_API_BASE_URL="$API_URL"
gcloud run deploy cinetag-frontend --image "$IMAGE" --region "$REGION" --allow-unauthenticated --set-env-vars "NEXT_PUBLIC_API_BASE_URL=$API_URL"
gcloud run services describe cinetag-frontend --region "$REGION" --format='value(status.url)'
