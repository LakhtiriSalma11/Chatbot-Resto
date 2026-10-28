"""Tests automatiques :   python -m pytest -q

Les tests marqués `needs_model` sont ignorés si le classifieur n'est pas entraîné
(lance d'abord `python -m src.train_intent`).
"""
import pytest

from src import config as C
from src.database import RestaurantDB
from src.dialogue_manager import DialogueManager
from src.nlu import SlotExtractor

needs_model = pytest.mark.skipif(not C.MODEL_PATH.exists(), reason="modèle non entraîné")


@pytest.fixture(scope="module")
def db():
    return RestaurantDB()


@pytest.fixture(scope="module")
def nlu(db):
    return SlotExtractor(db)


# ----------------------------------------------------------------------------- base de données
def test_db_size_and_search(db):
    assert len(db.rows) == 110
    res = db.search(food="chinese", area="centre", pricerange="cheap")
    assert res and all(r["food"] == "chinese" and r["area"] == "centre" for r in res)
    assert db.search(food="dontcare", area=None, pricerange=None) == db.rows


# ----------------------------------------------------------------------------- NLU
def test_dontcare_phrases(nlu):
    r = nlu.extract("I want chinese food, I don't care about the price or the area").slots
    assert r["food"] == "chinese" and r["pricerange"] == "dontcare" and r["area"] == "dontcare"
    assert nlu.extract("no preference for price").slots == {"pricerange": "dontcare"}


@pytest.mark.parametrize("text,expected", [
    ("I'm looking for a cheap Italian place in the centre", {"food": "italian", "area": "centre", "pricerange": "cheap"}),
    ("a moderately priced restaurant in the west side of town", {"area": "west", "pricerange": "moderate"}),
    ("an inexpensive restaurant", {"pricerange": "cheap"}),                       # "inexpensive" != "expensive"
    ("an expensive north american restaurant", {"food": "north american", "pricerange": "expensive"}),  # pas de zone "north"
    ("table for two at 19:45 on sunday", {"bookpeople": "2", "booktime": "19:45", "bookday": "sunday"}),
    ("Book a table for 4 on Friday at 7:30pm", {"bookpeople": "4", "bookday": "friday", "booktime": "19:30"}),
    ("something with sushi", {"food": "japanese"}),
])
def test_nlu_slots(nlu, text, expected):
    assert nlu.extract(text).slots == expected


def test_nlu_pending_answers(nlu):
    assert nlu.extract("any area is fine", pending="area").slots == {"area": "dontcare"}
    assert nlu.extract("it doesn't matter", pending="food").slots == {"food": "dontcare"}
    assert nlu.extract("7", pending="bookpeople").slots == {"bookpeople": "7"}
    assert nlu.extract("fri", pending="bookday").slots == {"bookday": "friday"}


def test_nlu_requests_and_flags(nlu):
    assert set(nlu.extract("What's the phone number and address?").requests) == {"phone", "address"}
    assert nlu.extract("any price").requests == []                      # préférence, pas une question
    assert nlu.extract("Is there another one?").another
    assert nlu.extract("thanks, bye!").bye


def test_nlu_goodbye_is_not_a_booking_day(nlu):
    assert "bookday" not in nlu.extract("That's all I need today, thank you!").slots


def test_nlu_restaurant_name(nlu):
    r = nlu.extract("Can you book Pizza Hut City Centre for 3 on sunday")
    assert r.name["name"] == "pizza hut city centre"
    assert "area" not in r.slots and "food" not in r.slots              # le nom n'ajoute pas de faux critères


# ----------------------------------------------------------------------------- dialogue (règles seules : déterministe)
def run(bot, msgs):
    return [bot.respond(m) for m in msgs]


def test_full_booking_flow_rules_only(db):
    bot = DialogueManager(db, None, seed=0)
    out = run(bot, ["I'm looking for a Chinese restaurant", "in the centre", "yes please",
                    "for 4 people", "on friday", "7:30 pm"])
    assert [o.action for o in out] == ["ask_area", "propose", "ask_bookpeople", "ask_bookday",
                                       "ask_booktime", "confirm_booking"]
    b = bot.state.booked[-1]
    assert (b["people"], b["day"], b["time"]) == ("4", "friday", "19:30")
    assert db.get(b["name"])["food"] == "chinese"


def test_one_shot_booking_without_prior_search(db):
    bot = DialogueManager(db, None, seed=0)
    r = bot.respond("Book a table for 2 on saturday at 6pm at a cheap italian place in the north")
    assert r.action == "confirm_booking"


def test_no_match_then_relax(db):
    bot = DialogueManager(db, None, seed=0)
    r1 = bot.respond("I want a vegetarian restaurant")
    assert r1.action == "no_match"
    r2 = bot.respond("a cheap one in the west")
    assert r2.action == "no_match" and "flexible" in r2.reply
    assert bot.respond("yes").action == "propose"


def test_another_option_and_info(db):
    bot = DialogueManager(db, None, seed=0)
    bot.respond("an expensive british restaurant in the centre")
    first = bot.state.current["name"]
    r = bot.respond("is there another one?")
    assert r.action == "propose_next" and bot.state.current["name"] != first
    r = bot.respond("what is the address and postcode?")
    assert r.action == "info" and bot.state.current["address"] in r.reply


def test_restart_and_greeting(db):
    bot = DialogueManager(db, None, seed=0)
    assert bot.respond("hello").action == "greet"
    bot.respond("cheap chinese food")
    assert bot.respond("start over").action == "restart"
    assert bot.state.slots["food"] is None


# ----------------------------------------------------------------------------- avec le classifieur ML
@needs_model
def test_hybrid_accepts_ok_sounds_good():
    """Régression : le ML prenait « ok sounds good » pour un au revoir."""
    bot = DialogueManager.from_defaults(seed=0)
    bot.respond("I want an expensive mexican restaurant in the south")
    r = bot.respond("ok sounds good")
    assert r.action == "ask_bookpeople"


@needs_model
def test_hybrid_full_conversation():
    bot = DialogueManager.from_defaults(seed=0)
    out = run(bot, ["Hello", "cheap italian in the north", "what's the phone number?",
                    "book it for 2 on saturday at 6pm", "thanks, goodbye"])
    assert [o.action for o in out] == ["greet", "propose", "info", "confirm_booking", "bye"]
