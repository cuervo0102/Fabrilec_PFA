import os
import psycopg2
from dotenv import load_dotenv
import chromadb
from sentence_transformers import SentenceTransformer

load_dotenv()

CHUNK_SIZE = 1500
CHUNK_OVERLAP = 200
CHROMA_PATH = "data/chroma_db"
COLLECTION_NAME = "fabrilec_tenders"


def get_connection():
    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=os.environ["DB_PORT"],
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    )


def fetch_documents(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, tender_ref, relative_path, document_type, extraction_quality, char_count
            FROM dbt_fab.stg_raw_documents
            WHERE extraction_quality != 'echec'
            ORDER BY tender_ref, relative_path;
        """)
        rows = cur.fetchall()

    docs = []
    with conn.cursor() as cur:
        for doc_id, tender_ref, relative_path, document_type, extraction_quality, char_count in rows:
            cur.execute("SELECT text FROM raw_documents WHERE id = %s;", (doc_id,))
            text = cur.fetchone()[0]
            docs.append({
                "id": doc_id,
                "tender_ref": tender_ref,
                "relative_path": relative_path,
                "document_type": document_type,
                "extraction_quality": extraction_quality,
                "text": text or "",
            })
    return docs


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP):
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


def main():
    print("Connecting to Postgres...")
    conn = get_connection()
    docs = fetch_documents(conn)
    conn.close()
    print(f"Fetched {len(docs)} reliably-extracted documents.")

    print("Loading embedding model (first run downloads it, may take a minute)...")
    model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

    client = chromadb.PersistentClient(path=CHROMA_PATH)
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.create_collection(COLLECTION_NAME)

    all_chunks, all_ids, all_metadatas = [], [], []
    for doc in docs:
        chunks = chunk_text(doc["text"])
        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc['id']}_{i}"
            all_chunks.append(chunk)
            all_ids.append(chunk_id)
            all_metadatas.append({
                "tender_ref": doc["tender_ref"],
                "relative_path": doc["relative_path"],
                "document_type": doc["document_type"],
                "extraction_quality": doc["extraction_quality"],
                "chunk_index": i,
            })

    print(f"Built {len(all_chunks)} chunks across {len(docs)} documents. Embedding...")

    batch_size = 64
    for i in range(0, len(all_chunks), batch_size):
        batch_chunks = all_chunks[i:i + batch_size]
        batch_ids = all_ids[i:i + batch_size]
        batch_meta = all_metadatas[i:i + batch_size]
        embeddings = model.encode(batch_chunks, show_progress_bar=False).tolist()
        collection.add(
            ids=batch_ids,
            embeddings=embeddings,
            documents=batch_chunks,
            metadatas=batch_meta,
        )
        print(f"  Embedded {min(i + batch_size, len(all_chunks))}/{len(all_chunks)} chunks")

    print(f"Done. Chroma collection '{COLLECTION_NAME}' has {collection.count()} chunks.")


if __name__ == "__main__":
    main()