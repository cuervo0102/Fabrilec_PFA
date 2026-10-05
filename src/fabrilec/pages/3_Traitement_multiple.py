import os
import zipfile
import tempfile
import shutil
import streamlit as st
from src.fabrilec.airflow_client import trigger_dag_run, wait_for_completion, AirflowTriggerError

from src.fabrilec.config import EXTRACTED_ROOT

st.title("Ajouter plusieurs dossiers (traitement par Airflow)")
st.write(
    "Téléversez plusieurs archives ZIP en une fois. Chaque archive est extraite, "
    "puis toutes sont traitées ensemble par Airflow (extraction du contenu, "
    "chargement, dbt, indexation), en parallèle."
)

uploaded_files = st.file_uploader(
    "Archives ZIP (une par dossier)", type="zip", accept_multiple_files=True
)

if uploaded_files:
    st.write(f"{len(uploaded_files)} archive(s) sélectionnée(s) :")
    dossier_names = []
    for f in uploaded_files:
        default_name = os.path.splitext(f.name)[0]
        name = st.text_input(f"Nom du dossier pour « {f.name} »", value=default_name, key=f.name)
        dossier_names.append((f, name.strip()))

    if st.button("Extraire et lancer le traitement par lot"):
        try:
            with st.spinner("Extraction des archives..."):
                for f, name in dossier_names:
                    if not name:
                        st.error(f"Nom de dossier vide pour {f.name}, opération annulée.")
                        st.stop()
                    target_dir = os.path.join(EXTRACTED_ROOT, name)
                    if os.path.exists(target_dir):
                        st.error(f"Le dossier « {name} » existe déjà, choisissez un autre nom.")
                        st.stop()
                    os.makedirs(target_dir, exist_ok=True)
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
                        tmp.write(f.getbuffer())
                        tmp_path = tmp.name
                    with zipfile.ZipFile(tmp_path, "r") as zf:
                        zf.extractall(target_dir)
                    os.remove(tmp_path)

            names_only = [name for _, name in dossier_names]
            st.success(f"Extraction terminée pour : {', '.join(names_only)}")

            with st.spinner("Déclenchement du traitement Airflow..."):
                run_id = trigger_dag_run(target_dossiers=names_only)
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
                lines = [
                    f"- **{tid}** : {c['success']} réussi(s), {c['running']} en cours, "
                    f"{c['queued']} en attente, {c['failed']} échoué(s)"
                    for tid, c in summary.items()
                ]
                tasks_area.markdown("\n".join(lines))

            if final_state == "success":
                st.success("Tous les dossiers ont été traités avec succès.")
            else:
                st.error("Le traitement a échoué pour au moins un dossier. Consultez l'interface Airflow.")
                st.link_button("Ouvrir Airflow", "http://localhost:8081")

        except AirflowTriggerError as e:
            st.error(f"Impossible de déclencher le pipeline : {e}")
        except Exception as e:
            st.error(f"Erreur inattendue : {e}")