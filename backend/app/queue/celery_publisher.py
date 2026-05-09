from app.workers.tasks import run_pipeline


def publish_celery_job(job_id: int) -> None:
    run_pipeline.delay(job_id)
