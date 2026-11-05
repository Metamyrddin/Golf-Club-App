"""Synthetic-but-realistic v1 catalog.

Three houses, ten heads and ten shafts each. Model names are original so the
dataset can be shipped; specs (loft ladders, shaft weights, launch/spin) follow
the shape of current driver / iron / wedge lines without copying a SKU.

Extend the catalog by appending to HEADS or SHAFTS and re-running the seed.
Every brand must be able to fill a bag: driver (players + max), one fairway
with 15° and 18°, a hybrid, a utility iron, three iron families, a wedge
with 46–60, and a putter that can be ordered blade or mallet.
"""

from __future__ import annotations

BRANDS = [
    {
        "id": "titleist",
        "name": "Titleist",
        "country": "USA",
        "blurb": "Players-leaning house. Forged irons and a lower-spin driver sit next to a high-MOI distance driver.",
    },
    {
        "id": "taylormade",
        "name": "TaylorMade",
        "country": "USA",
        "blurb": "Distance-leaning house. Lighter high-launch woods and a wide iron ladder from tour to max game improvement.",
    },
    {
        "id": "callaway",
        "name": "Callaway",
        "country": "USA",
        "blurb": "Balanced house. A mid-launch players driver, a very high-launch distance driver, and a deep game-improvement iron line.",
    },
]


def _head(**kwargs: object) -> dict:
    base = {
        "gender": "unisex",
        "offset": "mid",
        "spin": "mid",
        "launch": "mid",
        "year": 2025,
        "set_makeup": None,
        "pw_loft": None,
    }
    base.update(kwargs)
    return base


def _shaft(
    *,
    brand: str,
    model: str,
    families: list[str],
    profile: str,
    launch: str,
    spin: str,
    weights: dict[str, float],
    torque: float,
    blurb: str,
) -> dict:
    slug = f"{brand}-{model}".lower().replace(" ", "-")
    return {
        "id": slug,
        "brand": brand,
        "model": model,
        "families": families,
        "profile": profile,
        "launch": launch,
        "spin": spin,
        "flex_weights": weights,
        "torque": torque,
        "blurb": blurb,
    }


