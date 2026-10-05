import datetime
import time
import os
import requests

AIRFLOW_BASE_URL = os.environ.get("AIRFLOW_BASE_URL", "http://localhost:8081")
AIRFLOW_API = f"{AIRFLOW_BASE_URL}/api/v2"
AIRFLOW_USER = os.environ.get("AIRFLOW_API_USER", "airflow")
AIRFLOW_PASSWORD = os.environ.get("AIRFLOW_API_PASSWORD")
DAG_ID = "fabrilec_ingestion_pipeline"


class AirflowTriggerError(Exception):
    pass


def _get_token() -> str:
    resp = requests.post(
        f"{AIRFLOW_BASE_URL}/auth/token",
        json={"username": AIRFLOW_USER, "password": AIRFLOW_PASSWORD},
        timeout=10,
    )
    if resp.status_code not in (200, 201):
        raise AirflowTriggerError(f"Auth failed ({resp.status_code}): {resp.text}")
    return resp.json()["access_token"]


def _headers() -> dict:
    return {"Authorization": f"Bearer {_get_token()}"}


def trigger_dag_run(target_dossiers: list[str] | None = None) -> str:
    logical_date = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {"logical_date": logical_date}
    if target_dossiers:
        payload["conf"] = {"target_dossiers": target_dossiers}
    resp = requests.post(
        f"{AIRFLOW_API}/dags/{DAG_ID}/dagRuns",
        json=payload,
        headers=_headers(),
        timeout=10,
    )
    if resp.status_code not in (200, 201):
        raise AirflowTriggerError(f"Trigger failed ({resp.status_code}): {resp.text}")
    return resp.json()["dag_run_id"]


def get_dag_run_state(dag_run_id: str) -> str:
    resp = requests.get(
        f"{AIRFLOW_API}/dags/{DAG_ID}/dagRuns/{dag_run_id}",
        headers=_headers(),
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["state"]


def get_task_instances(dag_run_id: str) -> list[dict]:
    resp = requests.get(
        f"{AIRFLOW_API}/dags/{DAG_ID}/dagRuns/{dag_run_id}/taskInstances",
        headers=_headers(),
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["task_instances"]


def wait_for_completion(dag_run_id: str, poll_interval: int = 5, timeout: int = 3600):
    elapsed = 0
    while elapsed < timeout:
        state = get_dag_run_state(dag_run_id)
        tasks = get_task_instances(dag_run_id)
        yield state, tasks
        if state in ("success", "failed"):
            return
        time.sleep(poll_interval)
        elapsed += poll_interval
    raise TimeoutError(f"DAG run {dag_run_id} did not finish within {timeout}s")