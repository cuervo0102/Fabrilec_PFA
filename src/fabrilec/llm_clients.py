import json
import os
import time

from dotenv import load_dotenv
from openai import BadRequestError, InternalServerError, OpenAI, RateLimitError

load_dotenv()

PROVIDERS = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "key_env": "GROQ_API_KEY",
        "model": "qwen/qwen3.8-27b",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "key_env": "OPENROUTER_API_KEY",
        "model": "meta-llama/llama-3.3-70b-instruct:free",
    },
    "gemini": {  
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "key_env": "GEMINI_API_KEY",
        "model": "gemini-2.5-flash",  
    },
    "ollama": { 
        "base_url": "http://localhost:11434/v1",
        "key_env": "",
        "model": "llama3.1",
    },
}

GEN_PROVIDER = os.getenv("GEN_PROVIDER", "groq")
GEN_MODEL = os.getenv("GEN_MODEL", "") 
JUDGE_PROVIDER = os.getenv("JUDGE_PROVIDER", "groq")
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "openai/gpt-oss-120b" if JUDGE_PROVIDER == "groq" else "")


def chat(provider, messages, model="", tools=None, temperature=0.2, retries=5, **kwargs):
    """One chat completion, with backoff on 429 / 5xx (free tiers hit both)."""
    cfg = PROVIDERS[provider]
    client = OpenAI(
        base_url=cfg["base_url"],
        api_key=os.getenv(cfg["key_env"], "") if cfg["key_env"] else "ollama",
    )
    params = dict(
        model=model or cfg["model"],
        messages=messages,
        temperature=temperature,
        **kwargs,
    )
    if tools:
        params["tools"] = tools  

    bad_request_retried = False
    for attempt in range(retries):
        try:
            return client.chat.completions.create(**params)
        except (RateLimitError, InternalServerError):
            time.sleep(min(2 ** attempt, 30))
        except BadRequestError as e:
            
            if "tool_use_failed" in str(e) and not bad_request_retried:
                bad_request_retried = True
                continue
            raise
    raise RuntimeError(f"{provider}: still failing after {retries} tries")


def generate(messages, tools=None, **kwargs):
    """Use this wherever the code used to call ollama.chat()."""
    forced_answer = kwargs.get("tool_choice") == "none"
    resp = chat(GEN_PROVIDER, messages, model=GEN_MODEL, tools=tools, **kwargs)
    for _ in range(2):
        msg = resp.choices[0].message
        if msg.tool_calls or "<tool_call>" not in (msg.content or ""):
            return resp
        retry = messages
        if forced_answer:  
            retry = messages + [{
                "role": "user",
                "content": "Réponds maintenant en français, en texte normal, à partir "
                           "des résultats d'outils déjà obtenus. N'appelle plus d'outil. "
                           "Si l'information manque, dis-le clairement.",
            }]
        resp = chat(GEN_PROVIDER, retry, model=GEN_MODEL, tools=tools, **kwargs)
    msg = resp.choices[0].message
    if forced_answer and not msg.tool_calls and "<tool_call>" in (msg.content or ""):
        msg.content = "Je n'ai pas pu formuler de réponse à partir des résultats obtenus."
    return resp

JUDGE_SYSTEM = """Tu es un évaluateur strict d'un assistant RAG pour des appels d'offres
d'infrastructure électrique (HTB/HTA/BT, postes, CCTP, CPS, RC, bordereaux des prix).
Tu reçois une QUESTION, le CONTEXTE récupéré par les outils, la RÉPONSE de l'assistant
et, parfois, une RÉFÉRENCE. Réponds UNIQUEMENT avec ce JSON :
{"faithful": true|false, "correct": true|false, "score": 1-5, "reason": "<une phrase>"}
- faithful : chaque affirmation de la RÉPONSE est appuyée par le CONTEXTE (rien d'inventé).
- correct : la RÉPONSE est d'accord avec la RÉFÉRENCE sur les faits, nombres et unités.
  Sans RÉFÉRENCE, juge la justesse uniquement à partir du CONTEXTE.
- Si le CONTEXTE ne contient pas l'information et que la RÉPONSE le dit honnêtement,
  faithful=true et correct=true. Une réponse inventée dans ce cas est faithful=false.
Ne récompense ni la longueur ni le style. Sois strict sur les nombres, dates et unités."""


def judge(question, context, answer, reference=None):
    user = (
        f"QUESTION:\n{question}\n\nCONTEXTE:\n{context}\n\nRÉPONSE:\n{answer}\n\n"
        f"RÉFÉRENCE:\n{reference or '(aucune)'}"
    )
    resp = chat(
        JUDGE_PROVIDER,
        [{"role": "system", "content": JUDGE_SYSTEM}, {"role": "user", "content": user}],
        model=JUDGE_MODEL,
        temperature=0,
    )
    text = resp.choices[0].message.content or ""
    try:
        return json.loads(text[text.find("{"): text.rfind("}") + 1])
    except json.JSONDecodeError:
        return {"faithful": None, "correct": None, "score": None, "reason": f"unparseable: {text[:200]}"}
