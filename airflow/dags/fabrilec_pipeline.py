import os
from datetime import datetime

from airflow.sdk import dag, task


EXTRACTED_ROOT = "/opt/airflow/data/raw_dossiers/extracted"


@dag(
    dag_id="fabrilec_ingestion_pipeline",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["fabrilec", "ingestion"],
)
def fabrilec_ingestion_pipeline():

    @task
    def list_dossiers(**context) -> list[str]:
        if not os.path.isdir(EXTRACTED_ROOT):
            raise FileNotFoundError(f"Extracted dossiers folder not found: {EXTRACTED_ROOT}")

        dag_run = context.get("dag_run")
        conf = dag_run.conf or {} if dag_run else {}
        targets = conf.get("target_dossiers")  

        if targets:
            missing = [t for t in targets if not os.path.isdir(os.path.join(EXTRACTED_ROOT, t))]
            if missing:
                raise FileNotFoundError(f"Requested dossiers not found: {missing}")
            return targets

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

    @task
    def run_dbt() -> str:
        """Run dbt build (models + tests) after all dossiers are loaded.
        Runs only once, after every process_dossier task has completed."""
        import subprocess

        result = subprocess.run(
            ["dbt", "build", "--project-dir", "/opt/airflow/dbt/fabrilec_dbt",
             "--profiles-dir", "/opt/airflow/dbt/fabrilec_dbt", "--target", "docker"],
            capture_output=True, text=True,
        )
        print(result.stdout)
        if result.returncode != 0:
            print(result.stderr)
            raise RuntimeError(f"dbt build failed with exit code {result.returncode}")
        return "dbt build succeeded"

    @task
    def rebuild_rag_index() -> str:
        """Rechunk and re-embed all reliably-extracted documents into Chroma.
        Runs after dbt, since it reads from dbt's stg_raw_documents model."""
        from src.fabrilec.rag.build_index import main as build_index_main

        build_index_main()
        return "RAG index rebuilt"

    dossiers = list_dossiers()
    processed = process_dossier.expand(dossier=dossiers)

    processed >> run_dbt() >> rebuild_rag_index()


fabrilec_ingestion_pipeline()