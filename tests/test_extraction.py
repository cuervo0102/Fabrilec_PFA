import os

from src.fabrilec.extraction.router import discover_files, extract_file


DOSSIER_TO_TEST = r"data\raw_dossiers\extracted\09-2026"
def main():
    if not os.path.isdir(DOSSIER_TO_TEST):
        print(f"Folder not found: {DOSSIER_TO_TEST}")
        print("Edit DOSSIER_TO_TEST in this script to point at a real extracted dossier folder.")
        return

    files = list(discover_files(DOSSIER_TO_TEST))
    print(f"Found {len(files)} supported files in {DOSSIER_TO_TEST}\n")

    for full_path, relative_path in files:
        result = extract_file(full_path)
        print(f"- {relative_path}")
        print(f"    method: {result['method']}   chars: {result['char_count']}   pages: {result.get('n_pages')}")
        if result.get("error"):
            print(f"    ERROR: {result['error']}")
        if result["char_count"] > 0:
            preview = result["text"][:120].replace("\n", " ")
            print(f"    preview: {preview!r}")
        print()


if __name__ == "__main__":
    main()