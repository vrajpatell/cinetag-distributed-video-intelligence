from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get('/health')
def health():
    return {'status': 'ok', 'env': settings.app_env}


@router.get('/ready')
def ready():
    return {'status': 'ready', 'env': settings.app_env}
