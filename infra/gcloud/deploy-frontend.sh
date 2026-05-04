#!/usr/bin/env bash
set -euo pipefail
PROJECT_ID=${PROJECT_ID:-cinetag-distributed-video}
REGION=${REGION:-us-central1}
REPO=${REPO:-cinetag-containers}

gcloud auth list --filter=status:ACTIVE --format='value(account)' | grep -q .
gcloud config set project "$PROJECT_ID" >/dev/null

case "$(basename "$0")" in
  setup-gcp.sh)
    gcloud services enable run.googleapis.com sqladmin.googleapis.com redis.googleapis.com storage.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com cloudbuild.googleapis.com logging.googleapis.com monitoring.googleapis.com iam.googleapis.com compute.googleapis.com
    gcloud artifacts repositories describe "$REPO" --location "$REGION" >/dev/null 2>&1 || gcloud artifacts repositories create "$REPO" --repository-format=docker --location "$REGION"
    gcloud storage buckets describe "gs://${PROJECT_ID}-media" >/dev/null 2>&1 || gcloud storage buckets create "gs://${PROJECT_ID}-media" --location "$REGION"
    ;;
  build-and-push.sh)
    gcloud builds submit --config cloudbuild.yaml --substitutions _PROJECT_ID="$PROJECT_ID",_REGION="$REGION",_REPOSITORY="$REPO"
    ;;
  deploy-api.sh)
    gcloud run deploy cinetag-api --image "$REGION-docker.pkg.dev/$PROJECT_ID/$REPO/cinetag-api:latest" --region "$REGION" --allow-unauthenticated
    ;;
  deploy-worker.sh)
    gcloud run deploy cinetag-worker --image "$REGION-docker.pkg.dev/$PROJECT_ID/$REPO/cinetag-worker:latest" --region "$REGION" --no-allow-unauthenticated --command python --args -m,app.workers.worker_main
    ;;
  deploy-frontend.sh)
    gcloud run deploy cinetag-frontend --image "$REGION-docker.pkg.dev/$PROJECT_ID/$REPO/cinetag-frontend:latest" --region "$REGION" --allow-unauthenticated
    ;;
  run-migrations.sh)
    gcloud run jobs execute cinetag-migrate --region "$REGION" --wait
    ;;
  destroy-dev-resources.sh)
    gcloud run services delete cinetag-api cinetag-worker cinetag-frontend --region "$REGION" --quiet || true
    ;;
esac
