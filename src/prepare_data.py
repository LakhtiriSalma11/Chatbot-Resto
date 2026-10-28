"""Étapes 1 & 2 — Acquisition et prétraitement de MultiWOZ 2.2 (domaine restaurant).

Ce script :
  1. télécharge MultiWOZ 2.2 (si absent) dans data/raw/
  2. garde les dialogues 100 % restaurant (services == ["restaurant"])
  3. nettoie le texte et gère les tours de parole (USER / SYSTEM)
  4. étiquette chaque tour utilisateur avec une intention (dérivée des annotations)
  5. découpe par dialogue en train / val / test (80/10/10, sans fuite entre splits)
  6. écrit data/processed/ : dialogues.jsonl, intents_{split}.csv, lexicon.json, stats.json

Usage :
    python -m src.prepare_data               # télécharge si besoin puis traite
    python -m src.prepare_data --no-download # utilise seulement ce qui est dans data/raw/
"""
import argparse
import csv
import json
import random
import sys
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from src import config as C
from src.text_utils import clean_text


# ----------------------------------------------------------------------------
# 1. Acquisition
# ----------------------------------------------------------------------------
def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=120) as r, open(dest, "wb") as f:
        f.write(r.read())


def download_raw(raw_dir: Path = C.RAW_DIR) -> None:
    """Télécharge les 21 fichiers MultiWOZ 2.2 (~210 Mo au total) en parallèle."""
    jobs = []
    for rel in C.MULTIWOZ_FILES:
        dest = raw_dir / rel.replace("/", "_")
        if not dest.exists():
            jobs.append((f"{C.MULTIWOZ_BASE_URL}/data/MultiWOZ_2.2/{rel}", dest))
    if not C.DB_PATH.exists():
        jobs.append((f"{C.MULTIWOZ_BASE_URL}/db/restaurant_db.json", C.DB_PATH))
    if not jobs:
        print("Données brutes déjà présentes.")
        return
    print(f"Téléchargement de {len(jobs)} fichier(s)... (patience, ~210 Mo)")
    with ThreadPoolExecutor(max_workers=6) as ex:
        list(ex.map(lambda j: _download(*j), jobs))
    print("Téléchargement terminé.")


# ----------------------------------------------------------------------------
# 2. Lecture des dialogues & étiquetage des intentions
# ----------------------------------------------------------------------------
def _flat_state(frame_state: dict) -> dict:
    """{'restaurant-food': ['chinese']} -> {'food': 'chinese'} (1re valeur)."""
    out = {}
    for k, v in frame_state.get("slot_values", {}).items():
        out[k.replace("restaurant-", "")] = v[0] if isinstance(v, list) and v else v
    return out


def label_intent(state: dict, prev_state: dict, turn_idx: int) -> str:
    """Dérive l'intention d'un tour utilisateur à partir des annotations MultiWOZ.

    Règles (par priorité) :
      - active_intent == NONE (hors 1er tour)           -> bye
      - demande d'info (adresse, tel, postcode, ...)    -> request_info
      - réservation (créneau modifié, ref demandée)     -> book
      - critère de recherche modifié / nom cité         -> inform
      - sinon                                           -> other
    """
    ai = state["active_intent"]
    req = [r.replace("restaurant-", "") for r in state["requested_slots"]]
    cur, prev = _flat_state(state), prev_state
    changed = {k for k in cur if cur.get(k) != prev.get(k)}

    if ai == "NONE":
        return "bye" if turn_idx > 0 else "other"
    if any(r in C.INFO_SLOTS for r in req):
        return "request_info"
    if "ref" in req or changed & set(C.BOOK_SLOTS):
        return "book"
    if ai == "book_restaurant":
        if changed & set(C.SEARCH_SLOTS):
            return "inform"
        return "book"
    if changed & (set(C.SEARCH_SLOTS) | {"name"}):
        return "inform"
    return "other"


def state_flags(flat_state: dict) -> list:
    """Vecteur d'état binaire (7 valeurs) : quels slots sont déjà renseignés."""
    return [1 if flat_state.get(s) else 0 for s in C.STATE_FEATURES]


def iter_raw_dialogues(raw_dir: Path):
    for f in sorted(raw_dir.glob("*_dialogues_*.json")):
        split = f.name.split("_")[0]
        for d in json.load(open(f, encoding="utf-8")):
            yield split, d


