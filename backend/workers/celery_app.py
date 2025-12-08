from celery import Celery

from app.config import get_settings


settings = get_settings()

celery_app = Celery(
    "forex_ai",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.task_routes = {
    "workers.backtest_worker.*": {"queue": "backtest"},
    "workers.ml_worker.*": {"queue": "ml"},
}
