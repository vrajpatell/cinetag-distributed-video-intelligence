import logging
import time
import uuid
from contextvars import ContextVar

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.bootstrap import ensure_preload

ensure_preload()

from app.api import (  # noqa: E402
    routes_health,
    routes_jobs,
    routes_metrics,
    routes_review,
    routes_search,
    routes_tags,
    routes_upload,
    routes_videos,
)
from app.core.config import settings  # noqa: E402
from app.db.session import get_engine  # noqa: E402
from app.observability.metrics import api_request_duration_seconds, api_request_total  # noqa: E402

request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


class _RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        rid = request_id_ctx.get()
        record.request_id = rid if rid else "-"
        return True


logging.basicConfig(
    level=settings.log_level,
    format="%(levelname)s %(name)s [rid=%(request_id)s] %(message)s",
    force=True,
)
for _h in logging.root.handlers:
    _h.addFilter(_RequestIdFilter())

_LOG = logging.getLogger(__name__)


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("x-request-id") or str(uuid.uuid4())
        token = request_id_ctx.set(rid)
        request.state.request_id = rid
        try:
            response = await call_next(request)
        finally:
            request_id_ctx.reset(token)
        response.headers["X-Request-ID"] = rid
        return response


app = FastAPI(title=settings.app_name)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _route_metric_label(request: Request) -> str:
    r = request.scope.get("route")
    if r is not None and getattr(r, "path", None):
        return str(r.path)
    return request.url.path.split("?")[0] or "unknown"


@app.middleware("http")
async def api_metrics_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    label = _route_metric_label(request)
    api_request_total.labels(route=label, status_code=str(response.status_code)).inc()
    api_request_duration_seconds.labels(route=label).observe(time.perf_counter() - start)
    return response


app.include_router(routes_health.router)
app.include_router(routes_upload.router, prefix="/api")
app.include_router(routes_jobs.router, prefix="/api")
app.include_router(routes_videos.router, prefix="/api")
app.include_router(routes_tags.router, prefix="/api")
app.include_router(routes_search.router, prefix="/api")
app.include_router(routes_review.router, prefix="/api")
app.include_router(routes_metrics.router)

if settings.otel_enabled:
    if settings.otel_exporter_otlp_endpoint:
        try:
            from opentelemetry import trace
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            from opentelemetry.sdk.resources import Resource
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor

            resource = Resource.create(
                {"service.name": settings.otel_service_name or "cinetag-api"}
            )
            provider = TracerProvider(resource=resource)
            exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint)
            provider.add_span_processor(BatchSpanProcessor(exporter))
            trace.set_tracer_provider(provider)
            _LOG.info("otel_otlp_exporter_configured")
        except Exception:
            _LOG.warning("otel_otlp_configure_failed", exc_info=True)
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)
        _LOG.info("otel_fastapi_instrumented")
    except Exception:
        _LOG.warning("otel_fastapi_instrumentation_unavailable", exc_info=True)
    try:
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

        SQLAlchemyInstrumentor().instrument(engine=get_engine())
        _LOG.info("otel_sqlalchemy_instrumented")
    except Exception:
        _LOG.warning("otel_sqlalchemy_instrumentation_unavailable", exc_info=True)
