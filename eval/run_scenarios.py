"""Étape 5 — Test de scénarios (les 6 scénarios S1–S6 de eval/human_eval.md), joués automatiquement.

    python -m eval.run_scenarios

Chaque scénario est joué avec 2 formulations différentes (messages « libres », écrits à la main, pas générés
par le simulateur). On vérifie objectivement si le but est atteint (bonne réservation / bonne info).
Sorties : reports/scenario_transcripts.md (transcriptions complètes) + reports/scenario_results.csv.

⚠️ Ce n'est PAS une évaluation humaine : voir l'onglet « Évaluation » de l'app (formulaire de notes)
et eval/analyze_human_eval.py pour de vrais testeurs.
"""
import csv
import re

from src import config as C
from src.database import RestaurantDB
from src.dialogue_manager import DialogueManager
from src.intent import IntentClassifier

DAYS = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6}

# ---------------------------------------------------------------- scénarios : (id, but, [variantes de messages])
SCENARIOS = {
    "S1": ("Réserver un indien bon marché au centre, 4 pers., vendredi 19h",
           [["I want a cheap indian restaurant in the centre",
             "Book it for 4 people on friday at 7pm"],
            ["hi, can you find me an inexpensive Indian place in the city centre?",
             "yes please",
             "4 people, friday, 19:00"]]),
    "S2": ("Trouver un italien dans le nord + adresse et téléphone (sans réserver)",
           [["Looking for an italian restaurant in the north",
             "What is the address and phone number?"],
            ["I'd like some Italian food, north part of town",
             "can I get the phone number please",
             "and the address too"]]),
    "S3": ("Réserver un britannique cher, 2 pers., samedi 20h (demander un autre si besoin)",
           [["I need an expensive british restaurant",
             "do you have another one?",
             "Book a table for 2 on saturday at 8pm"],
            ["expensive british food please",
             "Book it for 2 people on Saturday at 20:00"]]),
    "S4": ("Végétarien (inexistant) puis alternative, 3 pers., dimanche 12h30",
           [["I'm looking for a vegetarian restaurant",
             "ok then an italian restaurant is fine",
             "Book a table for 3 on sunday at 12:30"],
            ["Do you have vegetarian food?",
             "chinese then",
             "reserve for 3 people sunday 12:30 please"]]),
    "S5": ("Chinois, aucune préférence prix/zone, 6 pers., jeudi 18h",
           [["I want chinese food, I don't care about the price or the area",
             "Book a table for 6 people on thursday at 6pm"],
            ["chinese restaurant please, any price, any area",
             "6 people thursday 18:00"]]),
    "S6": ("Modéré à l'est, changer pour l'ouest, 2 pers., lundi 13h",
           [["hello",
             "I'm looking for a moderately priced restaurant in the east",
             "actually, I would prefer the west",
             "Book for 2 people on monday at 13:00"],
            ["Hi there",
             "moderate price, east side please",
             "no wait, make it the west part of town",
             "book a table for two on monday at 1pm"]]),
}


def book_ok(b, db, want):
    """b : réservation du bot ; want : dict de critères attendus."""
    row = next((r for r in db.rows if r["name"] == b["name"]), None)
    if row is None:
        return False
    for k in ("food", "area", "pricerange"):
        if k in want and want[k] != "any" and row[k] != want[k]:
            return False
    return (b["people"] == str(want["people"]) and b["day"].lower() == want["day"]
            and b["time"] == want["time"])


EXPECT = {
    "S1": dict(food="indian", pricerange="cheap", area="centre", people=4, day="friday", time="19:00"),
    "S3": dict(food="british", pricerange="expensive", people=2, day="saturday", time="20:00"),
    "S5": dict(food="chinese", people=6, day="thursday", time="18:00"),
    "S6": dict(pricerange="moderate", area="west", people=2, day="monday", time="13:00"),
    "S4": dict(people=3, day="sunday", time="12:30"),
}


def run_one(bot, msgs):
    bot.reset()
    log = [("BOT", bot.opening_message())]
    for m in msgs:
        r = bot.respond(m)
        log.append(("USER", m))
        log.append(("BOT", r.reply))
    return log


def main():
    db = RestaurantDB()
    bot = DialogueManager(db, IntentClassifier.load(), seed=C.SEED)
    rows, md = [], ["# Transcriptions des scénarios (test automatisé)\n"]
    for sid, (goal, variants) in SCENARIOS.items():
        for vi, msgs in enumerate(variants, 1):
            log = run_one(bot, msgs)
            text = " ".join(t for who, t in log if who == "BOT").lower()
            booked = bot.state.booked
            if sid == "S2":
                row = next((r for r in db.rows if r["food"] == "italian" and r["area"] == "north"
                            and r["phone"] in " ".join(t for who, t in log if who == "BOT")), None)
                ok = row is not None and row["address"].lower().split(",")[0] in text
                detail = "adresse+téléphone d'un italien du nord donnés" if ok else "info manquante/incorrecte"
            elif sid == "S4":
                ok = bool(booked) and book_ok(booked[-1], db, EXPECT["S4"]) and \
                     "vegetarian" not in db.foods
                detail = f"réservation {booked[-1]['name']}" if booked else "aucune réservation"
            else:
                ok = bool(booked) and book_ok(booked[-1], db, EXPECT[sid])
                detail = (f"réservé {booked[-1]['name']} ({booked[-1]['people']} pers., "
                          f"{booked[-1]['day']} {booked[-1]['time']})" if booked else "aucune réservation")
            n_user = sum(1 for who, _ in log if who == "USER")
            rows.append({"scenario": sid, "variante": vi, "succes": int(ok), "tours_utilisateur": n_user,
                         "detail": detail})
            md.append(f"## {sid} / variante {vi} — {'✅ réussi' if ok else '❌ échec'} — {goal}\n")
            md += [f"- **{who}** : {t}" for who, t in log]
            md.append(f"\n*Résultat : {detail}*\n")
    C.REPORTS_DIR.mkdir(exist_ok=True)
    (C.REPORTS_DIR / "scenario_transcripts.md").write_text("\n".join(md), encoding="utf-8")
    with open(C.REPORTS_DIR / "scenario_results.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    ok = sum(r["succes"] for r in rows)
    for r in rows:
        print(f"{r['scenario']} v{r['variante']}  {'OK ' if r['succes'] else 'KO '} {r['tours_utilisateur']} tours  {r['detail']}")
    print(f"\nTaux de réussite : {ok}/{len(rows)} = {ok/len(rows):.0%}")


if __name__ == "__main__":
    main()
