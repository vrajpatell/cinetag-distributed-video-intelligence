# Deploying CineTag to GCP

## Quickstart
```bash
gcloud config set project cinetag-distributed-video
gcloud config set run/region us-central1
cd infra/terraform
terraform init
terraform plan -var="project_id=cinetag-distributed-video"
terraform apply -var="project_id=cinetag-distributed-video"
```

```bash
gcloud builds submit --config cloudbuild.yaml \
  --substitutions _PROJECT_ID=cinetag-distributed-video,_REGION=us-central1
```

```bash
gcloud run jobs execute cinetag-migrate --region us-central1 --wait
curl https://<api-url>/health
curl https://<api-url>/ready
```