def _brand_heads(brand: str, prefix: str, spec: dict) -> list[dict]:
    """Build the ten heads for one house. ``spec`` shifts lofts and iron PW loft."""
    return [
        _head(
            id=f"{prefix}-forge-driver",
            brand=brand,
            model=f"{prefix} Forge Driver",
            club_type="driver",
            category="players",
            launch="low",
            spin="low",
            offset="low",
            lofts=[8.0, 9.0, 10.5],
            standard_loft=9.0,
            blurb="Compact players driver, low spin, for golfers who already launch it.",
        ),
        _head(
            id=f"{prefix}-max-driver",
            brand=brand,
            model=f"{prefix} Max Driver",
            club_type="driver",
            category="super_game_improvement",
            launch="high",
            spin="mid",
            offset="high",
            lofts=[9.0, 10.5, 12.0, 13.5],
            standard_loft=10.5,
            blurb="High-MOI distance driver. Stock loft ladder runs high on purpose.",
        ),
        _head(
            id=f"{prefix}-fairway",
            brand=brand,
            model=f"{prefix} Fairway",
            club_type="fairway_wood",
            category="players_distance",
            launch="mid",
            spin="mid",
            offset="mid",
            lofts=[15.0, 18.0],
            standard_loft=15.0,
            blurb="One fairway head in 15° (3-wood) or 18° (5-wood).",
        ),
        _head(
            id=f"{prefix}-hybrid",
            brand=brand,
            model=f"{prefix} Rescue Hybrid",
            club_type="hybrid",
            category="game_improvement",
            launch="high",
            spin="mid",
            offset="mid",
            lofts=[17.0, 19.0, 22.0, 25.0],
            standard_loft=19.0,
            blurb="Wide-soled hybrid that replaces long irons for most amateurs.",
        ),
        _head(
            id=f"{prefix}-utility",
            brand=brand,
            model=f"{prefix} Utility Iron",
            club_type="utility_iron",
            category="players",
            launch="low",
            spin="low",
            offset="low",
            lofts=[18.0, 20.0],
            standard_loft=18.0,
            blurb="Hollow utility long iron for faster swings who prefer a iron profile.",
        ),
        _head(
            id=f"{prefix}-cb-irons",
            brand=brand,
            model=f"{prefix} CB Irons",
            club_type="iron_set",
            category="players",
            launch="low",
            spin="low",
            offset="low",
            lofts=[spec["players_pw"]],
            standard_loft=spec["players_pw"],
            pw_loft=spec["players_pw"],
            set_makeup="4-PW",
            blurb="Cavity-back players iron. Lofts are traditional; PW is the weak loft in this set.",
        ),
        _head(
            id=f"{prefix}-gi-irons",
            brand=brand,
            model=f"{prefix} Game Irons",
            club_type="iron_set",
            category="game_improvement",
            launch="mid",
            spin="mid",
            offset="mid",
            lofts=[spec["gi_pw"]],
            standard_loft=spec["gi_pw"],
            pw_loft=spec["gi_pw"],
            set_makeup="5-PW",
            blurb="Game-improvement cavity. Stronger lofts, more offset, wider sole.",
        ),
        _head(
            id=f"{prefix}-max-irons",
            brand=brand,
            model=f"{prefix} Max Irons",
            club_type="iron_set",
            category="super_game_improvement",
            launch="high",
            spin="mid",
            offset="high",
            lofts=[spec["sgi_pw"]],
            standard_loft=spec["sgi_pw"],
            pw_loft=spec["sgi_pw"],
            set_makeup="5-PW",
            blurb="Max-forgiveness iron with the strongest lofts in the house.",
        ),
        _head(
            id=f"{prefix}-spin-wedge",
            brand=brand,
            model=f"{prefix} Spin Wedge",
            club_type="wedge",
            category="players",
            launch="mid",
            spin="high",
            offset="low",
            lofts=[46.0, 48.0, 50.0, 52.0, 54.0, 56.0, 58.0, 60.0],
            standard_loft=56.0,
            blurb="One wedge head, ordered in any loft from 46° to 60°. Finish is mid bounce.",
        ),
        _head(
            id=f"{prefix}-putter",
            brand=brand,
            model=f"{prefix} Putter",
            club_type="putter",
            category="putter",
            launch="mid",
            spin="low",
            offset="low",
            lofts=[3.0, 3.5],
            standard_loft=3.0,
            blurb="Order as a blade or a mallet. Face-balanced mallet, toe-hang blade.",
        ),
    ]


