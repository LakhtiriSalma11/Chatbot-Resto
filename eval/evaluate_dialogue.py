"""Étape 5 (métriques de dialogue) — évaluation AUTOMATIQUE du système de dialogue.

    python -m eval.evaluate_dialogue [--n-sim 300]

Deux volets (ce n'est PAS une évaluation humaine, voir eval/human_eval.md pour celle-là) :

 A. Suivi d'état sur les vrais dialogues du split `test` : on rejoue les tours utilisateur dans le NLU
    et on compare les slots prédits aux annotations MultiWOZ (Joint Goal Accuracy + F1 slot-valeur).
 B. Utilisateurs simulés : un script d'utilisateur avec un but (cuisine/zone/prix + réservation)
    discute avec le bot ; on mesure le taux de réussite de la tâche (réservation correcte).
    Comparaison : système hybride (ML + règles) vs règles seules.
"""
import argparse
import datetime as dt
import json
import random
import re
from collections import Counter

from src import config as C
from src.database import RestaurantDB
from src.dialogue_manager import DialogueManager
from src.intent import IntentClassifier
from src import nlu as nlu_module
from src.nlu import SlotExtractor

EVAL_SLOTS = C.ALL_SLOTS


# =============================================================================
# A. Suivi d'état sur les vrais dialogues
# =============================================================================
def guess_pending(system_text: str):
    """Devine le slot demandé par le système réel (réponses libres de MultiWOZ)."""
    t = system_text.lower()
    rules = [("bookpeople", r"how many (?:people|guests)|party size|for how many"),
             ("bookday", r"what day|which day|day (?:would|do)"),
             ("booktime", r"what time|which time|time (?:would|do)"),
             ("food", r"what (?:type|kind) of food|which cuisine|what cuisine|type of cuisine|kind of cuisine"),
             ("area", r"what (?:area|part of town)|which (?:area|part of town)|part of town|what side"),
             ("pricerange", r"price ?range|how expensive|what price")]
    for slot, pat in rules:
        if re.search(pat, t):
            return slot
    return None


def evaluate_state_tracking(extractor: SlotExtractor):
    n_turns = n_joint = 0
    tp = Counter(); fp = Counter(); fn = Counter()
    for line in open(C.PROCESSED_DIR / "dialogues.jsonl", encoding="utf-8"):
        d = json.loads(line)
        if d["split"] != "test":
            continue
        pred, prev_sys = {}, ""
        for t in d["turns"]:
            if t["speaker"] == "SYSTEM":
                prev_sys = t["text"]
                continue
            pred.update(extractor.extract(t["text"], pending=guess_pending(prev_sys)).slots)
            gold = {s: t["state"][s] for s in EVAL_SLOTS if t["state"].get(s)}
            p = {s: pred[s] for s in EVAL_SLOTS if pred.get(s)}
            n_turns += 1
            n_joint += int(p == gold)
            for s in EVAL_SLOTS:
                if s in gold and p.get(s) == gold[s]:
                    tp[s] += 1
                else:
                    if s in p:
                        fp[s] += 1
                    if s in gold:
                        fn[s] += 1

    def prf(a, b, c):
        pr = a / (a + b) if a + b else 0.0
        rc = a / (a + c) if a + c else 0.0
        return round(pr, 3), round(rc, 3), round(2 * pr * rc / (pr + rc), 3) if pr + rc else 0.0

    per_slot = {s: dict(zip(("precision", "recall", "f1"), prf(tp[s], fp[s], fn[s]))) for s in EVAL_SLOTS}
    micro = dict(zip(("precision", "recall", "f1"), prf(sum(tp.values()), sum(fp.values()), sum(fn.values()))))
    return {"turns": n_turns, "joint_goal_accuracy": round(n_joint / n_turns, 4),
            "slot_micro": micro, "per_slot": per_slot}


