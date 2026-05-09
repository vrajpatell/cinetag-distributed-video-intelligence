from __future__ import annotations

import importlib.util
import os
import sysconfig


def publish_processing_job(job_id: int) -> None:
    # Lazy import avoids import cycles and keeps module import side effects low.
    from app.queue.publisher import publish_processing_job as _publish_processing_job

    _publish_processing_job(job_id)


def _load_stdlib_queue_symbols() -> None:
    """Expose stdlib queue symbols when this module is imported as `queue`.

    pytest sets `pythonpath=app`, so `import queue` from third-party libs can
    resolve to this package path. We mirror stdlib symbols to avoid breakage.
    """
    stdlib_queue_path = os.path.join(sysconfig.get_path("stdlib"), "queue.py")
    spec = importlib.util.spec_from_file_location("_stdlib_queue", stdlib_queue_path)
    if spec is None or spec.loader is None:
        return
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for symbol in ("Queue", "LifoQueue", "PriorityQueue", "SimpleQueue", "Empty", "Full"):
        if hasattr(module, symbol):
            globals()[symbol] = getattr(module, symbol)


_load_stdlib_queue_symbols()

__all__ = ["publish_processing_job", "Queue", "LifoQueue", "PriorityQueue", "SimpleQueue", "Empty", "Full"]
