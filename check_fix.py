import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"
import re
from src.fabrilec.rag.hybrid_retrieval import HybridRetriever

results = HybridRetriever().search(
    "Câbles BT armés section nominale diamètre minimal diamètre maximal", top_k=10
)
for x in results:
    m = re.search(r"16\s+4[.,]6\s+\S+", x["text"])
    if m:
        print(x["metadata"]["relative_path"][-60:], "->", m.group(0))