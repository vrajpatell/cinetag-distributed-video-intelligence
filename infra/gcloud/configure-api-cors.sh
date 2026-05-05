#!/usr/bin/env bash
set -euo pipefail
REGION="${REGION:-us-central1}"
FRONTEND_URL="$(gcloud run services describe cinetag-frontend --region "$REGION" --format='value(status.url)')"
EXISTING="$(gcloud run services describe cinetag-api --region "$REGION" --format='value(spec.template.spec.containers[0].env[?name="CORS_ALLOWED_ORIGINS"].value)')"
UPDATED="$FRONTEND_URL,http://localhost:3000,http://localhost:5173${EXISTING:+,$EXISTING}"
gcloud run services update cinetag-api --region "$REGION" --update-env-vars "CORS_ALLOWED_ORIGINS=$UPDATED"
API_URL="$(gcloud run services describe cinetag-api --region "$REGION" --format='value(status.url)')"
echo "curl -i -X OPTIONS $API_URL/api/uploads/init -H 'Origin: $FRONTEND_URL' -H 'Access-Control-Request-Method: POST'"
