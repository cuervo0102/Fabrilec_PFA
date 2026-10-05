import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ["ANONYMIZED_TELEMETRY"] = "False"

import streamlit as st
from src.fabrilec.extraction.router import discover_files, extract_file
from src.fabrilec.loading.postgres import get_connection, load_document

EXTRACTED_ROOT = Path(PROJECT_ROOT) / "data" / "extracted"


def extract_all_zips(zip_bytes, dest_dir):
    """Extract a zip, then recursively extract any .zip files found inside it."""
    with zipfile.ZipFile(zip_bytes) as z:
        z.extractall(dest_dir)

    for _ in range(3):
        nested_zips = list(Path(dest_dir).rglob("*.zip"))
        if not nested_zips:
            break
        for nested_zip in nested_zips:
            nested_dir = nested_zip.with_suffix("")
            nested_dir.mkdir(exist_ok=True)
            try:
                with zipfile.ZipFile(nested_zip) as z:
                    z.extractall(nested_dir)
                try:
                    nested_zip.unlink()
                except PermissionError:
                    pass
            except zipfile.BadZipFile:
                pass


st.set_page_config(page_title="Nouveau dossier - Fabrilec - Airflow", page_icon="📁")
st.title("Ajouter un nouveau dossier")

tender_name = st.text_input("Nom du dossier (ex: AOO 310-2026)")
uploaded_zip = st.file_uploader("Fichier ZIP", type="zip")

if st.button("Lancer le traitement complet", disabled=not (tender_name and uploaded_zip)):

 
    dossier_path = EXTRACTED_ROOT / tender_name
    if dossier_path.exists():
        st.warning(f"'{tender_name}' existe déjà — écrasement.")
        shutil.rmtree(dossier_path)
    dossier_path.mkdir(parents=True)
    extract_all_zips(uploaded_zip, dossier_path)
    st.success(f"ZIP extrait dans {dossier_path}")

    st.subheader("Extraction du contenu")
    extracted_docs = []
    progress = st.progress(0)
    files = list(discover_files(str(dossier_path)))
    for i, (full_path, relative_path) in enumerate(files):
        result = extract_file(full_path)
        result["relative_path"] = f"{tender_name}/{relative_path}"
        result["tender_ref"] = tender_name
        extracted_docs.append(result)
        st.write(f"- {relative_path} — méthode: `{result['method']}`, {result['char_count']} caractères")
        progress.progress((i + 1) / len(files))
    st.success(f"{len(extracted_docs)} fichiers traités")

    # --- 3. Chargement dans Postgres ---
    st.subheader("Chargement dans Postgres")
    conn = get_connection()
    loaded, failed = 0, 0
    progress2 = st.progress(0)
    for i, doc in enumerate(extracted_docs):
        try:
            load_document(conn, tender_name, doc["relative_path"], doc)
            loaded += 1
        except Exception as e:
            failed += 1
            st.error(f"Échec du chargement pour {doc['relative_path']} : {e}")
        progress2.progress((i + 1) / len(extracted_docs))
    conn.close()
    st.success(f"{loaded} documents chargés dans Postgres" + (f", {failed} échecs" if failed else ""))

    # --- 4. dbt run ---
    with st.status("Exécution de dbt...", expanded=True) as status:
        result = subprocess.run(
            ["dbt", "run", "--project-dir", "fabrilec_dbt", "--profiles-dir", "fabrilec_dbt", "--target", "dev"],
            capture_output=True, text=True, timeout=300, cwd=PROJECT_ROOT,
        )
        st.code(result.stdout[-3000:] or "(pas de sortie standard)")
        if result.returncode != 0:
            st.code(result.stderr[-2000:])
            status.update(label="dbt a échoué ❌", state="error")
            st.stop()
        status.update(label="dbt terminé ✅", state="complete")

    # --- 5. Reconstruction de l'index RAG ---
    with st.status("Reconstruction de l'index RAG (peut prendre quelques minutes)...", expanded=True) as status:
        result = subprocess.run(
            [sys.executable, "-m", "src.fabrilec.rag.build_index"],
            capture_output=True, text=True, timeout=900, cwd=PROJECT_ROOT,
        )
        st.code(result.stdout[-3000:] or "(pas de sortie standard)")
        if result.returncode != 0:
            st.code(result.stderr[-2000:])
            status.update(label="Reconstruction de l'index échouée ❌", state="error")
            st.stop()
        status.update(label="Index RAG reconstruit ✅", state="complete")

    st.success(f"✅ Dossier '{tender_name}' entièrement traité. Vous pouvez maintenant l'interroger dans l'assistant.")