# =============================================================================
# B. Utilisateurs simulés
# =============================================================================
DAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
AREA_TXT = {"centre": ["in the centre", "in the city centre", "in the centre of town"],
            "north": ["in the north", "in the north part of town"], "south": ["in the south", "on the south side"],
            "east": ["in the east", "on the east side"], "west": ["in the west", "on the west side of town"]}
PRICE_TXT = {"cheap": ["cheap", "inexpensive"], "moderate": ["moderately priced", "moderate"],
             "expensive": ["expensive", "upscale"]}


def time_phrase(hhmm: str, rng) -> str:
    h, m = map(int, hhmm.split(":"))
    style = rng.choice(["24h", "ampm"])
    if style == "24h":
        return f"{h:02d}:{m:02d}"
    h12 = h - 12 if h > 12 else h
    return f"{h12}{':%02d' % m if m else ''} pm" if h >= 12 else f"{h12}:{m:02d} am"


class SimUser:
    """Utilisateur simulé avec un but et un STYLE de conversation (tiré au hasard) :
       - accept_all : accepte la 1re proposition en donnant tous les détails de réservation d'un coup
       - accept_bare: dit juste "yes please" puis répond aux questions une par une
       - info_first : demande adresse/téléphone avant de réserver
       - other_first: demande "un autre ?" une fois avant d'accepter
    Le nombre de critères donnés d'emblée varie (1, 2 ou 3) : le bot doit poser les questions manquantes."""

    STYLES = ["accept_all", "accept_bare", "info_first", "other_first"]

    def __init__(self, db: RestaurantDB, rng: random.Random):
        r = rng.choice(db.rows)
        n_stated = rng.choice([1, 2, 2, 3])
        stated = rng.sample(["food", "area", "pricerange"], n_stated)
        self.goal = {k: r[k] for k in stated}              # critères que l'utilisateur exige
        self.people = str(rng.randint(1, 8))
        self.day = rng.choice(DAY_NAMES)
        self.time = rng.choice([f"{h}:{m}" for h in range(12, 21) for m in ("00", "15", "30", "45")])
        self.style = rng.choice(self.STYLES)
        self.rng, self.db = rng, db
        self.asked_info = self.asked_other = False
        self.done = False

    def say_slot(self, slot):
        v, rng = self.goal.get(slot), self.rng
        if v is None:
            return rng.choice(["I don't care", "any is fine", "it doesn't matter"])
        if slot == "food":
            return rng.choice([f"{v} food", f"{v}", f"I'd like {v} food"])
        if slot == "area":
            return rng.choice(AREA_TXT[v])
        return rng.choice(PRICE_TXT[v])

    def opening(self):
        parts = []
        if "pricerange" in self.goal:
            parts.append(self.rng.choice(PRICE_TXT[self.goal["pricerange"]]))
        if "food" in self.goal:
            parts.append(self.goal["food"])
        s = " ".join(parts + ["restaurant"])
        if "area" in self.goal:
            s += " " + self.rng.choice(AREA_TXT[self.goal["area"]])
        return self.rng.choice([f"I'm looking for a {s}", f"Can you find me a {s}?", f"I want a {s}"])

    def book_phrase(self, prefix="yes please, "):
        t = time_phrase(self.time, self.rng)
        return prefix + self.rng.choice([f"book a table for {self.people} on {self.day} at {t}",
                                         f"I need a table for {self.people} at {t} on {self.day}"])

    def reply(self, action: str, proposed: dict):
        """Réponse selon la DERNIÈRE ACTION du bot (pas selon son texte). None = le bot est perdu -> échec."""
        rng = self.rng
        if action == "ask_food":
            return self.say_slot("food")
        if action == "ask_area":
            return self.say_slot("area")
        if action == "ask_pricerange":
            return self.say_slot("pricerange")
        if action in ("propose", "propose_next"):
            if not all(proposed[k] == v for k, v in self.goal.items()):
                return "is there another one?"
            if self.style == "info_first" and not self.asked_info:
                self.asked_info = True
                return rng.choice(["what's the phone number and address?", "Can I have the postcode and the phone number?"])
            if self.style == "other_first" and not self.asked_other:
                self.asked_other = True
                return rng.choice(["is there another one?", "something else please"])
            return self.book_phrase() if self.style != "accept_bare" else rng.choice(["yes please", "yes", "ok sounds good"])
        if action == "no_more":
            return "ok then please book it"
        if action == "info":
            return self.book_phrase("ok, ") if self.style != "accept_bare" else "yes please"
        if action == "ask_bookpeople":
            return rng.choice([f"{self.people} people", f"for {self.people}", self.people, f"a table for {self.people}"])
        if action == "ask_bookday":
            return rng.choice([self.day, f"on {self.day}", f"{self.day} please"])
        if action == "ask_booktime":
            t = time_phrase(self.time, rng)
            return rng.choice([f"at {t}", t, f"{t} please"])
        if action == "confirm_booking":
            self.done = True
            return "thank you, goodbye"
        if action == "no_match":
            return "yes"
        return None


