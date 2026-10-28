"""Étape 5 (métriques) — Évaluation du classifieur d'intention sur le split `test`.

    python -m eval.evaluate_intent

Produit dans reports/ :
    intent_metrics.json      accuracy, macro-F1, IC95% bootstrap, rapport par classe
    confusion_matrix.png     matrice de confusion
    intent_errors.csv        phrases mal classées (pour l'analyse d'erreurs)
    intent_ablation.csv      comparaison : phrase seule / + contexte, TF-IDF / SBERT / RoBERTa-spaCy (si installés)
"""
import csv
import json
from collections import Counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score

from src import config as C
from src.embeddings import load_split
from src.intent import IntentClassifier
from src.train_intent import train


def bootstrap_ci(y_true, y_pred, n=1000, seed=C.SEED):
    rng = np.random.default_rng(seed)
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    accs = [np.mean(y_true[i] == y_pred[i]) for i in (rng.integers(0, len(y_true), len(y_true)) for _ in range(n))]
    return float(np.percentile(accs, 2.5)), float(np.percentile(accs, 97.5))


def main():
    C.REPORTS_DIR.mkdir(exist_ok=True)
    model = IntentClassifier.load()
    utts, ctxs, states, y = load_split("test")
    X = model.featurizer.transform(utts, ctxs, states)
    pred = list(model.clf.predict(X))
    labels = C.INTENTS

    acc = accuracy_score(y, pred)
    lo, hi = bootstrap_ci(y, pred)
    majority = Counter(load_split("train")[3]).most_common(1)[0][0]
    base = accuracy_score(y, [majority] * len(y))
    report = classification_report(y, pred, labels=labels, output_dict=True, zero_division=0)
    metrics = {"n_test": len(y), "accuracy": round(acc, 4), "accuracy_ci95": [round(lo, 4), round(hi, 4)],
               "macro_f1": round(f1_score(y, pred, average="macro"), 4),
               "majority_baseline_accuracy": round(base, 4), "per_class": report}
    json.dump(metrics, open(C.REPORTS_DIR / "intent_metrics.json", "w"), indent=1)

    print(f"Accuracy test = {acc:.4f}  (IC95% bootstrap [{lo:.3f}, {hi:.3f}])   "
          f"baseline classe majoritaire = {base:.3f}")
    print(classification_report(y, pred, labels=labels, zero_division=0, digits=3))

    cm = confusion_matrix(y, pred, labels=labels)
    fig, ax = plt.subplots(figsize=(5.5, 4.6))
    ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(len(labels)), labels, rotation=30, ha="right")
    ax.set_yticks(range(len(labels)), labels)
    ax.set_xlabel("Prédit")
    ax.set_ylabel("Réel")
    ax.set_title(f"Matrice de confusion (test, acc={acc:.3f})")
    for i in range(len(labels)):
        for j in range(len(labels)):
            ax.text(j, i, cm[i, j], ha="center", va="center",
                    color="white" if cm[i, j] > cm.max() / 2 else "black")
    fig.tight_layout()
    fig.savefig(C.REPORTS_DIR / "confusion_matrix.png", dpi=150)

    with open(C.REPORTS_DIR / "intent_errors.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["utterance", "context", "true", "pred"])
        for u, c, t, p in zip(utts, ctxs, y, pred):
            if t != p:
                w.writerow([u, c, t, p])
    print(f"{sum(t != p for t, p in zip(y, pred))} erreurs -> reports/intent_errors.csv")

    # ---- ablation
    print("\nAblation (réentraîne chaque variante, C choisi sur val) :")
    rows = []
    variants = [("tfidf", False), ("tfidf", True)]
    try:
        import sentence_transformers  # noqa: F401
        variants += [("sbert", False), ("sbert", True)]
    except ImportError:
        print("  (sentence-transformers non installé : variantes SBERT ignorées)")
    try:
        import spacy  # noqa: F401
        import spacy_transformers  # noqa: F401
        spacy.load("en_core_web_trf")
        variants += [("spacy", False), ("spacy", True)]
    except Exception:
        print("  (spaCy en_core_web_trf non installé : variantes RoBERTa ignorées)")
    for backend, ctx in variants:
        _, m = train(backend, ctx, verbose=False)
        rows.append({"backend": backend, "contexte": "oui" if ctx else "non",
                     "val_macro_f1": m["val_macro_f1"], "test_accuracy": m["test_accuracy"],
                     "test_macro_f1": m["test_macro_f1"]})
        print(f"  {backend:6s} contexte={'oui' if ctx else 'non'}  acc={m['test_accuracy']:.4f}  macroF1={m['test_macro_f1']:.4f}")
    with open(C.REPORTS_DIR / "intent_ablation.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
