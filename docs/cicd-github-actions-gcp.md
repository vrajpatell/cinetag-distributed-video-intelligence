# CI/CD: GitHub Actions → GCP Cloud Run

This guide sets up a fully automated CI/CD pipeline that runs every time you push to `main`:

```
push to main  ──▶  Lint + tests  ──▶  Cloud Build (api/worker/frontend)
                                              │
                                              ▼
                                     Run DB migrations job
                                              │
                                              ▼
                                  Deploy api / worker / frontend (parallel)
                                              │
                                              ▼
                                       Smoke test API /health
```

The workflow file is [`.github/workflows/deploy-gcp.yml`](../.github/workflows/deploy-gcp.yml).
The build config it submits is [`cloudbuild.yaml`](../cloudbuild.yaml).

GitHub authenticates to GCP using **Workload Identity Federation (WIF)** — no
long‑lived service account JSON keys are stored in GitHub.

---

## Prerequisites (one‑time, on your laptop)

- `gcloud` CLI logged in: `gcloud auth login`
- Project bootstrapped (APIs enabled, Artifact Registry repo, GCS bucket). If not yet done:
  ```bash
  bash infra/gcloud/setup-gcp.sh
  ```
- Cloud Run services and the migration job already exist (Terraform under
  `infra/terraform/` provisions them). Run once:
  ```bash
  cd infra/terraform
  terraform init
  terraform apply -var="project_id=cinetag-distributed-video"
  ```
- You know your GCP project number (not the project id):
  ```bash
  gcloud projects describe cinetag-distributed-video --format='value(projectNumber)'
  ```

Throughout this guide, replace these placeholders:

| Placeholder              | Example value                                    |
| ------------------------ | ------------------------------------------------ |
| `<PROJECT_ID>`           | `cinetag-distributed-video`                      |
| `<PROJECT_NUMBER>`       | `1015789800459`                                  |
| `<REGION>`               | `us-central1`                                    |
| `<REPO>`                 | `cinetag-containers`                             |
| `<GITHUB_OWNER>/<REPO>`  | `vrajpatel/cinetag-distributed-video-intelligence` |

---

## Step 1 — Create a deployer service account in GCP

This is the identity GitHub Actions will impersonate.

```bash
PROJECT_ID=cinetag-distributed-video
REGION=us-central1

gcloud iam service-accounts create github-deployer \
  --project="$PROJECT_ID" \
  --display-name="GitHub Actions deployer"

DEPLOYER_SA="github-deployer@${PROJECT_ID}.iam.gserviceaccount.com"
```

Grant the roles it needs to build images, run the migration job, and update Cloud Run:

```bash
for ROLE in \
  roles/run.admin \
  roles/cloudbuild.builds.editor \
  roles/artifactregistry.writer \
  roles/storage.admin \
  roles/logging.logWriter \
  roles/iam.serviceAccountUser; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${DEPLOYER_SA}" \
    --role="$ROLE"
done
```

Why each role:

- `run.admin` — deploy/update Cloud Run services and execute Cloud Run jobs.
- `cloudbuild.builds.editor` — submit Cloud Build builds.
- `artifactregistry.writer` — push images to Artifact Registry.
- `storage.admin` — Cloud Build's source upload bucket (`gs://<PROJECT>_cloudbuild`).
- `logging.logWriter` — write build/deploy logs.
- `iam.serviceAccountUser` — required to deploy a Cloud Run revision that runs as
  the api/worker runtime service accounts (`cinetag-api-sa`, `cinetag-worker-sa`).

> If your runtime SAs are restricted, you can scope this last role to only those
> SAs instead of project‑wide:
> ```bash
> gcloud iam service-accounts add-iam-policy-binding \
>   "cinetag-api-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
>   --member="serviceAccount:${DEPLOYER_SA}" \
>   --role="roles/iam.serviceAccountUser"
> # repeat for cinetag-worker-sa
> ```

---

## Step 2 — Set up Workload Identity Federation

### 2a. Enable the IAM Credentials API

```bash
gcloud services enable iamcredentials.googleapis.com sts.googleapis.com \
  --project="$PROJECT_ID"
```

### 2b. Create a Workload Identity Pool

```bash
gcloud iam workload-identity-pools create "github-pool" \
  --project="$PROJECT_ID" \
  --location="global" \
  --display-name="GitHub Actions pool"
```

### 2c. Create a GitHub OIDC provider inside the pool

Replace `<GITHUB_OWNER>/<REPO>` with your repository, e.g. `vrajpatel/cinetag-distributed-video-intelligence`.

```bash
GITHUB_REPO="<GITHUB_OWNER>/<REPO>"

gcloud iam workload-identity-pools providers create-oidc "github-provider" \
  --project="$PROJECT_ID" \
  --location="global" \
  --workload-identity-pool="github-pool" \
  --display-name="GitHub OIDC" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
  --attribute-condition="assertion.repository == '${GITHUB_REPO}'"
```

The `attribute-condition` is the security boundary — only tokens issued for
**your** repo can use this provider.

### 2d. Allow the GitHub repo to impersonate the deployer SA

```bash
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
DEPLOYER_SA="github-deployer@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud iam service-accounts add-iam-policy-binding "$DEPLOYER_SA" \
  --project="$PROJECT_ID" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-pool/attribute.repository/${GITHUB_REPO}"
```

### 2e. Capture the provider resource name

You'll paste this into a GitHub secret in Step 3.

```bash
echo "projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-pool/providers/github-provider"
```

It will look like:

```
projects/1015789800459/locations/global/workloadIdentityPools/github-pool/providers/github-provider
```

