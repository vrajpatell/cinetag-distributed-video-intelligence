import atexit
import logging
import os
import signal
import subprocess
import threading
from typing import Any

import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.secrets import preload_known_secrets

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


class WorkerRuntime:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._process: subprocess.Popen[str] | None = None
        self._stop_requested = False
        self._healthy = False

    def start(self) -> None:
        with self._lock:
            if self._process is not None:
                return
            logger.info('starting background worker process')
            self._process = subprocess.Popen(
                ['python', '-m', 'app.workers.worker_main'],
                stdout=None,
                stderr=None,
                text=True,
            )
            self._healthy = True

    def poll(self) -> int | None:
        proc = self._process
        if proc is None:
            return None
        code = proc.poll()
        if code is not None:
            with self._lock:
                self._healthy = False
        return code

    def healthy(self) -> bool:
        proc = self._process
        if proc is None:
            return False
        if proc.poll() is not None:
            with self._lock:
                self._healthy = False
            return False
        return self._healthy

    def stop(self) -> None:
        with self._lock:
            if self._stop_requested:
                return
            self._stop_requested = True
            proc = self._process

        if proc is None:
            return

        logger.info('stopping background worker process')
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                logger.warning('worker process did not exit in time; killing')
                proc.kill()
                proc.wait(timeout=5)
        logger.info('worker process exited', extra={'exit_code': proc.returncode})


runtime = WorkerRuntime()


def create_app() -> FastAPI:
    app = FastAPI(title='cinetag-worker-health', docs_url=None, redoc_url=None, openapi_url=None)

    @app.get('/health')
    def health() -> dict[str, str]:
        return {'status': 'ok'}

    @app.get('/ready')
    def ready() -> Any:
        if runtime.healthy():
            return {'status': 'ok'}
        return JSONResponse(status_code=503, content={'status': 'unhealthy'})

    return app


app = create_app()


def _shutdown_handler(signum: int, _frame: Any) -> None:
    logger.info('received signal, shutting down worker service', extra={'signal': signum})
    runtime.stop()


def main() -> None:
    preload_known_secrets()
    runtime.start()

    signal.signal(signal.SIGTERM, _shutdown_handler)
    signal.signal(signal.SIGINT, _shutdown_handler)
    atexit.register(runtime.stop)

    port = int(os.getenv('PORT', '8080'))
    logger.info('starting worker health server', extra={'host': '0.0.0.0', 'port': port})
    uvicorn.run(app, host='0.0.0.0', port=port, log_level=settings.log_level.lower())

    # If server exits, ensure worker is shutdown and propagate failure when worker crashed.
    exit_code = runtime.poll()
    runtime.stop()
    if exit_code not in (None, 0):
        raise SystemExit(exit_code)


if __name__ == '__main__':
    main()
