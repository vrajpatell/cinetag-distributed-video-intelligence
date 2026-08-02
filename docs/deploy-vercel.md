# Deploying the CineTag frontend on Vercel

CineTag uses a hybrid deployment: the Next.js web application runs on Vercel, while the FastAPI control plane and ffmpeg/Celery video workers remain on Cloud Run. PostgreSQL, Redis/Pub/Sub, and GCS remain the durable data and processing tier.

This is an optional managed-cloud path. Vercel and GCP are not open-source infrastructure, and free-tier quotas or pricing can change. Use [`open-source-local-stack.md`](open-source-local-stack.md) when the goal is a local stack with no metered services.

This split keeps request/response web traffic on Vercel without forcing long-running media processing into frontend functions.

## Deployment topology

```text
Browser
  -> Vercel: Next.js 15 / React 19 frontend
       -> Cloud Run: FastAPI control-plane API
            -> Cloud SQL: PostgreSQL + pgvector
            -> Memorystore Redis or Pub/Sub
            -> GCS signed upload URL
                 -> Cloud Run worker: ffmpeg + AI pipeline
```

Video bytes still travel directly from the browser to GCS. Vercel and the FastAPI service only handle the small upload-init and upload-complete requests.

## 1. Deploy the backend tier first

Deploy the API and worker using [`deploy-gcp-cloud-run.md`](deploy-gcp-cloud-run.md). Record the public HTTPS API origin, for example:

```text
https://cinetag-api-abc123-uc.a.run.app
```

The API must be publicly reachable for this frontend integration. Keep mutation authentication enabled and replace the current demo-style browser API key approach with user/session authentication before handling untrusted production users.

## 2. Import the repository into Vercel

Create a Vercel project from this GitHub repository and set:

| Setting | Value |
|---------|-------|
| Framework Preset | Next.js |
| Root Directory | `frontend` |
| Install Command | `npm ci` |
| Build Command | `npm run build` |
| Output Directory | leave unset; Vercel detects `.next` |
| Node.js | 20.x or a currently supported newer LTS |

The checked-in [`frontend/vercel.json`](../frontend/vercel.json) pins the framework and deterministic install/build commands. Git integration will create preview deployments for branches and a production deployment from the configured production branch.

## 3. Configure Vercel environment variables

Add these in Project Settings -> Environment Variables:

| Variable | Required | Scope | Example |
|----------|----------|-------|---------|
| `NEXT_PUBLIC_API_BASE_URL` | yes | Production, Preview, Development | `https://cinetag-api-abc123-uc.a.run.app` |
| `NEXT_PUBLIC_APP_ENV` | recommended | all | `production` or `preview` |
| `NEXT_PUBLIC_DEPLOY_PLATFORM` | optional | all | `Vercel` |
| `NEXT_PUBLIC_DEPLOY_REGION` | optional | all | `global` |

`NEXT_PUBLIC_API_BASE_URL` is compiled into the browser bundle, so changing it requires a redeploy. Do not store API keys, database credentials, OpenAI keys, or other secrets in variables prefixed with `NEXT_PUBLIC_`.

When System Environment Variables are exposed to the deployment, Vercel supplies framework values such as `NEXT_PUBLIC_VERCEL_ENV` and `NEXT_PUBLIC_VERCEL_GIT_COMMIT_SHA`; the footer uses these when custom values are absent.

## 4. Allow Vercel origins in FastAPI

For the production domain, set an exact backend origin allowlist:

```env
CORS_ALLOWED_ORIGINS=https://cinetag.example.com,https://cinetag.vercel.app
```

Preview URLs are dynamic. The backend supports an optional Starlette origin regex:

```env
CORS_ALLOWED_ORIGIN_REGEX=https://cinetag-[a-z0-9-]+-vrajpatells-projects\.vercel\.app
```

Use a project-specific expression, not a blanket `https://.*\.vercel\.app`, because credentials are allowed by the API CORS middleware.

The GCS bucket also needs CORS permission for browser `PUT` requests from the same production and preview origins. See [`infra/gcloud/configure-gcs-cors.sh`](../infra/gcloud/configure-gcs-cors.sh) and keep the list as narrow as practical.

## 5. Verify the preview

After Vercel reports the deployment as ready:

1. Open the preview URL and confirm the health indicator reaches `All systems`.
2. Load Browse, Jobs, Review, and Search and confirm requests target the configured API origin.
3. Upload a small test video and confirm the signed GCS `PUT` completes.
4. Confirm a processing job appears and advances in the Jobs view.
5. Inspect the browser console for CORS failures and Vercel runtime/build logs for rendering failures.

## Boundaries of this deployment

- Vercel hosts the Next.js frontend only in the current implementation.
- FastAPI, migrations, worker processes, ffmpeg/ffprobe, queues, and media storage remain on GCP.
- Vercel Functions, Vercel Queues, Vercel Blob, and a managed Postgres integration are viable future migration targets, but adopting them requires changes to the Python queue, storage, database, and worker execution paths; they are not implied by this frontend deployment.
