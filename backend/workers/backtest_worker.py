from workers.celery_app import celery_app


@celery_app.task(name="workers.backtest_worker.run_backtest")
def run_backtest(session_id: str):
    return {"session_id": session_id, "status": "completed"}
