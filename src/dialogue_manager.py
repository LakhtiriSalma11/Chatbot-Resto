"""Étape 4.2 — Gestion de l'état du dialogue + politique à base de règles (système hybride).

Pipeline pour chaque message utilisateur :

    texte ──► NLU (règles)         : slots, infos demandées, nom de restaurant, oui/non/merci...
          └─► Classifieur ML       : intention (inform / request_info / book / bye / other)
                   │
                   ▼  _resolve_intent : les règles corrigent le ML quand les indices sont clairs
          mise à jour de l'ÉTAT ──► POLITIQUE (règles) ──► action ──► NLG (templates) ──► réponse
"""
from dataclasses import dataclass, field
from hashlib import md5
from typing import Optional

from src import config as C
from src.database import RestaurantDB
from src.nlg import (NLG, AREA_LABEL, describe_criteria, describe_restaurant, display_name, info_sentence)
from src.nlu import NLUResult, SlotExtractor
from src.text_utils import clean_text, tokenize

SLOT_LABEL = {"food": "type of food", "area": "area", "pricerange": "price range"}
MIN_CONFIDENCE = 0.45   # en dessous, on se fie aux règles plutôt qu'au classifieur


@dataclass
class TurnResult:
    reply: str
    intent: str
    confidence: float
    action: str
    slots: dict
    debug: dict = field(default_factory=dict)


