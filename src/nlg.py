"""Génération de réponses par templates (plusieurs variantes par action pour plus de naturel)."""
import random

AREA_LABEL = {"centre": "the centre", "north": "the north", "south": "the south",
              "east": "the east", "west": "the west"}
PRICE_ADJ = {"cheap": "cheap", "moderate": "moderately priced", "expensive": "expensive"}

TEMPLATES = {
    "greet": [
        "Hello! I can help you find a restaurant in Cambridge and book a table. What kind of food are you looking for?",
        "Hi there! Tell me what you feel like eating (cuisine, area or price range) and I'll find you a restaurant.",
    ],
    "ask_food": ["What type of food would you like?", "Which cuisine do you prefer?"],
    "ask_area": ["Which part of town would you like: north, south, east, west or the centre?",
                 "Do you have a preferred area? (north, south, east, west or centre)"],
    "ask_pricerange": ["What price range do you have in mind: cheap, moderate or expensive?",
                       "Are you looking for something cheap, moderately priced or expensive?"],
    "propose": [
        "{count}I'd suggest {name}, {desc}. Would you like me to book a table, or shall I give you more details?",
        "{count}How about {name}? It is {desc}. Shall I book it for you?",
    ],
    "propose_next": [
        "How about {name} instead? It is {desc}. Shall I book it?",
        "Another option is {name}, {desc}. Would you like to book it?",
    ],
    "no_more": ["I'm afraid that was the last restaurant matching your criteria. Would you like to change the area, "
                "the price range or the type of food?"],
    "no_match": ["Sorry, I couldn't find {what}. {suggestion}"],
    "info": ["{info} {follow}"],
    "ask_bookpeople": ["How many people should I book for?", "For how many people?"],
    "ask_bookday": ["Which day would you like to come?", "What day should I book it for?"],
    "ask_booktime": ["What time would you like the table?", "At what time?"],
    "confirm_booking": [
        "All set! I've booked a table at {name} for {people} {people_word} on {day} at {time}. "
        "Your reference number is {ref}. Is there anything else I can help you with?",
        "Your booking is confirmed: {name}, {people} {people_word}, {day} at {time}. "
        "Reference number: {ref}. Anything else I can do for you?",
    ],
    "bye": ["You're welcome! Enjoy your meal. Goodbye!", "Glad I could help. Enjoy your meal and goodbye!"],
    "restart": ["Okay, let's start over. What kind of restaurant are you looking for?"],
    "need_restaurant": ["Which restaurant do you mean? Tell me a cuisine, an area or a price range and I'll find one."],
    "need_criteria": ["I can book that for you, but first I need to find a restaurant. "
                      "What kind of food, area or price range do you have in mind?"],
    "clarify": ["Sorry, I didn't quite get that. You can give me a cuisine, an area or a price range, "
                "ask for an address or phone number, or ask me to book a table."],
    "reask": ["Sorry, I didn't catch that. "],
}


class NLG:
    def __init__(self, seed=None):
        self.rng = random.Random(seed)

    def say(self, action: str, **kw) -> str:
        return self.rng.choice(TEMPLATES[action]).format(**kw)


def display_name(row: dict) -> str:
    return row["name"].title()


def describe_restaurant(row: dict) -> str:
    adj = PRICE_ADJ.get(row["pricerange"], row["pricerange"])
    article = "an" if adj[0] in "aeiou" else "a"
    return f"{article} {adj} {row['food']} restaurant in {AREA_LABEL[row['area']]}"


def describe_criteria(slots: dict) -> str:
    """{'food': 'chinese', 'area': 'north'} -> 'chinese restaurants in the north'."""
    food = slots.get("food") if slots.get("food") not in (None, "dontcare") else None
    price = slots.get("pricerange") if slots.get("pricerange") not in (None, "dontcare") else None
    area = slots.get("area") if slots.get("area") not in (None, "dontcare") else None
    s = " ".join(x for x in [PRICE_ADJ.get(price, price) if price else None, food] if x)
    s = (s + " restaurants") if s else "restaurants"
    if area:
        s += f" in {AREA_LABEL[area]}"
    return s


def info_sentence(row: dict, fields: list) -> str:
    parts = {
        "address": f"the address is {row['address']}",
        "postcode": f"the postcode is {row['postcode']}",
        "phone": f"the phone number is {row['phone']}",
        "pricerange": f"it is in the {row['pricerange']} price range",
        "food": f"it serves {row['food']} food",
        "area": f"it is located in {AREA_LABEL[row['area']]}",
    }
    chosen = [parts[f] for f in fields if f in parts]
    if not chosen:
        return ""
    text = chosen[0] if len(chosen) == 1 else ", ".join(chosen[:-1]) + " and " + chosen[-1]
    return f"For {display_name(row)}, {text}."
