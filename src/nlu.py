"""Compréhension (NLU) à base de règles : extraction des slots et des signaux de dialogue.

Le classifieur d'intention dit *ce que veut* l'utilisateur ; ce module extrait *les valeurs* :
cuisine, zone, prix, nombre de personnes, jour, heure, nom du restaurant, infos demandées...
Le lexique des cuisines vient de la base de restaurants + des annotations d'entraînement MultiWOZ.
"""
import datetime as dt
import json
import re
from dataclasses import dataclass, field
from typing import Optional

from src import config as C
from src.database import RestaurantDB, _norm
from src.text_utils import clean_text

NUM_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
             "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12}
_NUM = r"(\d{1,2}|" + "|".join(NUM_WORDS) + r")"
DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
DAY_ABBR = {"mon": "monday", "tue": "tuesday", "tues": "tuesday", "wed": "wednesday", "thu": "thursday",
            "thur": "thursday", "thurs": "thursday", "fri": "friday", "sat": "saturday", "sun": "sunday"}

FOOD_SYNONYMS = {"pizza": "italian", "pasta": "italian", "curry": "indian", "curries": "indian",
                 "sushi": "japanese", "fish": "seafood", "asian": "asian oriental",
                 "oriental": "asian oriental", "american": "north american", "english": "british",
                 "burger": "north american", "burgers": "north american", "steak": "british"}

AREA_PATTERNS = {
    "centre": r"\b(?:cent(?:re|er)|downtown|city cent(?:re|er)|middle of (?:the )?(?:town|city))\b",
    "north": r"\bnorth(?:ern)?\b", "south": r"\bsouth(?:ern)?\b",
    "east": r"\beast(?:ern)?\b", "west": r"\bwest(?:ern)?\b",
}
PRICE_PATTERNS = {  # ordre important : "inexpensive" doit être testé avant "expensive"
    "cheap": r"\b(?:cheap(?:er|ly)?|inexpensive|budget|economical|low[- ]?(?:priced|cost)|affordable)\b",
    "moderate": r"\b(?:moderate(?:ly)?(?: ?priced)?|mid[- ]?(?:range|priced)|medium|reasonabl[ey])\b",
    "expensive": r"\b(?:expensive|pricey|upscale|high[- ]?end|posh|fancy|luxur\w+|fine dining)\b",
}
DONTCARE_EXPLICIT = {
    "food": r"\bany (?:kind |type |sort )?(?:of )?(?:food|cuisine)\b|\b(?:food|cuisine) (?:doesn'?t|does not|don'?t) matter\b|\bno (?:particular )?(?:preference|pref) (?:for|on|in) (?:food|cuisine)\b",
    "area": r"\bany (?:area|part of town|location|side of town)\b|\barea (?:doesn'?t|does not) matter\b|\bno (?:particular )?(?:preference|pref) (?:for|on|in) (?:the )?(?:area|location)\b",
    "pricerange": r"\bany (?:price|price ?range)\b|\bprice(?: ?range)? (?:doesn'?t|does not|isn'?t|is not) (?:matter|important)\b|\bno (?:particular )?(?:preference|pref) (?:for|on|in) price\b",
}
GENERIC_DONTCARE = (r"\b(?:don'?t care|do not care|doesn'?t matter|does not matter|no preference|any(?:thing)?|"
                    r"whatever|either (?:is|one)|not important|no matter|don'?t mind|up to you|you choose|"
                    r"surprise me|you pick|pick one|any is fine)\b")

REQUEST_PATTERNS = {
    "address": r"\b(?:address|where (?:is|are|exactly)|located|location|directions|how (?:do|can) i get|which street)\b",
    "phone": r"\b(?:phone|telephone|contact number|number to call|call them|ring them)\b",
    "postcode": r"\b(?:post ?code|postal code|zip)\b",
    "pricerange": r"\b(?:(?:what(?:'s| is| are)|tell me|give me|and|also) (?:the )?price ?(?:range)?s?|how expensive|how much|cost|are they expensive|is it expensive)\b",
    "food": r"\b(?:what (?:type|kind|sort) of food|what cuisine|what (?:do|does) (?:they|it) serve|type of food|what food)\b",
    "area": r"\b(?:what area|which area|what part of town|which part of town|what side of town)\b",
}
RE_GREET = re.compile(r"^\s*(?:hi|hello|hey|hiya|good (?:morning|afternoon|evening)|greetings|yo)\b", re.I)
RE_BYE = re.compile(r"\b(?:thanks?|thank you|bye|goodbye|good bye|that'?s all|that is all|that will be all|"
                    r"that'?s it|that is it|cheers|see you|have a (?:good|nice|great))\b", re.I)
