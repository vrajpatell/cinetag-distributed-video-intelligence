import logging
import signal
import sys

from app.core.config import settings
from app.core.secrets import preload_known_secrets
from app.db.session import engine
from app.workers.tasks import celery

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


def _shutdown(*_args):
    logger.info('worker shutdown requested')
    sys.exit(0)


def main() -> None:
    preload_known_secrets()
    logger.info('starting worker', extra={'app_env': settings.app_env, 'queue_backend': settings.queue_backend})
    with engine.connect() as conn:
        from sqlalchemy import text
        conn.execute(text('SELECT 1'))
    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)
    celery.worker_main(
        argv=[
            'worker',
            '--loglevel',
            settings.log_level.lower(),
            '--pool',
            settings.worker_pool,
            '--concurrency',
            str(settings.worker_concurrency),
        ]
    )


if __name__ == '__main__':
    main()
