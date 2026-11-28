"""Open-source MLflow tracking (D-084). Local database; the UI runs on the owner's laptop:
    mlflow ui --backend-store-uri sqlite:///mlflow.db
"""
import json
import os
import tempfile
import mlflow

def setup(root="."):
    mlflow.set_tracking_uri(f"sqlite:///{os.path.abspath(os.path.join(root, 'mlflow.db'))}")
    mlflow.set_experiment("late-payment-stage1")

def log_run(name, params, metrics, source="notebook", artifacts=(), card=None):
    with mlflow.start_run(run_name=name) as run:
        mlflow.set_tag("source", source)
        mlflow.log_params(params)
        mlflow.log_metrics({k: float(v) for k, v in metrics.items()})
        for path in artifacts:
            mlflow.log_artifact(path)
        if card:
            with tempfile.TemporaryDirectory() as d:
                p = os.path.join(d, "model_card.json"); json.dump(card, open(p, "w"), indent=2, default=str)
                mlflow.log_artifact(p)
        return run.info.run_id
