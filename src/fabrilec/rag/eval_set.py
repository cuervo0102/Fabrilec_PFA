import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"

from src.fabrilec.rag.hybrid_retrieval import HybridRetriever


QUESTIONS = [
    {
        "question": "Quel est l'objet du marché 254/26/ELEC ?",
        "expected_tender_ref": "AO 254-26-ELEC A PUBLIER",
    },
    {
        "question": "Installation des postes HTA/BT avec raccordement HTA",
        "expected_tender_ref": "AO 254-26-ELEC A PUBLIER",
    },
    {
        "question": "Quel est le bordereau des prix pour l'appel d'offres 254/26/ELEC ?",
        "expected_tender_ref": "AO 254-26-ELEC A PUBLIER",
    },
    {
        "question": "Travaux d'aménagement du boulevard Mohamed VI à Souk Sebt Ouled Nemma",
        "expected_tender_ref": "09-2026",
    },
    {
        "question": "Appel d'offres ouvert international numéro 09/2026, quelle commune ?",
        "expected_tender_ref": "09-2026",
    },
    {
        "question": "Déclaration sur l'honneur pour le marché de Souk Sebt Ouled Nemma",
        "expected_tender_ref": "09-2026",
    },
    {
        "question": "Extension du poste 225/60 kV à Benslimane",
        "expected_tender_ref": "CCH TC4130723 Extension poste 22560 KV Benslimane II",
    },
    {
        "question": "Dossier d'appel d'offres de la Direction Transport Région Centre Casablanca",
        "expected_tender_ref": "TC4130724",
    },
    {
        "question": "Date limite de remise des offres pour le marché 10009032",
        "expected_tender_ref": "PMMP 10009032",
    },
    {
        "question": "Société Régionale Multiservices Souss-Massa SRM-SM",
        "expected_tender_ref": "PMMP 10009032",
    },
    {
        "question": "Prorogation du délai de validité de l'offre, quelles conditions ?",
        "expected_tender_ref": "AOO 299-26  Pour Publication",
    },
    {
        "question": "Règlement de consultation de l'appel d'offres AOO 299-26",
        "expected_tender_ref": "AOO 299-26  Pour Publication",
    },
    {
        "question": "Câbles BT armés isolés pour lignes et postes électriques",
        "expected_tender_ref": "AOO 299-26  Pour Publication",
    },
    {
        "question": "Coffrets de distribution BT en matière synthétique, spécifications techniques",
        "expected_tender_ref": "AOO 299-26  Pour Publication",
    },
]


def top3_accuracy(retriever, search_fn, questions):
    correct = 0
    details = []
    for q in questions:
        results = search_fn(q["question"], top_k=3)
        found_refs = {r["metadata"]["tender_ref"] for r in results}
        hit = q["expected_tender_ref"] in found_refs
        correct += int(hit)
        details.append({
            "question": q["question"],
            "expected": q["expected_tender_ref"],
            "found": list(found_refs),
            "hit": hit,
        })
    return correct / len(questions), details


def semantic_only_search(retriever, query, top_k=3):
    semantic_ids = retriever._semantic_search(query, top_k)
    id_to_index = {cid: i for i, cid in enumerate(retriever.chunk_ids)}
    return [
        {"chunk_id": cid, "text": retriever.chunk_texts[id_to_index[cid]],
         "metadata": retriever.chunk_metadatas[id_to_index[cid]]}
        for cid in semantic_ids
    ]


def main():
    print("Loading retriever (embeddings model + BM25 index)...")
    retriever = HybridRetriever()

    print(f"\nEvaluating {len(QUESTIONS)} questions...\n")

    semantic_acc, semantic_details = top3_accuracy(
        retriever, lambda q, top_k: semantic_only_search(retriever, q, top_k), QUESTIONS
    )
    hybrid_acc, hybrid_details = top3_accuracy(
        retriever, retriever.search, QUESTIONS
    )

    print("=" * 60)
    print(f"Semantic-only top-3 accuracy: {semantic_acc:.1%}")
    print(f"Hybrid (semantic + BM25 RRF) top-3 accuracy: {hybrid_acc:.1%}")
    print("=" * 60)

    print("\nPer-question results (hybrid):")
    for d in hybrid_details:
        status = "PASS" if d["hit"] else "FAIL"
        print(f"[{status}] {d['question']}")
        if not d["hit"]:
            print(f"    expected: {d['expected']}, found: {d['found']}")


if __name__ == "__main__":
    main()