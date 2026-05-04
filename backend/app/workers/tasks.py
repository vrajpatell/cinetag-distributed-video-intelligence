from celery import Celery
from app.core.config import settings
celery = Celery(__name__, broker=settings.broker_url, backend=settings.result_backend)
@celery.task(name='run_pipeline')
def run_pipeline(job_id:int):
    return {"job_id":job_id, "status":"queued"}