RE_AFFIRM = re.compile(r"^\s*(?:yes|yeah|yep|yup|sure|ok(?:ay)?|sounds (?:good|great)|that works|perfect|great|"
                       r"please do|go ahead|that would be (?:great|good|fine)|that'?s fine|alright|definitely|absolutely)\b", re.I)
RE_DENY = re.compile(r"^\s*(?:no|nope|nah|not really|not that one)\b", re.I)
RE_ANOTHER = re.compile(r"\b(?:another|anything else|something else|other (?:one|ones|option|options|restaurant|"
                        r"restaurants|place|places|choice|choices)|different (?:one|restaurant|place)|"
                        r"something different|next one|any other|what else)\b", re.I)
RE_RESTART = re.compile(r"\b(?:start over|start again|restart|reset|new search|begin again|from scratch|never ?mind)\b", re.I)
RE_BOOKWORD = re.compile(r"\b(?:book|booking|reserve|reservation|table for)\b", re.I)


@dataclass
class NLUResult:
    slots: dict = field(default_factory=dict)      # slot -> valeur extraite
    requests: list = field(default_factory=list)   # infos demandées (address, phone, ...)
    name: Optional[dict] = None                    # ligne DB si un restaurant est nommé
    greet: bool = False
    bye: bool = False
    affirm: bool = False
    deny: bool = False
    another: bool = False
    restart: bool = False
    wants_booking: bool = False

    @property
    def search_slots(self):
        return {k: v for k, v in self.slots.items() if k in C.SEARCH_SLOTS}

    @property
    def book_slots(self):
        return {k: v for k, v in self.slots.items() if k in C.BOOK_SLOTS}


def _fmt_time(h: int, m: int, ampm: Optional[str]) -> str:
    ampm = (ampm or "").replace(".", "")
    if ampm == "pm" and h < 12:
        h += 12
    elif ampm == "am" and h == 12:
        h = 0
    elif not ampm and 1 <= h <= 10:   # "at 7" / "7:30" sans am/pm -> on suppose le soir pour un restaurant
        h += 12
    return f"{h:02d}:{m:02d}"


def parse_time(t: str, pending=None) -> Optional[str]:
    t = t.lower()
    m = re.search(r"\b([01]?\d|2[0-3])[:.h]([0-5]\d)\s*(am|pm|a\.m\.|p\.m\.)?", t)
    if m:
        return _fmt(m)
    m = re.search(r"\b(1[0-2]|0?[1-9])\s*(am|pm|a\.m\.|p\.m\.)", t)
    if m:
        return _fmt_time(int(m.group(1)), 0, m.group(2))
    m = re.search(r"\b(\d{1,2})\s*o'?clock\b", t)
    if m:
        return _fmt_time(int(m.group(1)), 0, None)
    if re.search(r"\bnoon\b", t):
        return "12:00"
    m = re.search(r"\bat\s+(\d{1,2})\b(?!\s*(?:people|persons|guests|:))", t)
    if m and int(m.group(1)) <= 23:
        return _fmt_time(int(m.group(1)), 0, None)
    if pending == "booktime":
        m = re.fullmatch(r"\s*(\d{1,2})\s*", t)
        if m and int(m.group(1)) <= 23:
            return _fmt_time(int(m.group(1)), 0, None)
    return None


def _fmt(m):
    return _fmt_time(int(m.group(1)), int(m.group(2)), m.group(3))


def _to_int(s: str) -> int:
    return NUM_WORDS.get(s, None) or int(s)


def parse_people(t: str, pending=None) -> Optional[str]:
    t = t.lower()
    neg = r"(?!\s*(?::|\.\d|am\b|pm\b|o'?clock|min|hours?|days?|nights?))"
    pats = [rf"\b(?:table|reservation|booking|seats?|party|group)\s+(?:for|of)\s+{_NUM}\b{neg}",
            rf"\bfor\s+{_NUM}\s*(?:people|persons|guests|diners|adults|of us)\b",
            rf"\b{_NUM}\s*(?:people|persons|guests|diners|adults|of us)\b",
            rf"\bparty of {_NUM}\b", rf"\bfor\s+{_NUM}\b{neg}"]
    for p in pats:
        m = re.search(p, t)
        if m and 1 <= _to_int(m.group(1)) <= 20:
            return str(_to_int(m.group(1)))
    if re.search(r"\b(?:just me|only me|by myself|for me|myself)\b", t):
        return "1"
    if pending == "bookpeople":
        m = re.fullmatch(rf"\s*{_NUM}\s*(?:please)?\s*[.!]?", t)
        if m and 1 <= _to_int(m.group(1)) <= 20:
            return str(_to_int(m.group(1)))
    return None


TODAY_OVERRIDE = None   # fixé par les scripts d'évaluation pour des résultats reproductibles


