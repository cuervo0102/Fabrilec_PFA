import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"



import json
import ollama
import psycopg2
from dotenv import load_dotenv

from src.fabrilec.rag.hybrid_retrieval import HybridRetriever

load_dotenv()

MODEL = "llama3.1"

_retriever = None  

def get_retriever():
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever()
    return _retriever


def get_db_connection():
    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=os.environ["DB_PORT"],
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    )


def search_documents(query: str) -> str:
    retriever = get_retriever()
    results = retriever.search(query, top_k=3)
    if not results:
        return "Aucun résultat trouvé."

    formatted = []
    for r in results:
        meta = r["metadata"]
        formatted.append(
            f"[Tender: {meta['tender_ref']} | Document: {meta['document_type']} | {meta['relative_path']}]\n"
            f"{r['text'][:500]}"
        )
    return "\n\n---\n\n".join(formatted)


def query_database(tender_ref: str) -> str:
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT tender_ref, n_documents, n_fiable, n_ocr_a_verifier, n_echec,
                       has_cctp, has_cps, has_rc, has_bordereau_prix
                FROM dbt_fab.mart_documents_summary
                WHERE regexp_replace(tender_ref, '[^a-zA-Z0-9]', '', 'g')
                      ILIKE '%%' || regexp_replace(%s, '[^a-zA-Z0-9]', '', 'g') || '%%';
            """, (tender_ref,))
            row = cur.fetchone()
    finally:
        conn.close()

    if not row:
        return f"Aucun dossier trouvé correspondant à '{tender_ref}'."

    ref, n_docs, n_fiable, n_ocr, n_echec, has_cctp, has_cps, has_rc, has_bordereau = row
    return (
        f"Dossier: {ref}\n"
        f"Documents: {n_docs} (fiables: {n_fiable}, OCR à vérifier: {n_ocr}, échecs: {n_echec})\n"
        f"Contient CCTP: {has_cctp}, CPS: {has_cps}, RC: {has_rc}, Bordereau des prix: {has_bordereau}"
    )

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": (
                "Search the CONTENT of tender documents for conceptual or descriptive questions -- "
                "e.g. 'what does the CCTP say about delivery deadlines', 'find clauses about penalties'. "
                "Use this when the question is about WHAT a document says, not about counts or metadata."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query, in French, describing what content to find."}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_database",
            "description": (
                "Look up structured metadata for a SPECIFIC tender by its reference number/name -- "
                "e.g. 'how many documents does tender 254/26/ELEC have', 'does tender 09-2026 have a CCTP'. "
                "Use this when the question names a specific tender_ref and asks about counts, quality, or which document types exist."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "tender_ref": {"type": "string", "description": "The tender reference or folder name to look up, e.g. '254/26/ELEC' or '09-2026'."}
                },
                "required": ["tender_ref"],
            },
        },
    },
]

AVAILABLE_FUNCTIONS = {
    "search_documents": search_documents,
    "query_database": query_database,
}


def ask(question: str) -> str:
    messages = [{"role": "user", "content": question}]

    response = ollama.chat(model=MODEL, messages=messages, tools=TOOLS)
    tool_calls = response["message"].get("tool_calls")

    if not tool_calls:
        return response["message"]["content"]

    messages.append(response["message"])

    for call in tool_calls:
        func_name = call["function"]["name"]
        func_args = call["function"]["arguments"]
        func = AVAILABLE_FUNCTIONS.get(func_name)

        if func is None:
            result = f"Erreur: outil inconnu '{func_name}'"
        else:
            if func_name == "search_documents":
                arg_value = func_args.get("query") or next(iter(func_args.values()), "")
            elif func_name == "query_database":
                arg_value = func_args.get("tender_ref") or func_args.get("query") or next(iter(func_args.values()), "")
            else:
                arg_value = next(iter(func_args.values()), "")
            result = func(arg_value)

        messages.append({"role": "tool", "content": result, "name": func_name})

    final_response = ollama.chat(model=MODEL, messages=messages, tools=TOOLS)
    return final_response["message"]["content"]


if __name__ == "__main__":
    test_questions = [
        "Combien de documents contient le dossier 254/26/ELEC ?",
        "Que dit le CCTP à propos des câbles BT armés ?",
    ]
    for q in test_questions:
        print(f"Q: {q}")
        print(f"A: {ask(q)}\n")