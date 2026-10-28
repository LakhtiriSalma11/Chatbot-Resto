"""Classifieur d'intention : encapsule featurizer + régression logistique (inférence)."""
import joblib

from src import config as C


class IntentClassifier:
    def __init__(self, featurizer, clf, meta=None):
        self.featurizer, self.clf, self.meta = featurizer, clf, meta or {}

    @property
    def labels(self):
        return list(self.clf.classes_)

    def predict(self, utterance: str, context: str = "", state_flags=None):
        """Retourne (intention, confiance, {intention: proba})."""
        flags = [state_flags if state_flags is not None else [0] * len(C.STATE_FEATURES)]
        X = self.featurizer.transform([utterance], [context], flags)
        proba = self.clf.predict_proba(X)[0]
        probs = {l: float(p) for l, p in zip(self.clf.classes_, proba)}
        best = max(probs, key=probs.get)
        return best, probs[best], probs

    def save(self, path=C.MODEL_PATH):
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"featurizer": self.featurizer, "clf": self.clf, "meta": self.meta}, path)

    @staticmethod
    def default_path():
        """Modèle contextuel (RoBERTa) s'il existe ET si spaCy est installé ; sinon baseline TF-IDF."""
        if C.MODEL_CONTEXTUAL_PATH.exists():
            try:
                import spacy
                import spacy_transformers  # noqa: F401
                spacy.util.get_package_path("en_core_web_trf")
                return C.MODEL_CONTEXTUAL_PATH
            except Exception:
                pass
        return C.MODEL_PATH

    @classmethod
    def load(cls, path=None):
        path = path or cls.default_path()
        if not path.exists():
            raise FileNotFoundError(
                f"Modèle introuvable : {path}\nEntraîne-le d'abord :  python -m src.train_intent")
        d = joblib.load(path)
        return cls(d["featurizer"], d["clf"], d.get("meta"))
