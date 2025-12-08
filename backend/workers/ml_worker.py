from workers.celery_app import celery_app


@celery_app.task(name="workers.ml_worker.train_model")
def train_model(model_id: str):
    return {"model_id": model_id, "status": "trained"}
