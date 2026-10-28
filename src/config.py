"""Configuration centrale du projet (chemins, constantes, listes d'intentions/slots)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
MODELS_DIR = ROOT / "models"
REPORTS_DIR = ROOT / "reports"

DB_PATH = DATA_DIR / "restaurant_db.json"
MODEL_PATH = MODELS_DIR / "intent_clf.joblib"                    # TF-IDF (baseline, sans dépendance lourde)
MODEL_CONTEXTUAL_PATH = MODELS_DIR / "intent_clf_spacy.joblib"   # embeddings contextuels RoBERTa (spaCy)

SEED = 42

# --- MultiWOZ 2.2 (GitHub) -------------------------------------------------
MULTIWOZ_BASE_URL = "https://raw.githubusercontent.com/budzianowski/multiwoz/master"
MULTIWOZ_FILES = (
    [f"train/dialogues_{i:03d}.json" for i in range(1, 18)]
    + ["dev/dialogues_001.json", "dev/dialogues_002.json"]
    + ["test/dialogues_001.json", "test/dialogues_002.json"]
)

# --- Intentions -------------------------------------------------------------
# inform       : l'utilisateur donne/modifie des critères (cuisine, zone, prix) ou cite un restaurant
# request_info : il demande une info (adresse, téléphone, code postal, prix...)
# book         : il veut réserver (personnes, jour, heure, référence)
# bye          : remerciements / au revoir
# other        : "un autre ?", "oui", "peu importe"... (géré par les règles)
INTENTS = ["inform", "request_info", "book", "bye", "other"]

# Slots de recherche et de réservation (noms MultiWOZ sans le préfixe "restaurant-")
SEARCH_SLOTS = ["food", "area", "pricerange"]
BOOK_SLOTS = ["bookpeople", "bookday", "booktime"]
ALL_SLOTS = SEARCH_SLOTS + BOOK_SLOTS
INFO_SLOTS = ["address", "phone", "postcode", "food", "pricerange", "area"]

# Vecteur d'état (7 indicateurs binaires) fourni au classifieur comme contexte
STATE_FEATURES = ["food", "area", "pricerange", "name", "bookpeople", "bookday", "booktime"]

DONTCARE = "dontcare"
