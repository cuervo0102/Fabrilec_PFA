import streamlit as st
from src.fabrilec.airflow_client import trigger_dag_run, wait_for_completion, AirflowTriggerError

st.title("Traitement par lot (Airflow)")
st.write(
    "Cette page déclenche le pipeline complet sur tous les dossiers présents "
    "dans le répertoire source. Utilisez-la pour traiter plusieurs dossiers "
    "à la fois ; pour un seul dossier, préférez la page « Nouveau dossier »."
)

if st.button("Lancer le traitement par lot"):
    try:
        with st.spinner("Déclenchement du DAG Airflow..."):
            run_id = trigger_dag_run()
        st.success(f"Run déclenché : {run_id}")

        status_area = st.empty()
        tasks_area = st.empty()

        final_state = None
        for dag_state, tasks in wait_for_completion(run_id, poll_interval=5):
            final_state = dag_state
            status_area.info(f"État du run : **{dag_state}**")

            summary = {}
            for t in tasks:
                key = t["task_id"]
                summary.setdefault(key, {"success": 0, "failed": 0, "running": 0, "queued": 0, "other": 0})
                state = t.get("state") or "other"
                if state in summary[key]:
                    summary[key][state] += 1
                else:
                    summary[key]["other"] += 1

            lines = []
            for task_id, counts in summary.items():
                lines.append(
                    f"- **{task_id}** : "
                    f"{counts['success']} réussi(s), "
                    f"{counts['running']} en cours, "
                    f"{counts['queued']} en attente, "
                    f"{counts['failed']} échoué(s)"
                )
            tasks_area.markdown("\n".join(lines))

        if final_state == "success":
            st.success("Traitement par lot terminé avec succès.")
        else:
            st.error("Le traitement par lot a échoué. Consultez l'interface Airflow pour le détail.")
            st.link_button("Ouvrir Airflow", "http://localhost:8081")

    except AirflowTriggerError as e:
        st.error(f"Impossible de déclencher le pipeline : {e}")
    except Exception as e:
        st.error(f"Erreur inattendue : {e}")