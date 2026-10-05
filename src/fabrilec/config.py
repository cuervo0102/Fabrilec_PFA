from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHROMA_PATH = str(PROJECT_ROOT / "data" / "chroma_db")
BM25_CACHE_PATH = str(Path(CHROMA_PATH) / "bm25_index.pkl")
EXTRACTED_ROOT = str(PROJECT_ROOT / "data" / "raw_dossiers" / "extracted")