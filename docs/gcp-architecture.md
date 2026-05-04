```mermaid
flowchart LR
  U[User] --> F[Cloud Run Frontend\ncinetag-frontend]
  F --> A[Cloud Run API\ncinetag-api]
  A --> Q[Memorystore Redis\ncinetag-redis]
  A --> DB[Cloud SQL PostgreSQL\ncinetag-postgres]
  A --> GCS[GCS Bucket\ncinetag-distributed-video-media]
  Q --> W[Cloud Run Worker\ncinetag-worker]
  W --> GCS
  W --> DB
  A --> SM[Secret Manager]
  W --> SM
  A --> OBS[Cloud Logging/Monitoring]
  W --> OBS
```
