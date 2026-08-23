import os
from datetime import datetime

from airflow.sdk import dag, task

EXTRACTED_ROOT = "/opt/airflow/data/raw_dossiers/extracted"


@dag(
    dag_id="fabrilec_ingestion_pipeline",
    schedule=None, 
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["fabrilec", "ingestion"],
)
def fabrilec_ingestion_pipeline():

    @task
    def list_dossiers() -> list[str]:
        if not os.path.isdir(EXTRACTED_ROOT):
            raise FileNotFoundError(f"Extracted dossiers folder not found: {EXTRACTED_ROOT}")
        return sorted(
            d for d in os.listdir(EXTRACTED_ROOT)
            if os.path.isdir(os.path.join(EXTRACTED_ROOT, d))
        )

    @task
    def process_dossier(dossier: str) -> dict:
        from src.fabrilec.extraction.router import discover_files, extract_file
        from src.fabrilec.loading.postgres import get_connection, load_document

        dossier_path = os.path.join(EXTRACTED_ROOT, dossier)
        files = list(discover_files(dossier_path))

        method_counts = {}
        failures = []

        conn = get_connection()
        try:
            for full_path, relative_path in files:
                try:
                    result = extract_file(full_path)
                except Exception as e:
                    failures.append({"file": relative_path, "error": str(e)})
                    continue

                method_counts[result["method"]] = method_counts.get(result["method"], 0) + 1
                if result.get("error"):
                    failures.append({"file": relative_path, "error": result["error"]})

                try:
                    load_document(conn, dossier, relative_path, result)
                except Exception as e:
                    conn.rollback()
                    failures.append({"file": relative_path, "error": f"load error: {e}"})
        finally:
            conn.close()

        return {
            "dossier": dossier,
            "n_files": len(files),
            "method_counts": method_counts,
            "failures": failures,
        }

    dossiers = list_dossiers()
    process_dossier.expand(dossier=dossiers)


fabrilec_ingestion_pipeline()