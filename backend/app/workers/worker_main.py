import logging
import signal
import sys

from app.bootstrap import ensure_preload

ensure_preload()

from app.core.config import settings  # noqa: E402
from app.db.session import get_engine  # noqa: E402
from app.workers.tasks import celery  # noqa: E402

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


def _shutdown(*_args):
    logger.info("worker shutdown requested")
    sys.exit(0)


def main() -> None:
    logger.info(
        "starting worker",
        extra={"app_env": settings.app_env, "queue_backend": settings.queue_backend},
    )
    with get_engine().connect() as conn:
        from sqlalchemy import text

        conn.execute(text("SELECT 1"))
    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)
    celery.worker_main(
        argv=[
            "worker",
            "--loglevel",
            settings.log_level.lower(),
            "--pool",
            settings.worker_pool,
            "--concurrency",
            str(settings.worker_concurrency),
        ]
    )


if __name__ == "__main__":
    main()
