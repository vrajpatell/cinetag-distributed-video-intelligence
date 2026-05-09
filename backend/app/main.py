import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    routes_health,
    routes_jobs,
    routes_metrics,
    routes_review,
    routes_search,
    routes_tags,
    routes_upload,
    routes_videos,
)
from app.core.config import settings
from app.core.secrets import preload_known_secrets
from app.db.session import engine

preload_known_secrets()
logging.basicConfig(level=settings.log_level)

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)
app.include_router(routes_health.router)
app.include_router(routes_upload.router, prefix='/api')
app.include_router(routes_jobs.router, prefix='/api')
app.include_router(routes_videos.router, prefix='/api')
app.include_router(routes_tags.router, prefix='/api')
app.include_router(routes_search.router, prefix='/api')
app.include_router(routes_review.router, prefix='/api')
app.include_router(routes_metrics.router)

if settings.otel_enabled:
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)
        logging.getLogger(__name__).info("otel_fastapi_instrumented")
    except Exception:
        logging.getLogger(__name__).warning("otel_fastapi_instrumentation_unavailable")
    try:
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

        SQLAlchemyInstrumentor().instrument(engine=engine)
        logging.getLogger(__name__).info("otel_sqlalchemy_instrumented")
    except Exception:
        logging.getLogger(__name__).warning("otel_sqlalchemy_instrumentation_unavailable")