---

## Step 3 — Add GitHub secrets and variables

In GitHub: **Repo → Settings → Secrets and variables → Actions**.

### Secrets (tab "Secrets")

| Name                              | Value                                                                                                  |
| --------------------------------- | ------------------------------------------------------------------------------------------------------ |
| `GCP_WORKLOAD_IDENTITY_PROVIDER`  | The full provider resource name from Step 2e                                                           |
| `GCP_DEPLOYER_SA`                 | `github-deployer@<PROJECT_ID>.iam.gserviceaccount.com`                                                 |

### Variables (tab "Variables" — not secrets, just config)

| Name                | Value                          |
| ------------------- | ------------------------------ |
| `GCP_PROJECT_ID`    | `cinetag-distributed-video`    |
| `GCP_REGION`        | `us-central1`                  |
| `GCP_ARTIFACT_REPO` | `cinetag-containers`           |

> Variables are referenced in the workflow as `${{ vars.GCP_PROJECT_ID }}`.
> Secrets are referenced as `${{ secrets.GCP_DEPLOYER_SA }}`.

---

## Step 4 — Push to `main` and watch it run

```bash
git add .github/workflows/deploy-gcp.yml cloudbuild.yaml docs/cicd-github-actions-gcp.md
git commit -m "ci: add GitHub Actions → GCP Cloud Run deploy pipeline"
git push origin main
```

Open **GitHub → Actions → deploy-gcp** and watch the five jobs run in order:

1. **test** — `ruff check` + `pytest`
2. **build** — `gcloud builds submit` builds all 3 images, tags each as
   `:latest` and `:sha-<short-sha>`, pushes to Artifact Registry
3. **migrate** — points the `cinetag-migrate` Cloud Run job at the new image
   and executes it (`--wait`)
4. **deploy** — updates `cinetag-api`, `cinetag-worker`, `cinetag-frontend`
   to the new image tag in parallel
5. **smoke** — `curl <api>/health` with retries

---

## How the pipeline works (file map)

| File                                 | Role                                                                                |
| ------------------------------------ | ----------------------------------------------------------------------------------- |
| `.github/workflows/ci.yml`           | PR/push gate: ruff + pytest only. Runs on every branch and PR.                      |
| `.github/workflows/deploy-gcp.yml`   | The deploy pipeline. Runs only on push to `main` and manual `workflow_dispatch`.    |
| `cloudbuild.yaml`                    | Builds api/worker/frontend Docker images and pushes both `:latest` and `:<sha>`.    |
| `infra/gcloud/*.sh`                  | Equivalent manual `gcloud` commands — useful for one-off deploys outside CI.        |
| `infra/terraform/`                   | One-time infra (Cloud Run services, jobs, SQL, Redis, Pub/Sub, IAM, network, etc.). |

The CI image tag is `sha-<first 12 chars of commit>`. Every build also updates
`:latest`, so manual rollbacks are easy:

```bash
# Roll cinetag-api back to a previous commit
gcloud run services update cinetag-api \
  --region us-central1 \
  --image us-central1-docker.pkg.dev/cinetag-distributed-video/cinetag-containers/cinetag-api:sha-abc123def456
```

---

## Verifying the WIF wiring (optional smoke test)

You can trigger the deploy manually from the GitHub UI:
**Actions → deploy-gcp → Run workflow → main**.

If auth is broken you'll see this in the `build` job:

```
Error: google-github-actions/auth failed with: failed to generate Google Cloud federated token
```

Most common causes:

1. The `attribute-condition` in Step 2c doesn't match your repo name exactly
   (case sensitive).
2. The principalSet binding in Step 2d uses the wrong project number or repo name.
3. The GitHub workflow is missing `permissions: id-token: write`.
4. You forgot to enable `iamcredentials.googleapis.com`.

---

## Troubleshooting

### `PERMISSION_DENIED: ... does not have permission to act as ...`

The deployer SA can't impersonate the runtime SA. Add `roles/iam.serviceAccountUser`
on the runtime SAs (see note in Step 1).

### `Cloud Run job cinetag-migrate not found`

Run `terraform apply` to create the migration job, or skip the `migrate` job by
removing it from `deploy-gcp.yml` (then run migrations manually with
`bash infra/gcloud/run-migrations.sh`).

### Smoke test fails with 503

The new revision didn't become ready in time. Check Cloud Run logs:

```bash
gcloud run services logs read cinetag-api --region us-central1 --limit 200
```

### Cloud Build fails with `denied: Permission "artifactregistry.repositories.uploadArtifacts"`

The deployer SA is missing `roles/artifactregistry.writer`, or the Artifact
Registry repo doesn't exist. Re‑run Step 1, or create the repo:

```bash
gcloud artifacts repositories create cinetag-containers \
  --repository-format=docker --location=us-central1
```

### Build is slow

`cloudbuild.yaml` already uses `E2_HIGHCPU_8`. For more speed, switch to
`N1_HIGHCPU_32` and add layer caching with `--cache-from`. The api and worker
images share the same `./backend` build context so Docker reuses layers
automatically inside a single Cloud Build run.

---

## Disabling auto‑deploy

If you need to push to `main` without deploying (docs‑only change, etc.):

- Quick: change the trigger to `paths-ignore` for `docs/**` and `*.md`, or
- Add `[skip ci]` to the commit message and gate jobs with
  `if: "!contains(github.event.head_commit.message, '[skip ci]')"`, or
- Disable the workflow from **Actions → deploy-gcp → ⋯ → Disable workflow**.
