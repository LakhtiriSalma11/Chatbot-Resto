"""Base de restaurants (MultiWOZ, Cambridge) : recherche par critères et par nom."""
import json
import re

from src import config as C

FIELDS = ("id", "name", "food", "area", "pricerange", "address", "postcode", "phone")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s.lower())).strip()


class RestaurantDB:
    def __init__(self, path=C.DB_PATH):
        raw = json.load(open(path, encoding="utf-8"))
        self.rows = sorted(({k: str(r.get(k, "")) for k in FIELDS} for r in raw), key=lambda r: r["name"])
        self.foods = sorted({r["food"] for r in self.rows})
        self.areas = sorted({r["area"] for r in self.rows})
        self.prices = ["cheap", "moderate", "expensive"]
        self._name_index = self._build_name_index()

    # -- recherche par critères --------------------------------------------------
    def search(self, food=None, area=None, pricerange=None) -> list:
        crit = {"food": food, "area": area, "pricerange": pricerange}
        crit = {k: v for k, v in crit.items() if v not in (None, C.DONTCARE)}
        return [r for r in self.rows if all(r[k] == v for k, v in crit.items())]

    def relaxations(self, food=None, area=None, pricerange=None) -> list:
        """Pour chaque critère connu, nombre de résultats si on l'abandonne : [(slot, [rows])]."""
        crit = {"food": food, "area": area, "pricerange": pricerange}
        out = []
        for slot, v in crit.items():
            if v in (None, C.DONTCARE):
                continue
            rest = {k: x for k, x in crit.items() if k != slot}
            res = self.search(**rest)
            if res:
                out.append((slot, res))
        return sorted(out, key=lambda x: -len(x[1]))

    # -- recherche par nom --------------------------------------------------------
    def _build_name_index(self) -> dict:
        idx = {}
        for r in self.rows:
            full = _norm(r["name"])
            keys = {full}
            if full.startswith("the "):
                keys.add(full[4:])
            if full.endswith(" restaurant") and len(full) - 11 >= 6:
                keys.add(full[:-11])
            for k in keys:
                if len(k) >= 4:
                    idx.setdefault(k, r)
        return idx

    def find_name(self, text: str):
        """Cherche un nom de restaurant dans `text`. Retourne (row, (start, end)) ou None.
        Les positions sont celles du texte *normalisé* en minuscules, voir nlu.py."""
        t = " " + _norm(text) + " "
        best = None
        for key, row in self._name_index.items():
            pos = t.find(" " + key + " ")
            if pos >= 0 and (best is None or len(key) > best[0]):
                best = (len(key), row, key)
        if best is None:
            return None
        return best[1], best[2]

    def get(self, name: str):
        return next((r for r in self.rows if r["name"] == name), None)
