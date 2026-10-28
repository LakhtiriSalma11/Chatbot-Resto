"""Étape 3 — Représentation vectorielle de la requête utilisateur ET de l'état du dialogue.

Pour chaque tour utilisateur on construit un vecteur à partir de 3 sources :
  1. la phrase de l'utilisateur                      (la requête)
  2. la dernière réponse du système                  (le contexte du dialogue)
  3. 7 indicateurs binaires : quels slots sont déjà remplis (l'état du dialogue)

Trois backends :
  - "tfidf" : TF-IDF (uni+bigrammes). Rapide, hors-ligne, aucun téléchargement. (baseline NON contextuelle)
  - "sbert" : embeddings CONTEXTUELS (Sentence-BERT, all-MiniLM-L6-v2, 384 dim).
              Nécessite `pip install sentence-transformers` (+ téléchargement du modèle au 1er usage).
  - "spacy" : embeddings CONTEXTUELS RoBERTa (spaCy en_core_web_trf, 768 dim, moyenne des vecteurs de tokens).
              Nécessite `pip install spacy spacy-transformers` + `python -m spacy download en_core_web_trf`.

Usage (génère et sauvegarde les matrices de features dans data/processed/) :
    python -m src.embeddings --backend tfidf
    python -m src.embeddings --backend sbert
"""
import argparse
import csv

import numpy as np
import scipy.sparse as sp
from sklearn.feature_extraction.text import TfidfVectorizer

from src import config as C
from src.text_utils import tokenize

_SPACY_CACHE: dict = {}          # texte -> vecteur (partagé entre instances, évite de recalculer RoBERTa)
_CACHE_FILE = C.PROCESSED_DIR / "embed_cache_spacy.joblib"
SBERT_DEFAULT = "sentence-transformers/all-MiniLM-L6-v2"


def load_split(split: str):
    """Charge intents_{split}.csv -> (utterances, contexts, states[list of 7 ints], labels)."""
    utts, ctxs, states, labels = [], [], [], []
    with open(C.PROCESSED_DIR / f"intents_{split}.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            utts.append(r["utterance"])
            ctxs.append(r["context"])
            states.append([int(c) for c in r["state_before"]])
            labels.append(r["intent"])
    return utts, ctxs, states, labels


class DialogueFeaturizer:
    """Transforme (phrase, contexte, état) en matrice de features."""

    def __init__(self, backend="tfidf", use_context=True, ctx_weight=0.5, state_weight=1.0,
                 sbert_model=SBERT_DEFAULT):
        assert backend in ("tfidf", "sbert", "spacy")
        self.backend, self.use_context = backend, use_context
        self.ctx_weight, self.state_weight, self.sbert_model = ctx_weight, state_weight, sbert_model
        self._sbert = None
        self._nlp = None
        self.utt_vec = TfidfVectorizer(tokenizer=tokenize, token_pattern=None, lowercase=False,
                                       ngram_range=(1, 2), min_df=2, sublinear_tf=True)
        self.ctx_vec = TfidfVectorizer(tokenizer=tokenize, token_pattern=None, lowercase=False,
                                       ngram_range=(1, 1), min_df=3, sublinear_tf=True)

    # -- pickle : on ne sérialise pas le modèle SBERT (rechargé à la demande)
    def __getstate__(self):
        d = self.__dict__.copy()
        d["_sbert"] = None
        d["_nlp"] = None
        return d

    def _encode_spacy(self, texts):
        """RoBERTa contextuel via spaCy : moyenne des vecteurs de la dernière couche, normalisée L2."""
        if self._nlp is None:
            try:
                import spacy
                self._nlp = spacy.load("en_core_web_trf",
                                       disable=["tagger", "parser", "attribute_ruler", "lemmatizer", "ner"])
            except (ImportError, OSError) as e:
                raise SystemExit("Backend 'spacy' : `pip install spacy spacy-transformers` puis "
                                 "`python -m spacy download en_core_web_trf`") from e
        import joblib
        if not _SPACY_CACHE and _CACHE_FILE.exists():
            _SPACY_CACHE.update(joblib.load(_CACHE_FILE))
        todo = sorted({t for t in texts if t.strip() and t not in _SPACY_CACHE})
        for t, doc in zip(todo, self._nlp.pipe(todo, batch_size=32)):
            v = np.asarray(doc._.trf_data.last_hidden_layer_state.data, dtype=np.float32).mean(axis=0)
            _SPACY_CACHE[t] = v / (np.linalg.norm(v) + 1e-9)
        if len(todo) > 50:   # gros calcul (entraînement) : on sauvegarde pour les prochaines exécutions
            joblib.dump(_SPACY_CACHE, _CACHE_FILE)
        out = np.zeros((len(texts), 768), dtype=np.float32)  # contexte vide -> vecteur nul
        for i, t in enumerate(texts):
            if t in _SPACY_CACHE:
                out[i] = _SPACY_CACHE[t]
        return out

    def _encode(self, texts):
        if self.backend == "spacy":
            return self._encode_spacy(texts)
        if self._sbert is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as e:  # message clair pour l'étudiant
                raise SystemExit("Backend 'sbert' : installe d'abord `pip install sentence-transformers`") from e
            self._sbert = SentenceTransformer(self.sbert_model)
        out = np.zeros((len(texts), self._sbert.get_sentence_embedding_dimension()), dtype=np.float32)
        idx = [i for i, t in enumerate(texts) if t.strip()]  # contexte vide -> vecteur nul
        if idx:
            out[idx] = self._sbert.encode([texts[i] for i in idx], batch_size=64,
                                          normalize_embeddings=True, show_progress_bar=False)
        return out

    def fit(self, utts, ctxs=None):
        if self.backend == "tfidf":
            self.utt_vec.fit(utts)
            if self.use_context:
                self.ctx_vec.fit(ctxs)
        return self

    def transform(self, utts, ctxs=None, states=None):
        n = len(utts)
        ctxs = ctxs if ctxs is not None else [""] * n
        st = np.asarray(states if states is not None else np.zeros((n, len(C.STATE_FEATURES))),
                        dtype=np.float32) * self.state_weight
        if self.backend == "tfidf":
            parts = [self.utt_vec.transform(utts)]
            if self.use_context:
                parts += [self.ctx_vec.transform(ctxs) * self.ctx_weight, sp.csr_matrix(st)]
            return sp.hstack(parts).tocsr()
        parts = [self._encode(list(utts))]
        if self.use_context:
            parts += [self._encode(list(ctxs)) * self.ctx_weight, st]
        return np.hstack(parts)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--backend", choices=["tfidf", "sbert", "spacy"], default="tfidf")
    ap.add_argument("--no-context", action="store_true")
    args = ap.parse_args(argv)

    fz = DialogueFeaturizer(args.backend, use_context=not args.no_context)
    tr = load_split("train")
    fz.fit(tr[0], tr[1])
    for split in ("train", "val", "test"):
        u, c, s, y = load_split(split)
        X = fz.transform(u, c, s)
        path = C.PROCESSED_DIR / f"features_{args.backend}_{split}"
        if sp.issparse(X):
            sp.save_npz(str(path) + ".npz", X)
        else:
            np.save(str(path) + ".npy", X)
        print(f"{split:5s} -> matrice {X.shape} sauvegardée ({path.name})")


if __name__ == "__main__":
    main()