def build_dialogues(raw_dir: Path) -> list:
    """Retourne la liste des dialogues restaurant-seul, nettoyés et annotés."""
    dialogues = []
    for official_split, d in iter_raw_dialogues(raw_dir):
        if d["services"] != ["restaurant"]:
            continue
        turns, prev_state = [], {}
        for i, t in enumerate(d["turns"]):
            text = clean_text(t["utterance"])
            if t["speaker"] == "SYSTEM":
                turns.append({"speaker": "SYSTEM", "text": text})
                continue
            fr = next(x for x in t["frames"] if x["service"] == "restaurant")
            st = fr["state"]
            turns.append({
                "speaker": "USER",
                "text": text,
                "intent": label_intent(st, prev_state, i),
                "state_before": state_flags(prev_state),
                "state": _flat_state(st),
                "requested": [r.replace("restaurant-", "") for r in st["requested_slots"]],
            })
            prev_state = _flat_state(st)
        dialogues.append({"id": d["dialogue_id"], "official_split": official_split, "turns": turns})
    return dialogues


# ----------------------------------------------------------------------------
# 3. Découpage, export
# ----------------------------------------------------------------------------
def split_dialogues(dialogues: list, seed: int = C.SEED) -> dict:
    ids = sorted(d["id"] for d in dialogues)
    random.Random(seed).shuffle(ids)
    n = len(ids)
    n_train, n_val = int(0.8 * n), int(0.1 * n)
    assign = {}
    for k, i in enumerate(ids):
        assign[i] = "train" if k < n_train else "val" if k < n_train + n_val else "test"
    return assign


def export(dialogues: list, assign: dict, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "dialogues.jsonl", "w", encoding="utf-8") as f:
        for d in dialogues:
            d = {**d, "split": assign[d["id"]]}
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

    rows = {"train": [], "val": [], "test": []}
    for d in dialogues:
        prev_sys = ""
        for t in d["turns"]:
            if t["speaker"] == "SYSTEM":
                prev_sys = t["text"]
                continue
            rows[assign[d["id"]]].append({
                "dialogue_id": d["id"], "utterance": t["text"], "context": prev_sys,
                "state_before": "".join(map(str, t["state_before"])), "intent": t["intent"],
            })
    cols = ["dialogue_id", "utterance", "context", "state_before", "intent"]
    for split, rs in rows.items():
        with open(out_dir / f"intents_{split}.csv", "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(rs)

    # Lexique des cuisines vu dans les annotations d'ENTRAÎNEMENT uniquement (pas de fuite vers le test)
    foods = Counter()
    for d in dialogues:
        if assign[d["id"]] != "train":
            continue
        for t in d["turns"]:
            if t["speaker"] == "USER" and t["state"].get("food") not in (None, C.DONTCARE):
                foods[t["state"]["food"]] += 1
    json.dump({"foods": dict(foods.most_common())}, open(out_dir / "lexicon.json", "w"), indent=1)

    stats = {
        "n_dialogues": len(dialogues),
        "dialogues_per_split": dict(Counter(assign.values())),
        "user_turns_per_split": {s: len(r) for s, r in rows.items()},
        "intent_distribution": {
            s: dict(Counter(r["intent"] for r in rs)) for s, rs in rows.items()
        },
        "avg_turns_per_dialogue": round(sum(len(d["turns"]) for d in dialogues) / len(dialogues), 1),
    }
    json.dump(stats, open(out_dir / "stats.json", "w"), indent=1)
    return stats


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw-dir", type=Path, default=C.RAW_DIR)
    ap.add_argument("--out-dir", type=Path, default=C.PROCESSED_DIR)
    ap.add_argument("--no-download", action="store_true", help="ne pas télécharger MultiWOZ")
    args = ap.parse_args(argv)

    if not args.no_download:
        download_raw(args.raw_dir)
    if not list(args.raw_dir.glob("*_dialogues_*.json")):
        sys.exit(f"Aucun fichier MultiWOZ dans {args.raw_dir}. Relance sans --no-download.")

    dialogues = build_dialogues(args.raw_dir)
    assign = split_dialogues(dialogues)
    stats = export(dialogues, assign, args.out_dir)
    print(json.dumps(stats, indent=1))
    ok = "OK" if stats["n_dialogues"] >= 1000 else "ATTENTION : < 1000 dialogues"
    print(f"\n{stats['n_dialogues']} dialogues restaurant -> {ok}. Fichiers écrits dans {args.out_dir}")


if __name__ == "__main__":
    main()
