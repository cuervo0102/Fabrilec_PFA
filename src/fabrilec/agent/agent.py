import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"



import json
import psycopg2
from dotenv import load_dotenv

from src.fabrilec.agent.llm_clients import generate
from src.fabrilec.rag.hybrid_retrieval import HybridRetriever

load_dotenv()

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
    results = retriever.search(query, top_k=5)
    if not results:
        return "Aucun résultat trouvé."

    formatted = []
    for r in results:
        meta = r["metadata"]
        formatted.append(
            f"[Tender: {meta['tender_ref']} | Document: {meta['document_type']} | {meta['relative_path']}]\n"
            f"{r['text'][:800]}"
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


SYSTEM_PROMPT = (
    "Tu es l'assistant Fabrilec pour les dossiers d'appels d'offres (CCTP, CPS, RC, bordereaux des prix). "
    "Réponds en français, uniquement à partir des résultats des outils. "
    "Cite la référence du dossier (tender_ref) et le type de document quand tu t'appuies sur un extrait. "
    "Si les résultats ne contiennent pas l'information, dis-le clairement au lieu d'inventer. "
    "Utilise query_database pour les questions de comptage ou de métadonnées sur un dossier précis, "
    "et search_documents pour le contenu des documents."
    "Recopie les nombres exactement comme dans l'extrait. Si un nombre semble incohérent "
    "(par exemple une virgule manquante), signale-le explicitement au lieu de le corriger. "
    "Si query_database ne trouve aucun dossier, utilise search_documents avant de répondre. "
    "Si la question ne concerne pas les dossiers d'appels d'offres, réponds poliment que tu ne peux "
    "aider que sur ces dossiers, sans répondre à la question. Vouvoie toujours l'utilisateur. "
    "Si une question mentionne une référence de dossier précise, vérifie toujours son existence "
    "avec query_database avant de répondre, même si la question porte sur le contenu. "
    "N'affirme jamais qu'un dossier n'existe pas uniquement parce que search_documents n'a rien "
    "trouvé : cela signifie seulement que le contenu recherché n'a pas été localisé, pas que le "
    "dossier est absent. Seul un résultat 'Aucun dossier trouvé' de query_database confirme "
    "l'absence d'un dossier. Si search_documents ne trouve rien pour un dossier existant, dis-le "
    "clairement (le dossier existe mais l'extrait demandé n'a pas été trouvé) plutôt que de nier "
    "son existence."
)


def _parse_args(raw) -> dict:
    """OpenAI-style tool calls give arguments as a JSON string (Ollama gave a dict)."""
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}


def _run_tool(func_name: str, func_args: dict) -> str:
    func = AVAILABLE_FUNCTIONS.get(func_name)
    if func is None:
        return f"Erreur: outil inconnu '{func_name}'"

    if func_name == "search_documents":
        arg_value = func_args.get("query") or next(iter(func_args.values()), "")
    elif func_name == "query_database":
        arg_value = func_args.get("tender_ref") or func_args.get("query") or next(iter(func_args.values()), "")
    else:
        arg_value = next(iter(func_args.values()), "")

    try:
        return func(arg_value)
    except Exception as e:  # a DB or index error should not crash the agent loop
        return f"Erreur lors de l'exécution de {func_name}: {e}"


def ask_with_trace(question: str, max_rounds: int = 3) -> dict:
    """Run the agent and also return what the tools produced (needed by the judge)."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    contexts, tool_calls_log = [], []

    for round_no in range(max_rounds):
        last_round = round_no == max_rounds - 1
        # On the last round, forbid new tool calls so the model must answer.
        response = generate(messages, tools=TOOLS, tool_choice="none" if last_round else "auto")
        msg = response.choices[0].message

        if not msg.tool_calls:
            return {"answer": msg.content or "", "contexts": contexts, "tool_calls": tool_calls_log}

        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {
                    "id": c.id,
                    "type": "function",
                    "function": {"name": c.function.name, "arguments": c.function.arguments},
                }
                for c in msg.tool_calls
            ],
        })

        for call in msg.tool_calls:
            args = _parse_args(call.function.arguments)
            result = _run_tool(call.function.name, args)
            contexts.append(result)
            tool_calls_log.append({"name": call.function.name, "args": args})
            messages.append({"role": "tool", "tool_call_id": call.id, "content": result})

    return {
        "answer": "Désolé, je n'ai pas pu formuler de réponse complète.",
        "contexts": contexts,
        "tool_calls": tool_calls_log,
    }


def ask(question: str, max_rounds: int = 3) -> str:
    return ask_with_trace(question, max_rounds)["answer"]


if __name__ == "__main__":
    test_questions = [
        "Combien de documents contient le dossier 254/26/ELEC ?",
        "Que dit le CCTP à propos des câbles BT armés ?",
    ]
    for q in test_questions:
        print(f"Q: {q}")
        print(f"A: {ask(q)}\n")