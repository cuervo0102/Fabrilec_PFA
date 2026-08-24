import os
from collections import Counter

from src.fabrilec.extraction.router import discover_files, extract_file
from src.fabrilec.loading.postgres import get_connection, load_document

EXTRACTED_ROOT = r"data\raw_dossiers\extracted"


def main():
    if not os.path.isdir(EXTRACTED_ROOT):
        print(f"Folder not found: {EXTRACTED_ROOT}")
        return

    dossier_folders = sorted(
        d for d in os.listdir(EXTRACTED_ROOT)
        if os.path.isdir(os.path.join(EXTRACTED_ROOT, d))
    )
    print(f"Found {len(dossier_folders)} dossier folders\n")

    method_counts = Counter()
    failed_files = []
    total_files = 0

    conn = get_connection()
    try:
        for dossier in dossier_folders:
            dossier_path = os.path.join(EXTRACTED_ROOT, dossier)
            files = list(discover_files(dossier_path))
            print(f"=== {dossier} ({len(files)} files) ===")

            for full_path, relative_path in files:
                total_files += 1
                try:
                    result = extract_file(full_path)
                except Exception as e:
                    print(f"  CRASHED: {relative_path} -> {e}")
                    method_counts["crashed"] += 1
                    failed_files.append((dossier, relative_path, str(e)))
                    continue

                method_counts[result["method"]] += 1

                status = "OK" if result["char_count"] > 0 else "EMPTY/FAILED"
                print(f"  [{status}] {relative_path}  method={result['method']}  chars={result['char_count']}")

                if result.get("error"):
                    failed_files.append((dossier, relative_path, result["error"]))

                try:
                    load_document(conn, dossier, relative_path, result)
                except Exception as e:
                    print(f"    LOAD FAILED: {e}")
                    conn.rollback()
                    failed_files.append((dossier, relative_path, f"load error: {e}"))

            print()
    finally:
        conn.close()

    print("=" * 60)
    print(f"TOTAL FILES PROCESSED: {total_files}")
    print("METHOD BREAKDOWN:")
    for method, count in method_counts.most_common():
        print(f"  {method}: {count}")

    if failed_files:
        print(f"\nFAILURES/ERRORS ({len(failed_files)}):")
        for dossier, relative_path, error in failed_files:
            print(f"  [{dossier}] {relative_path}: {error}")
    else:
        print("\nNo failures.")


if __name__ == "__main__":
    main()