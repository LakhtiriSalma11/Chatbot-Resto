"""Nettoyage et tokenisation du texte des dialogues."""
import re

_TOKEN_RE = re.compile(r"\d{1,2}:\d{2}|\w+(?:'\w+)?|[^\w\s]")


def clean_text(text: str) -> str:
    """Normalise un tour de parole : espaces, ponctuation collée, apostrophes typographiques."""
    if not text:
        return ""
    t = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"\s+([,.!?;:])", r"\1", t)  # "hello ," -> "hello,"
    return t


def tokenize(text: str) -> list:
    """Tokenisation simple : heures (19:45), mots (avec apostrophe) et ponctuation. Minuscule."""
    return _TOKEN_RE.findall(clean_text(text).lower())