def _brand_shafts(brand: str, prefix: str, grams: dict[str, float]) -> list[dict]:
    """Ten shafts. ``grams`` nudges a house heavier (+) or lighter (−)."""
    g = grams.get("nudge", 0.0)

    def w(table: dict[str, float]) -> dict[str, float]:
        return {flex: round(weight + g, 1) for flex, weight in table.items()}

    return [
        _shaft(
            brand=brand,
            model=f"{prefix} Velar Black",
            families=["driver"],
            profile="control",
            launch="low",
            spin="low",
            weights=w({"R": 62, "S": 67, "X": 72}),
            torque=3.1,
            blurb="Low-launch driver shaft for the control bag. Not offered in L or A.",
        ),
        _shaft(
            brand=brand,
            model=f"{prefix} Velar Air",
            families=["driver", "fairway"],
            profile="distance",
            launch="high",
            spin="high",
            weights=w({"L": 40, "A": 45, "R": 50, "S": 56}),
            torque=5.4,
            blurb="Light high-launch wood shaft. The distance-bag default.",
        ),
        _shaft(
            brand=brand,
            model=f"{prefix} Velar Mid",
            families=["driver"],
            profile="neutral",
            launch="mid",
            spin="mid",
            weights=w({"A": 52, "R": 57, "S": 62, "X": 68}),
            torque=4.1,
            blurb="Neutral driver shaft used when the golfer did not ask for a distance or control bias.",
        ),
        _shaft(
            brand=brand,
            model=f"{prefix} Fairway Tour",
            families=["fairway"],
            profile="control",
            launch="low",
            spin="low",
            weights=w({"R": 70, "S": 75, "X": 80}),
            torque=3.3,
            blurb="Heavier fairway shaft for the control bag.",
        ),
        _shaft(
            brand=brand,
            model=f"{prefix} Hybrid Air",
            families=["hybrid", "utility_iron"],
            profile="distance",
            launch="high",
            spin="mid",
            weights=w({"L": 55, "A": 60, "R": 66, "S": 72, "X": 78}),
            torque=3.9,
            blurb="Light hybrid / utility shaft across the full flex range.",
        ),
        _shaft(
            brand=brand,
            model=f"{prefix} Iron Air",
            families=["iron"],
            profile="distance",
            launch="high",
            spin="mid",
            weights=w({"L": 68, "A": 78, "R": 90, "S": 102}),
            torque=3.0,
            blurb="Lighter iron shaft. No X — a very fast player steps to the mid or heavy iron shaft.",
        ),
        _shaft(
            brand=brand,
            model=f"{prefix} Iron Project",
            families=["iron", "utility_iron"],
            profile="neutral",
            launch="mid",
            spin="mid",
            weights=w({"A": 86, "R": 104, "S": 116, "X": 126}),
            torque=2.3,
            blurb="Neutral iron shaft. Also an acceptable utility-iron shaft.",
        ),
        _shaft(
            brand=brand,
            model=f"{prefix} Iron Black",
            families=["iron"],
            profile="control",
            launch="low",
            spin="low",
            weights=w({"R": 112, "S": 122, "X": 132}),
            torque=1.9,
            blurb="Heavy low-launch iron shaft for the control bag. R, S and X only.",
        ),
        _shaft(
            brand=brand,
            model=f"{prefix} Wedge Spin",
            families=["wedge"],
            profile="control",
            launch="mid",
            spin="high",
            weights=w({"L": 92, "A": 102, "R": 114, "S": 124, "X": 130}),
            torque=2.0,
            blurb="Wedge shaft in every flex so the bag does not have to mix flex on the short clubs.",
        ),
        _shaft(
            brand=brand,
            model=f"{prefix} Putter Stable",
            families=["putter"],
            profile="neutral",
            launch="mid",
            spin="low",
            weights={"R": 120},
            torque=1.4,
            blurb="Single stock putter shaft. Not a flex family; do not call the bag mixed because of it.",
        ),
    ]


HEADS: list[dict] = []
HEADS += _brand_heads(
    "Titleist",
    "TS",
    {"players_pw": 46.0, "gi_pw": 43.0, "sgi_pw": 41.0},
)
HEADS += _brand_heads(
    "TaylorMade",
    "TM",
    {"players_pw": 47.0, "gi_pw": 42.0, "sgi_pw": 40.0},
)
HEADS += _brand_heads(
    "Callaway",
    "CW",
    {"players_pw": 46.0, "gi_pw": 43.0, "sgi_pw": 41.0},
)

SHAFTS: list[dict] = []
SHAFTS += _brand_shafts("Titleist", "TS", {"nudge": 0})
SHAFTS += _brand_shafts("TaylorMade", "TM", {"nudge": -2})
SHAFTS += _brand_shafts("Callaway", "CW", {"nudge": 1})


def get_catalog() -> dict:
    """Return the v1 catalog. Callers must treat the dicts as read-only."""
    return {"brands": BRANDS, "heads": HEADS, "shafts": SHAFTS}
