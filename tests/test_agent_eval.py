from src.fabrilec.agent.agent import ask
from src.fabrilec.rag.eval_set import QUESTIONS


def main():
    for i, q in enumerate(QUESTIONS, 1):
        print(f"--- Question {i}/{len(QUESTIONS)} ---")
        print(f"Q: {q['question']}")
        print(f"   (attendu: dossier {q['expected_tender_ref']})")
        answer = ask(q["question"])
        print(f"A: {answer}")
        print()


if __name__ == "__main__":
    main()