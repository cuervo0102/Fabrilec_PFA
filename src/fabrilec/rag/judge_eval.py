"""End-to-end evaluation of the agent's ANSWERS with an LLM judge.

eval_set.py measures retrieval (is the right tender in the top 3?).
This script measures the final answer: is it faithful to what the tools
returned, and is it correct?

Run from the project root:
    python -m src.fabrilec.rag.judge_eval

To also score correctness against a known answer, add a "reference" key to any
entry of QUESTIONS in eval_set.py (or to EXTRA below).
"""
import json
import os
import time

os.environ["ANONYMIZED_TELEMETRY"] = "False"

from src.fabrilec.agent.agent import ask_with_trace
from src.fabrilec.agent.llm_clients import judge
from src.fabrilec.rag.eval_set import QUESTIONS

# Real question/answer pairs. Fill "reference" when you know the true answer
# (e.g. the document count for a tender straight from Postgres).
EXTRA = [
    {
    "question": "Combien de documents contient le dossier 254/26/ELEC ?",
    "reference": "11 documents (11 fiables, 0 OCR à vérifier, 0 échec)",
    "expected_tender_ref": "254-26-ELEC",
},
{
    "question": "Que dit le CCTP à propos des câbles BT armés ?",
    "reference": None,
    "expected_text": "Câbles BT armés isolés",
},
]


PAUSE_S = 3  
REPORT_PATH = "data/judge_report.json"


def main():
    items = EXTRA + QUESTIONS
    rows = []

    for i, item in enumerate(items, 1):
        q = item["question"]
        try:
            trace = ask_with_trace(q)
            context = "\n\n---\n\n".join(trace["contexts"]) or "(aucun résultat d'outil)"
            verdict = judge(q, context, trace["answer"], item.get("reference"))
            expected = item.get("expected_tender_ref")
            row = {
                "question": q,
                "answer": trace["answer"],
                "tools": [c["name"] for c in trace["tool_calls"]],
                "expected_tender_in_context": (expected in context) if expected else None,
                **verdict,
                "contexts": trace["contexts"],
            }
        except Exception as e:  # keep going: one failure should not kill the run
            row = {"question": q, "error": str(e)}
        rows.append(row)

        status = "PASS" if row.get("faithful") and row.get("correct") else "FAIL"
        print(f"[{i}/{len(items)}] {status}  score={row.get('score')}  {q}")
        if status == "FAIL":
            print(f"      -> {row.get('reason') or row.get('error')}")
        time.sleep(PAUSE_S)

    graded = [r for r in rows if "error" not in r and r.get("faithful") is not None]
    n = len(graded) or 1
    print("=" * 60)
    print(f"Graded: {len(graded)}/{len(rows)}")
    print(f"Faithful: {sum(bool(r['faithful']) for r in graded) / n:.1%}")
    print(f"Correct:  {sum(bool(r['correct']) for r in graded) / n:.1%}")
    scores = [r["score"] for r in graded if isinstance(r.get("score"), (int, float))]
    if scores:
        print(f"Mean score: {sum(scores) / len(scores):.2f} / 5")
    print("=" * 60)

    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    print(f"Full report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