def _today() -> dt.date:
    return TODAY_OVERRIDE or dt.date.today()


def parse_day(t: str, pending=None) -> Optional[str]:
    t = t.lower()
    m = re.search(r"\b(" + "|".join(DAYS) + r")s?\b", t)
    if m:
        return m.group(1)
    if not RE_BYE.search(t):   # "that's all I need today, thanks" n'est pas un jour de réservation
        if re.search(r"\b(?:today|tonight)\b", t):
            return DAYS[_today().weekday()]
        if re.search(r"\btomorrow\b", t):
            return DAYS[(_today().weekday() + 1) % 7]
    if pending == "bookday":
        m = re.search(r"\b(" + "|".join(DAY_ABBR) + r")\b", t)
        if m:
            return DAY_ABBR[m.group(1)]
    return None


class SlotExtractor:
    def __init__(self, db: RestaurantDB, extra_foods=None):
        self.db = db
        if extra_foods is None:
            extra_foods = self._load_lexicon()
        foods = set(db.foods) | set(extra_foods)
        self.food_map = {f: f for f in foods}
        self.food_map.update(FOOD_SYNONYMS)
        keys = sorted(self.food_map, key=len, reverse=True)
        self.food_re = re.compile(r"\b(" + "|".join(re.escape(k) for k in keys) + r")\b", re.I)

    @staticmethod
    def _load_lexicon():
        p = C.PROCESSED_DIR / "lexicon.json"
        if not p.exists():
            return []
        bad = {C.DONTCARE, "not mentioned", "none", "?"}
        return [f for f, n in json.load(open(p)).get("foods", {}).items() if n >= 2 and f not in bad]

    def extract(self, text: str, pending=None) -> NLUResult:
        text = clean_text(text)
        r = NLUResult()
        low = text.lower()

        # 1) nom de restaurant (puis on le retire du texte pour ne pas en tirer de faux critères)
        found = self.db.find_name(low)
        if found:
            r.name, key = found
            words = key.split()
            low = re.sub(r"\b" + r"\W+".join(map(re.escape, words)) + r"\b", " ", low, count=1)

        # 2) critères de recherche
        m = self.food_re.search(low)
        if m:
            r.slots["food"] = self.food_map[m.group(1).lower()]
            # on retire la cuisine du texte : "north american" ne doit pas donner la zone "north"
            low = low[:m.start()] + " " + low[m.end():]
        for area, pat in AREA_PATTERNS.items():
            if re.search(pat, low):
                r.slots["area"] = area
                break
        for price, pat in PRICE_PATTERNS.items():
            if re.search(pat, low):
                r.slots["pricerange"] = price
                break
        for slot, pat in DONTCARE_EXPLICIT.items():
            if slot not in r.slots and re.search(pat, low):
                r.slots[slot] = C.DONTCARE
        # « I don't care about the price or the area », « no preference for price or area »
        for m in re.finditer(r"(?:don'?t|do not|doesn'?t|does not) (?:really )?(?:care|matter)(?: about| for| on| what| which)?([^.,;!?]*)"
                             r"|no (?:particular )?(?:preference|pref)s? (?:for|on|in|about)([^.,;!?]*)", low):
            clause = (m.group(1) or m.group(2) or "")
            for slot, kw in (("pricerange", r"\b(?:price|prices|cost|budget)\b"),
                             ("area", r"\b(?:area|areas|location|part of town|side of town|where)\b"),
                             ("food", r"\b(?:food|cuisine|kind of food|type of food)\b")):
                if slot not in r.slots and re.search(kw, clause):
                    r.slots[slot] = C.DONTCARE
        if pending in C.SEARCH_SLOTS and pending not in r.slots and re.search(GENERIC_DONTCARE, low):
            r.slots[pending] = C.DONTCARE

        # 3) réservation
        for slot, fn in (("bookpeople", parse_people), ("bookday", parse_day), ("booktime", parse_time)):
            v = fn(low, pending)
            if v:
                r.slots[slot] = v

        # 4) infos demandées, signaux de dialogue
        # (si l'utilisateur dit "any price", c'est une préférence, pas une demande d'information)
        r.requests = [k for k, pat in REQUEST_PATTERNS.items()
                      if re.search(pat, low) and r.slots.get(k) != C.DONTCARE]
        r.greet = bool(RE_GREET.search(text))
        r.bye = bool(RE_BYE.search(text))
        r.affirm = bool(RE_AFFIRM.search(text))
        r.deny = bool(RE_DENY.search(text))
        r.another = bool(RE_ANOTHER.search(text))
        r.restart = bool(RE_RESTART.search(text))
        r.wants_booking = bool(RE_BOOKWORD.search(text))
        return r
