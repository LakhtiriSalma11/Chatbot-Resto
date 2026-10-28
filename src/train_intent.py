"""Étape 4.1 — Entraînement du classifieur d'intention.

    python -m src.train_intent                     # TF-IDF + contexte (par défaut)
    python -m src.train_intent --backend sbert     # embeddings contextuels SBERT
    python -m src.train_intent --backend spacy     # embeddings contextuels RoBERTa (spaCy)
    python -m src.train_intent --no-context        # phrase seule (pour l'ablation)

Le paramètre de régularisation C de la régression logistique est choisi sur le split `val`
(macro-F1), puis les scores finaux sont mesurés une seule fois sur `test`.
"""
import argparse
import json

from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score

from src import config as C
from src.embeddings import DialogueFeaturizer, load_split
from src.intent import IntentClassifier


def train(backend="tfidf", use_context=True, c_grid=(0.5, 1, 2, 5, 10, 20, 50, 100), verbose=True):
    tr, va, te = load_split("train"), load_split("val"), load_split("test")
    fz = DialogueFeaturizer(backend, use_context=use_context).fit(tr[0], tr[1])
    Xtr, Xva, Xte = (fz.transform(*s[:3]) for s in (tr, va, te))

    best = None
    for c in c_grid:
        clf = LogisticRegression(C=c, max_iter=3000, random_state=C.SEED).fit(Xtr, tr[3])
        f1 = f1_score(va[3], clf.predict(Xva), average="macro")
        if verbose:
            print(f"  C={c:<5} val macro-F1 = {f1:.4f}")
        if best is None or f1 > best[0]:
            best = (f1, c, clf)
    f1_val, c_best, clf = best

    pred = clf.predict(Xte)
    metrics = {
        "backend": backend, "use_context": use_context, "C": c_best,
        "val_macro_f1": round(f1_val, 4),
        "test_accuracy": round(accuracy_score(te[3], pred), 4),
        "test_macro_f1": round(f1_score(te[3], pred, average="macro"), 4),
        "n_train": len(tr[0]), "n_val": len(va[0]), "n_test": len(te[0]),
    }
    meta = {**metrics, "labels": list(clf.classes_)}
    return IntentClassifier(fz, clf, meta), metrics


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--backend", choices=["tfidf", "sbert", "spacy"], default="tfidf")
    ap.add_argument("--no-context", action="store_true")
    ap.add_argument("--out", type=str, default=str(C.MODEL_PATH))
    args = ap.parse_args(argv)

    print(f"Entraînement : backend={args.backend}, contexte={'non' if args.no_context else 'oui'}")
    model, metrics = train(args.backend, not args.no_context)
    from pathlib import Path
    model.save(Path(args.out))
    C.REPORTS_DIR.mkdir(exist_ok=True)
    json.dump(metrics, open(C.REPORTS_DIR / "train_metrics.json", "w"), indent=1)
    print("\nRésultats :", json.dumps(metrics, indent=1))
    print(f"\nModèle sauvegardé -> {args.out}")


if __name__ == "__main__":
    main()
