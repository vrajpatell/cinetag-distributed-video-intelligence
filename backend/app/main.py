from fastapi import FastAPI
from app.api import routes_health, routes_upload, routes_jobs, routes_videos, routes_tags, routes_search, routes_metrics

app = FastAPI(title="CineTag Pipeline")
app.include_router(routes_health.router)
app.include_router(routes_upload.router, prefix="/api")
app.include_router(routes_jobs.router, prefix="/api")
app.include_router(routes_videos.router, prefix="/api")
app.include_router(routes_tags.router, prefix="/api")
app.include_router(routes_search.router, prefix="/api")
app.include_router(routes_metrics.router)
