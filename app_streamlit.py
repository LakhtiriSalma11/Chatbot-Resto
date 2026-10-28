"""Étape 6 — Interface web Streamlit du chatbot de réservation de restaurant.

Lancer :   streamlit run app_streamlit.py
"""
import csv

import streamlit as st

from src import config as C
from src.database import RestaurantDB
from src.dialogue_manager import DialogueManager
from src.intent import IntentClassifier

st.set_page_config(page_title="Chatbot Restaurant", page_icon="🍽️", layout="wide")

SLOT_NAMES_FR = {"food": "Cuisine", "area": "Zone", "pricerange": "Prix", "bookpeople": "Personnes",
                 "bookday": "Jour", "booktime": "Heure"}
EXAMPLES = ["I'm looking for a cheap Italian restaurant in the centre",
            "Find me an expensive Chinese place in the north",
            "What is the address and phone number?",
            "Is there another one?",
            "Book a table for 4 on Friday at 7pm"]


@st.cache_resource(show_spinner="Chargement du modèle...")
def load_resources():
    return RestaurantDB(), IntentClassifier.load()


def new_bot() -> DialogueManager:
    db, clf = load_resources()
    return DialogueManager(db, clf)


def reset_conversation():
    bot = new_bot()
    st.session_state.bot = bot
    st.session_state.messages = [{"role": "assistant", "content": bot.opening_message()}]
    st.session_state.last = None


SCENARIOS = {"S1": "Indien pas cher, centre, 4 pers., vendredi 19h",
             "S2": "Italien au nord + adresse et téléphone (sans réserver)",
             "S3": "Britannique cher, 2 pers., samedi 20h (demander un autre si besoin)",
             "S4": "Végétarien (n'existe pas) puis alternative, 3 pers., dimanche 12h30",
             "S5": "Chinois, aucune préférence prix/zone, 6 pers., jeudi 18h",
             "S6": "Modéré à l'est, puis changer pour l'ouest, 2 pers., lundi 13h",
             "libre": "Scénario libre"}
RESULTS_CSV = C.REPORTS_DIR / "human_eval_results.csv"
CSV_FIELDS = ["tester_id", "scenario_id", "task_completed", "n_turns", "fluency", "coherence", "efficiency", "comments"]


def save_rating(row: dict):
    C.REPORTS_DIR.mkdir(exist_ok=True)
    new = not RESULTS_CSV.exists() or RESULTS_CSV.stat().st_size == 0
    with open(RESULTS_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if new:
            w.writeheader()
        w.writerow(row)


def queue_example(text: str):
    st.session_state.queued = text


# ---------------------------------------------------------------- initialisation
try:
    load_resources()
except FileNotFoundError as e:
    st.error(f"{e}")
    st.info("Dans le terminal :  `python -m src.prepare_data`  puis  `python -m src.train_intent`")
    st.stop()

if "bot" not in st.session_state:
    reset_conversation()

# ---------------------------------------------------------------- traitement du message
prompt = st.chat_input("Écris ton message (en anglais)...")
prompt = st.session_state.pop("queued", None) or prompt
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    res = st.session_state.bot.respond(prompt)
    st.session_state.messages.append({"role": "assistant", "content": res.reply})
    st.session_state.last = res

# ---------------------------------------------------------------- affichage
st.title("🍽️ Chatbot de réservation de restaurant")
st.caption("Projet 18 — système hybride : classifieur d'intention (ML) + gestion d'état et politique à base de règles. "
           "Le chatbot comprend et répond en **anglais** (corpus MultiWOZ, restaurants de Cambridge).")

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

with st.expander("📝 Évaluation humaine — noter cette conversation (testeurs)"):
    with st.form("rating_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        tester = c1.text_input("Ton prénom / identifiant", placeholder="ex. T1")
        scen = c2.selectbox("Scénario", list(SCENARIOS), format_func=lambda k: f"{k} — {SCENARIOS[k]}")
        done = st.radio("Le bot a-t-il atteint le but demandé ?", ["Oui", "Non"], horizontal=True)
        f1, f2, f3 = st.columns(3)
        fluency = f1.slider("Fluidité (1-5)", 1, 5, 4, help="Réponses naturelles, bien écrites ?")
        coherence = f2.slider("Cohérence (1-5)", 1, 5, 4, help="Logique, se souvient du contexte ?")
        efficiency = f3.slider("Efficacité (1-5)", 1, 5, 4, help="But atteint sans effort inutile ni répétition ?")
        comments = st.text_area("Commentaires (phrases où le bot s'est trompé)")
        if st.form_submit_button("Enregistrer ma note"):
            if not tester.strip():
                st.warning("Indique un identifiant.")
            else:
                n_user = sum(1 for m in st.session_state.messages if m["role"] == "user")
                save_rating({"tester_id": tester.strip(), "scenario_id": scen,
                             "task_completed": int(done == "Oui"), "n_turns": n_user, "fluency": fluency,
                             "coherence": coherence, "efficiency": efficiency,
                             "comments": comments.replace("\n", " ").strip()})
                st.success("Merci ! Note enregistrée dans reports/human_eval_results.csv. "
                           "Clique sur « Nouvelle conversation » pour le scénario suivant.")

with st.sidebar:
    st.header("État du dialogue")
    bot: DialogueManager = st.session_state.bot
    rows = {SLOT_NAMES_FR[k]: (v if v is not None else "—") for k, v in bot.state.slots.items()}
    for slot, valeur in rows.items():
        st.markdown(f"**{slot}** : {valeur}")
    if bot.state.current:
        st.markdown(f"**Restaurant en cours :** {bot.state.current['name'].title()}")

    last = st.session_state.last
    st.header("Dernière analyse")
    if last is None:
        st.caption("Envoie un message pour voir l'intention détectée.")
    else:
        st.markdown(f"**Intention :** `{last.intent}`")
        st.progress(min(max(last.confidence, 0.0), 1.0), text=f"Confiance : {last.confidence:.0%}")
        st.markdown(f"**Action du bot :** `{last.action}`")
        st.caption(f"Décision : {last.debug.get('source')}")

    st.header("Réservations")
    if bot.state.booked:
        for b in bot.state.booked:
            st.success(f"{b['name'].title()} — {b['people']} pers., {b['day'].capitalize()} {b['time']} "
                       f"(réf. {b['ref']})")
    else:
        st.caption("Aucune réservation pour l'instant.")

    st.header("Exemples")
    for i, ex in enumerate(EXAMPLES):
        st.button(ex, key=f"ex{i}", on_click=queue_example, args=(ex,), use_container_width=True)
    st.button("🔄 Nouvelle conversation", on_click=reset_conversation, use_container_width=True)