def simulate(bot: DialogueManager, n: int, seed: int = C.SEED, max_turns: int = 16):
    rng = random.Random(seed)
    ok, lengths, fails = 0, [], Counter()
    by_style = {s: [0, 0] for s in SimUser.STYLES}
    for _ in range(n):
        user = SimUser(bot.db, rng)
        bot.reset()
        msg, success, outcome = user.opening(), False, "max_turns"
        for turn in range(1, max_turns + 1):
            res = bot.respond(msg)
            if res.action == "confirm_booking":
                b = bot.state.booked[-1]
                row = bot.db.get(b["name"])
                success = (all(row[k] == v for k, v in user.goal.items()) and b["people"] == user.people
                           and b["day"] == user.day and b["time"] == _norm_time(user.time))
                outcome = "wrong_booking" if not success else "ok"
                lengths.append(turn)
                break
            msg = user.reply(res.action, bot.state.current)
            if msg is None:
                outcome = f"lost_at:{res.action}"
                break
        if not success:
            fails[outcome] += 1
        ok += success
        by_style[user.style][0] += success
        by_style[user.style][1] += 1
    return {"n": n, "success_rate": round(ok / n, 4), "avg_turns_when_booked": round(sum(lengths) / max(len(lengths), 1), 2),
            "by_style": {s: f"{a}/{b}" for s, (a, b) in by_style.items()}, "failures": dict(fails)}


def _norm_time(t: str) -> str:
    h, m = t.split(":")
    return f"{int(h):02d}:{m}"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n-sim", type=int, default=300)
    args = ap.parse_args(argv)
    C.REPORTS_DIR.mkdir(exist_ok=True)
    nlu_module.TODAY_OVERRIDE = dt.date(2026, 10, 17)   # date fixe -> résultats reproductibles
    db = RestaurantDB()
    out = {}

    print("A. Suivi d'état sur les dialogues du split test (NLU à règles)")
    out["state_tracking"] = st = evaluate_state_tracking(SlotExtractor(db))
    print(f"   Joint Goal Accuracy = {st['joint_goal_accuracy']:.3f}   slot F1 (micro) = {st['slot_micro']['f1']:.3f}")
    for s, v in st["per_slot"].items():
        print(f"     {s:11s} P={v['precision']:.2f} R={v['recall']:.2f} F1={v['f1']:.2f}")

    print(f"\nB. {args.n_sim} dialogues avec utilisateur simulé")
    out["simulation"] = {}
    clf = IntentClassifier.load()
    for name, c in (("hybride (ML + règles)", clf), ("règles seules", None)):
        bot = DialogueManager(db, c, seed=C.SEED)
        r = simulate(bot, args.n_sim)
        out["simulation"][name] = r
        print(f"   {name:22s} réussite = {r['success_rate']:.1%}   tours moy. = {r['avg_turns_when_booked']}   échecs : {r['failures']}")

    json.dump(out, open(C.REPORTS_DIR / "dialogue_metrics.json", "w"), indent=1)
    print("\n-> reports/dialogue_metrics.json")


if __name__ == "__main__":
    main()
