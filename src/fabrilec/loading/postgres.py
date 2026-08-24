import os

import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.environ["DB_HOST"],
    "port": os.environ["DB_PORT"],
    "dbname": os.environ["DB_NAME"],
    "user": os.environ["DB_USER"],
    "password": os.environ["DB_PASSWORD"],
}


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def load_document(conn, tender_ref: str, relative_path: str, extraction_result: dict):
    
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO raw_documents
                (tender_ref, relative_path, source_path, extension,
                 extraction_method, text, char_count, n_pages, error, loaded_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (tender_ref, relative_path)
            DO UPDATE SET
                source_path = EXCLUDED.source_path,
                extension = EXCLUDED.extension,
                extraction_method = EXCLUDED.extraction_method,
                text = EXCLUDED.text,
                char_count = EXCLUDED.char_count,
                n_pages = EXCLUDED.n_pages,
                error = EXCLUDED.error,
                loaded_at = NOW();
            """,
            (
                tender_ref,
                relative_path,
                extraction_result.get("source_path"),
                extraction_result.get("extension"),
                extraction_result.get("method"),
                extraction_result.get("text"),
                extraction_result.get("char_count"),
                extraction_result.get("n_pages"),
                extraction_result.get("error"),
            ),
        )
    conn.commit()

