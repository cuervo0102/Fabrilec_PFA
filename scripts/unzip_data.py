import os
import zipfile

downloads = r"C:\Users\DELL\Desktop\PythonFaberlic_Project\data\raw_dossiers"
extracted_root = r"C:\Users\DELL\Desktop\PythonFaberlic_Project\data\raw_dossiers\extracted"
zip_names = [
    "10006779-1R.zip",
    "10008361.zip",
    "10009955.zip",
    "AO 15 DR4 2026.zip",
    "AO 254-26-ELEC A PUBLIER.zip",
    "AOO 299-26  Pour Publication.zip",
    "AOO 308-2026 DAO au PMMP.zip",
    "CCH TC4130723 Extension poste 22560 KV Benslimane II.zip",
    "DCE 03-2026-CLE DEF INSERT DEF.zip",
    "DOSSIER AO 122-EL-26.zip",
    "Dossier d'AO n° TS4130670.zip",
    "marché n°2 éléctrification.zip",
    "offre.zip",
    "PMMP 10008419.zip",
    "PMMP 10009032.zip",
    "PMMP 10009604.zip",
    "PMMP 10009856.zip",
    "TC4130724.zip",
    "09-2026.zip",
    "10005533-2R.zip",
]

os.makedirs(extracted_root, exist_ok=True)
all_extracted_folders = []

for name in zip_names:
    path = os.path.join(downloads, name)
    if not os.path.exists(path):
        print(f"MISSING: {path}")
        continue
    if zipfile.is_zipfile(path):
        target_folder = os.path.join(extracted_root, os.path.splitext(name)[0])
        os.makedirs(target_folder, exist_ok=True)
        with zipfile.ZipFile(path, "r") as zip_ref:
            zip_ref.extractall(target_folder)
        all_extracted_folders.append(target_folder)
        print(f"OK: {name} -> {target_folder}")
    else:
        print(f"NOT A VALID ZIP: {path}")

print(f"\n{len(all_extracted_folders)}/{len(zip_names)} extracted successfully")