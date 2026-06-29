from celery import Celery

from ..core.config import settings

celery_app = Celery("waypilot", broker=settings.redis_url, backend=settings.redis_url)
