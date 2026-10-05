import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"
from src.fabrilec.agent.agent import ask_with_trace

Q = "Dossier d'appel d'offres de la Direction Transport Région Centre Casablanca"

with open("failures.txt", "w", encoding="utf-8") as f:
    for run in range(1, 4):
        t = ask_with_trace(Q)
        f.write("=" * 70 + f"\nRUN {run}\nTOOLS: {[c['name'] for c in t['tool_calls']]}\n")
        f.write(f"ANSWER:\n{t['answer']}\n")
        for i, c in enumerate(t["contexts"], 1):
            f.write(f"\n--- CONTEXT {i} ---\n{c}\n")