class DialogueState:
    """Mémoire du dialogue en cours."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.slots = {s: None for s in C.ALL_SLOTS}   # critères + détails de réservation
        self.current: Optional[dict] = None           # restaurant dont on parle
        self.offered: list = []                       # résultats de la dernière recherche
        self.offer_idx = 0
        self.pending: Optional[str] = None            # slot que le bot vient de demander
        self.pending_relax: Optional[str] = None      # critère qu'on propose d'assouplir
        self.booking_mode = False
        self.booked: list = []
        self.last_action: Optional[str] = None
        self.last_reply = ""
        self.turns = 0

    def flags(self) -> list:
        """Vecteur d'état binaire (même définition que pendant l'entraînement)."""
        s = self.slots
        return [int(s["food"] is not None), int(s["area"] is not None), int(s["pricerange"] is not None),
                int(self.current is not None), int(s["bookpeople"] is not None),
                int(s["bookday"] is not None), int(s["booktime"] is not None)]


class DialogueManager:
    def __init__(self, db: RestaurantDB, classifier=None, extractor: Optional[SlotExtractor] = None, seed=None):
        self.db = db
        self.classifier = classifier            # IntentClassifier ou None (mode règles seules)
        self.nlu = extractor or SlotExtractor(db)
        self.nlg = NLG(seed)
        self.state = DialogueState()

    @classmethod
    def from_defaults(cls, rules_only=False, seed=None):
        from src.intent import IntentClassifier
        clf = None if rules_only else IntentClassifier.load()
        return cls(RestaurantDB(), clf, seed=seed)

    # ------------------------------------------------------------------ API publique
    def reset(self):
        self.state.reset()

    def opening_message(self) -> str:
        return self.nlg.say("greet")

    def respond(self, user_text: str) -> TurnResult:
        st = self.state
        text = clean_text(user_text)
        st.turns += 1
        nlu = self.nlu.extract(text, pending=st.pending)
        info = {"nlu_slots": dict(nlu.slots), "nlu_requests": list(nlu.requests),
                "nlu_name": nlu.name["name"] if nlu.name else None}

        # --- règles prioritaires (avant tout classifieur)
        if not text:
            return self._finish("clarify", "other", 1.0, info)
        if nlu.restart:
            st.reset()
            st.turns = 1
            return self._finish("restart", "other", 1.0, {**info, "source": "rule"})
        pure_greeting = nlu.greet and not (nlu.slots or nlu.requests or nlu.name) and len(tokenize(text)) <= 4
        if pure_greeting:
            return self._finish("greet", "greet", 1.0, {**info, "source": "rule"})

        # --- intention : ML + correction par les règles
        ml_intent, conf = None, 1.0
        if self.classifier is not None:
            ml_intent, conf, _ = self.classifier.predict(text, st.last_reply, st.flags())
        intent, source = self._resolve_intent(ml_intent, conf, nlu)
        info.update({"ml_intent": ml_intent, "source": source})

        handler = {"inform": self._handle_inform, "request_info": self._handle_request_info,
                   "book": self._handle_book, "bye": self._handle_bye, "other": self._handle_other}[intent]
        action, reply = handler(nlu)
        return self._finish(action, intent, conf, info, reply)

    # ------------------------------------------------------------------ intention
    def _rule_intent(self, nlu: NLUResult) -> str:
        if nlu.requests:
            return "request_info"
        if nlu.wants_booking or nlu.book_slots:
            return "book"
        if nlu.search_slots or nlu.name:
            return "inform"
        if nlu.bye and not (nlu.affirm or nlu.another):
            return "bye"
        return "other"

    def _resolve_intent(self, ml_intent: Optional[str], conf: float, nlu: NLUResult):
        rule = self._rule_intent(nlu)
        if ml_intent is None:
            return rule, "rules-only"
        if conf < MIN_CONFIDENCE:
            return rule, "rule (low confidence)"
        content = bool(nlu.requests or nlu.book_slots or nlu.search_slots or nlu.name)
        if ml_intent == "bye" and content:
            return rule, "rule (content after thanks)"
        if ml_intent == "bye" and nlu.affirm and not nlu.bye:
            # "ok sounds good" précède souvent la fin d'un dialogue MultiWOZ, mais sans "thanks/bye" c'est une acceptation
            return "other", "rule (affirmation without goodbye)"
        if nlu.book_slots and not nlu.requests:
            return "book", "rule (booking details found)"
        if nlu.requests and ml_intent in ("other", "inform", "bye"):
            return "request_info", "rule (info keyword)"
        if nlu.wants_booking and ml_intent in ("inform", "other"):
            return "book", "rule (booking keyword)"
        if ml_intent == "request_info" and not nlu.requests and (nlu.search_slots or nlu.name):
            return "inform", "rule (criteria found)"
        return ml_intent, "classifier"

    # ------------------------------------------------------------------ outils d'état
    def _apply_slots(self, nlu: NLUResult) -> bool:
        """Met à jour les slots. Retourne True si un critère de recherche a changé."""
        st, changed = self.state, False
        for slot, value in nlu.slots.items():
            if st.slots[slot] != value:
                if slot in C.SEARCH_SLOTS:
                    changed = True
                st.slots[slot] = value
        if changed:
            st.current, st.offered, st.offer_idx = None, [], 0
            st.booking_mode = False
            st.pending_relax = None
        if nlu.name:
            self._select(nlu.name)
        return changed

    def _select(self, row: dict):
        st = self.state
        st.current, st.offered, st.offer_idx = row, [row], 0

    def _criteria(self) -> dict:
        return {k: self.state.slots[k] for k in C.SEARCH_SLOTS}

    def _search(self) -> list:
        return self.db.search(**self._criteria())

    def _known(self) -> int:
        return sum(self.state.slots[k] is not None for k in C.SEARCH_SLOTS)

    def _next_missing(self) -> Optional[str]:
        return next((k for k in C.SEARCH_SLOTS if self.state.slots[k] is None), None)

    def _already_booked_here(self) -> bool:
        st = self.state
        return bool(st.booked) and st.current is not None and st.booked[-1]["name"] == st.current["name"]

    # ------------------------------------------------------------------ handlers
    def _propose(self, results: list, prefix=""):
        st = self.state
        st.offered, st.offer_idx, st.current = results, 0, results[0]
        st.pending, st.booking_mode = None, False
        n = len(results)
        count = "" if n == 1 else f"I found {n} matching restaurants. "
        reply = self.nlg.say("propose", count=prefix + count, name=display_name(st.current),
                             desc=describe_restaurant(st.current))
        return "propose", reply

    def _no_match(self):
        st = self.state
        st.pending, st.current = None, None
        crit = self._criteria()
        what = "any " + describe_criteria(crit)
        only_food = crit["food"] not in (None, C.DONTCARE) and all(
            crit[k] in (None, C.DONTCARE) for k in ("area", "pricerange"))
        if only_food:
            top = ", ".join(self.db.foods[:8])
            st.pending_relax = None
            return "no_match", self.nlg.say("no_match", what=what,
                                            suggestion=f"I can help with cuisines such as {top}. Which one would you like?")
        relax = self.db.relaxations(**crit)
        if relax:
            slot, rows = relax[0]
            st.pending_relax = slot
            ex = display_name(rows[0])
            sug = (f"If you're flexible on the {SLOT_LABEL[slot]}, I have {len(rows)} option"
                   f"{'s' if len(rows) > 1 else ''}, for example {ex}. Shall I look with that change?")
        else:
            sug = "Would you like to try different criteria?"
        return "no_match", self.nlg.say("no_match", what=what, suggestion=sug)

    def _ask_slot(self, slot: str, prefix=""):
        st = self.state
        st.pending = slot
        ack = ""
        if prefix == "" and self._known():
            ack = f"Okay, I'm looking for {describe_criteria(self._criteria())}. "
        return f"ask_{slot}", prefix + ack + self.nlg.say(f"ask_{slot}")

    def _handle_inform(self, nlu: NLUResult):
        st = self.state
        self._apply_slots(nlu)
        if nlu.name:
            st.pending = None
            return "propose", (f"{display_name(st.current)} is {describe_restaurant(st.current)}. "
                               "Would you like to book a table, or do you need more details?")
        if not nlu.search_slots:
            return self._handle_other(nlu)
        results = self._search()
        if not results:
            return self._no_match()
        missing = self._next_missing()
        if missing and self._known() < 2 and len(results) > 3:
            return self._ask_slot(missing)
        return self._propose(results)

    def _handle_request_info(self, nlu: NLUResult):
        st = self.state
        self._apply_slots(nlu)
        prefix = ""
        if st.current is None:
            results = self._search() if self._known() else []
            if not results:
                return "need_restaurant", self.nlg.say("need_restaurant")
            st.offered, st.offer_idx, st.current = results, 0, results[0]
            prefix = f"Let me suggest {display_name(st.current)}. "
        fields = nlu.requests or ["address", "phone", "postcode"]
        follow = ("Is there anything else I can help you with?" if self._already_booked_here()
                  else "Would you like me to book a table?")
        st.pending = None
        info = prefix + info_sentence(st.current, fields)
        return "info", self.nlg.say("info", info=info, follow=follow)

    def _booking_step(self, lead=""):
        st = self.state
        st.booking_mode = True
        for slot, action in (("bookpeople", "ask_bookpeople"), ("bookday", "ask_bookday"),
                             ("booktime", "ask_booktime")):
            if st.slots[slot] is None:
                st.pending = slot
                return action, lead + self.nlg.say(action)
        # tous les détails sont là -> confirmation
        s, r = st.slots, st.current
        ref = md5(f"{r['name']}{s['bookpeople']}{s['bookday']}{s['booktime']}{len(st.booked)}".encode()).hexdigest()[:8].upper()
        booking = {"name": r["name"], "people": s["bookpeople"], "day": s["bookday"],
                   "time": s["booktime"], "ref": ref}
        st.booked.append(booking)
        for k in C.BOOK_SLOTS:
            st.slots[k] = None
        st.booking_mode, st.pending = False, None
        n = int(booking["people"])
        return "confirm_booking", lead + self.nlg.say(
            "confirm_booking", name=display_name(r), people=n, people_word="person" if n == 1 else "people",
            day=booking["day"].capitalize(), time=booking["time"], ref=ref)

    def _handle_book(self, nlu: NLUResult):
        st = self.state
        self._apply_slots(nlu)
        lead = ""
        if st.current is None:
            if not self._known():
                return "need_criteria", self.nlg.say("need_criteria")
            results = self._search()
            if not results:
                return self._no_match()
            st.offered, st.offer_idx, st.current = results, 0, results[0]
            lead = (f"I'd suggest {display_name(st.current)}, {describe_restaurant(st.current)}. "
                    "Let's book it. ")
        elif not st.booking_mode:
            lead = f"Sure, let's book {display_name(st.current)}. "
        return self._booking_step(lead)

    def _handle_bye(self, nlu: NLUResult):
        self.state.pending = None
        return "bye", self.nlg.say("bye")

    def _handle_other(self, nlu: NLUResult):
        st = self.state
        # accepter l'assouplissement proposé ("Shall I look with that change?")
        if nlu.affirm and st.pending_relax:
            st.slots[st.pending_relax] = C.DONTCARE
            st.pending_relax = None
            results = self._search()
            return self._propose(results) if results else self._no_match()
        # "un autre ?" / "non" après une proposition -> option suivante
        if (nlu.another or nlu.deny) and st.offered and st.current is not None and not st.booking_mode:
            if st.offer_idx + 1 < len(st.offered):
                st.offer_idx += 1
                st.current = st.offered[st.offer_idx]
                return "propose_next", self.nlg.say("propose_next", name=display_name(st.current),
                                                    desc=describe_restaurant(st.current))
            return "no_more", self.nlg.say("no_more")
        # "oui" après une proposition -> on lance la réservation
        if nlu.affirm and st.current is not None:
            if self._already_booked_here():
                return "bye", "Great! Is there anything else I can help you with?"
            lead = "" if st.booking_mode else f"Sure, let's book {display_name(st.current)}. "
            return self._booking_step(lead)
        if nlu.bye:
            return self._handle_bye(nlu)
        # on attendait une réponse précise et on ne l'a pas comprise
        if st.pending:
            action, reply = self._ask_slot(st.pending, prefix=self.nlg.say("reask"))
            return action, reply
        return "clarify", self.nlg.say("clarify")

    # ------------------------------------------------------------------ sortie
    def _finish(self, action, intent, conf, info, reply=None) -> TurnResult:
        st = self.state
        if reply is None:
            reply = self.nlg.say(action)
        st.last_action, st.last_reply = action, reply
        return TurnResult(reply, intent, float(conf), action, dict(st.slots), info)
