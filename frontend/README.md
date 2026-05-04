# CineTag — frontend

React 18 + TypeScript + Vite 5 SPA, styled with Tailwind in a "Netflix 2026" dark theme. Talks to the FastAPI backend over HTTP and is served in production from `nginx:1.27-alpine` on port `8080`.

## Routes

| Path           | Page                | Notes                                                 |
| -------------- | ------------------- | ----------------------------------------------------- |
| `/`            | `BrowsePage`        | Billboard hero + horizontal carousels                 |
| `/search`      | `SearchPage`        | Semantic search via `POST /api/search/semantic`       |
| `/upload`      | `UploadPage`        | Multipart upload to `POST /api/videos/upload`         |
| `/videos/:id`  | `VideoDetailPage`   | Tags / Scenes / Transcript / Frames tabs              |
| `/jobs`        | `JobsPage`          | Auto-refreshing list of `ProcessingJob`               |
| `/jobs/:id`    | `JobDetailPage`     | Pipeline stepper + retry                              |
| `/review`      | `ReviewQueuePage`   | Approve/reject queue with keyboard shortcuts          |
| `*`            | `NotFoundPage`      | Styled 404                                            |

## Environment variables

All env vars must be prefixed `VITE_` to be exposed to the client. They are read at **build time** (Vite inlines them) — for the production image they're injected via Docker `ARG VITE_API_BASE_URL` (see `frontend/Dockerfile`).

| Variable             | Required | Default                  | Purpose                                         |
| -------------------- | -------- | ------------------------ | ----------------------------------------------- |
| `VITE_API_BASE_URL`  | yes (build) | `http://localhost:8000` | FastAPI base URL the SPA calls                  |
| `VITE_BUILD_SHA`     | no       | `dev`                    | Displayed in the footer                          |

> **Never** hardcode the deployed Cloud Run URL in source — only inject it via `VITE_API_BASE_URL` at build time.

## Local development

Install once:

```bash
cd frontend
npm install
```

Run against the local FastAPI (default `http://localhost:8000`):

```bash
npm run dev
```

Run against the deployed Cloud Run API:

```bash
VITE_API_BASE_URL=https://cinetag-api-1015789800459.us-central1.run.app npm run dev
```

On Windows PowerShell:

```powershell
$env:VITE_API_BASE_URL = "https://cinetag-api-1015789800459.us-central1.run.app"
npm run dev
```

## Type-checking, linting, build

```bash
npm run typecheck   # tsc --noEmit
npm run lint        # eslint
npm run build       # tsc -b && vite build → dist/
npm run preview     # serve dist/ for local smoke testing
```

## Production image

The two-stage Dockerfile builds the SPA with the supplied `VITE_API_BASE_URL` and serves the static `dist/` from nginx on port `8080`. The nginx config (`nginx.conf`) enables gzip, long-caches hashed `/assets/`, exposes `GET /health` returning `200 "ok"`, and falls back to `index.html` for SPA routes.

```bash
docker build \
  --build-arg VITE_API_BASE_URL=https://cinetag-api-1015789800459.us-central1.run.app \
  --build-arg VITE_BUILD_SHA=$(git rev-parse --short HEAD) \
  -t cinetag-frontend:dev frontend
```

## File map (high-level)

```
src/
  components/
    ErrorBoundary.tsx
    forms/Dropzone.tsx
    layout/{AppShell,TopNav,Footer}.tsx
    media/{Billboard,Carousel,MediaCard,PipelineStepper,TagChip}.tsx
    ui/{Button,Card,Badge,Skeleton,Modal,Tabs,RangeSlider,Toaster,toastStore}.tsx
  lib/{cn,format,zodSchemas}.ts
  pages/{Dashboard,SemanticSearch,Upload,Jobs,JobDetail,VideoDetail,ReviewQueue,NotFound}.tsx
  state/
    api.ts queryClient.ts
    hooks/{useVideos,useJobs,useVideoDetails,useTags,useSemanticSearch,useUploadVideo,useReviewQueue}.ts
  styles/globals.css
  main.tsx
```
