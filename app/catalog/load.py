"""Turn data/club-catalog.csv into the heads and shafts the fitter uses.

The file is one row per loft or flex. The engine wants one head per model
(with its loft ladder) and one shaft per model (with a weight per flex).
Shafts in the file are shaft companies, not the club brand on the head.
"""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path

CATALOG_PATH = Path(__file__).resolve().parents[2] / "data" / "club-catalog.csv"
# Same order as FLEX_ORDER in the rulebook. Kept here so loading the CSV
# does not import the fitting engine.
_FLEX_ORDER = ("L", "A", "R", "S", "X")

_CLUB_TYPE = {
    "driver": "driver",
    "fairway": "fairway_wood",
    "hybrid": "hybrid",
    "iron": "iron_set",
    "wedge": "wedge",
    "putter": "putter",
}

_IRON_LABELS = ["2", "3", "4", "5", "6", "7", "8", "9", "PW", "AW", "GW", "SW"]
_MALLET = ("spider", "mallet", "2-ball", "2 ball", "jailbird", "double wide", "tomcat", "phantom")


def _slug(*parts: str, limit: int = 60) -> str:
    raw = "-".join(parts)
    raw = "".join(ch.lower() if ch.isalnum() else "-" for ch in raw)
    while "--" in raw:
        raw = raw.replace("--", "-")
    return raw.strip("-")[:limit] or "item"


def _first_float(text: str | None) -> float | None:
    if not text:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    return float(match.group()) if match else None


def _year(text: str | None) -> int | None:
    match = re.search(r"(20\d{2})", text or "")
    return int(match.group(1)) if match else None


def _band(text: str | None) -> str:
    token = (text or "").strip().lower().replace(" ", "")
    if not token:
        return "mid"
    if "mid" in token and ("high" in token or "low" in token):
        return "mid"
    if token in {"m/h", "mh", "m/l", "ml", "l/m"}:
        return "mid"
    if "high" in token or token == "h":
        return "high"
    if "low" in token or token == "l":
        return "low"
    return "mid"


def _lofts(row: dict) -> list[float]:
    found: list[float] = []
    primary = _first_float(row.get("loft_deg"))
    if primary is not None:
        found.append(primary)
    for part in (row.get("loft_options") or "").split(";"):
        value = _first_float(part)
        if value is not None and value not in found:
            found.append(value)
    return found


def _classify(club_type: str, model: str) -> tuple[str, str, str, str, str | None]:
    """Return category, launch, spin, offset, putter style."""
    name = model.lower()
    if club_type == "putter":
        style = "mallet" if any(word in name for word in _MALLET) else "blade"
        return "players", "mid", "low", "low", style
    if club_type == "wedge":
        return "players", "mid", "high", "low", None
    if club_type == "hybrid":
        return "game_improvement", "high", "mid", "mid", None
    if club_type == "fairway_wood":
        if "max" in name:
            return "game_improvement", "high", "mid", "mid", None
        return "players_distance", "mid", "mid", "mid", None

    if any(word in name for word in ("hot metal hl", " elyte hl", "elyte hl", "max-d", "sft", "ultra-lite", "max+", "(max)")):
        return "super_game_improvement", "high", "mid", "high", None
    if any(word in name for word in ("lst", "tour-1", "gt4", "zxi ls", "dynapwr ls", "blueprint t", "t100", "zxi7")):
        return "players", "low", "low", "low", None
    if any(word in name for word in ("blueprint s", "t150", "i240")):
        return "players", "low", "low", "low", None
    if "hot metal pro" in name or any(word in name for word in ("t250", "p790", "i540", "gt2", "gt3", "qi35", "jpx one", " zxi")):
        if "hot metal pro" in name or any(word in name for word in ("t250", "p790", "i540", "gt2", "gt3")):
            launch = "mid" if "max" not in name else "high"
            category = "players_distance" if "max" not in name else "game_improvement"
            return category, launch, "mid", "mid", None
        return "players_distance", "mid", "mid", "mid", None
    if any(word in name for word in ("max", "hot metal", "t350", "elyte", "dynapwr", "black ops")):
        return "game_improvement", "high", "mid", "high", None
    return "players_distance", "mid", "mid", "mid", None


def _map_flex(raw: str | None) -> str | None:
    token = (raw or "").strip().lower()
    if not token:
        return None
    if token in {"l", "lite", "ladies", "4.0"}:
        return "L"
    if token in {"a", "lite/a", "soft regular", "r2", "r3", "senior"} or token.startswith("02"):
        return "A"
    if token in {"r", "regular", "r1", "5.0"} or "(r)" in token:
        return "R"
    if token in {"sr", "5.5", "r+", "regular+"}:
        return "S" if token == "5.5" else "R"
    if token in {"s", "stiff", "6.0", "s200", "tour s", "s+", "stiff+", "6.5"} or "(s)" in token:
        return "S"
    if token in {"x", "x-stiff", "xstiff", "7.0", "x100", "tour x", "tx", "x-stiff+"} or "(x)" in token or token.startswith("05"):
        return "X"
    return None


def _flex_rank(raw: str) -> int:
    token = raw.strip().lower()
    if token in {"l", "a", "r", "regular", "s", "stiff", "x", "x-stiff"}:
        return 0
    if "+" in token or token == "tx":
        return 2
    return 1


def _dedupe_ids(rows: list[dict], limit: int) -> None:
    seen: dict[str, int] = {}
    for row in rows:
        base = row["id"][:limit]
        count = seen.get(base, 0)
        seen[base] = count + 1
        row["id"] = base if count == 0 else f"{base[: limit - 2]}-{count}"


def _heads(rows: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for row in rows:
        club_type = _CLUB_TYPE.get((row.get("club_type") or "").strip())
        brand = (row.get("brand") or "").strip()
        model = (row.get("model") or "").strip()
        if not club_type or not brand or not model:
            continue
        grouped[(brand, model, club_type)].append(row)

    heads: list[dict] = []
    for (brand, model, club_type), items in grouped.items():
        lofts: list[float] = []
        for item in items:
            for loft in _lofts(item):
                if loft not in lofts:
                    lofts.append(loft)
        if club_type == "putter" and not lofts:
            lofts = [3.0]
        if not lofts:
            continue
        category, launch, spin, offset, style = _classify(club_type, model)
        labels = []
        for item in items:
            label = (item.get("gender_or_set") or "").strip().upper()
            if label in _IRON_LABELS and label not in labels:
                labels.append(label)
        labels.sort(key=lambda label: _IRON_LABELS.index(label))
        pw = None
        for item in items:
            if (item.get("gender_or_set") or "").strip().upper() == "PW":
                pw = _first_float(item.get("loft_deg"))
        if pw is None and club_type == "iron_set":
            under = [loft for loft in lofts if loft <= 50]
            pw = max(under) if under else max(lofts)
        notes = next((item.get("material_notes") or item.get("notes") or "" for item in items if item.get("material_notes") or item.get("notes")), "")
        length = next((_first_float(item.get("length_in")) for item in items if _first_float(item.get("length_in"))), None)
        blurb_bits = [notes.split("|")[0].strip()]
        if length:
            blurb_bits.append(f"Stock length {length:g} in.")
        stock = next((item.get("stock_shaft") for item in items if item.get("stock_shaft")), "")
        if stock:
            blurb_bits.append(f"Stock shaft: {stock}.")
        heads.append(
            {
                "id": _slug(brand, model, club_type),
                "brand": brand,
                "model": model[:120],
                "club_type": club_type,
                "category": category,
                "launch": launch,
                "spin": spin,
                "offset": offset,
                "lofts": lofts,
                "standard_loft": lofts[len(lofts) // 2],
                "pw_loft": pw,
                "set_makeup": f"{labels[0]}-{labels[-1]}" if labels else None,
                "year": _year(items[0].get("year_or_line")),
                "putter_style": style,
                "blurb": " ".join(bit for bit in blurb_bits if bit)[:500],
            }
        )
    labels = {
        "driver": "driver",
        "fairway_wood": "fairway",
        "hybrid": "hybrid",
        "iron_set": "irons",
        "wedge": "wedge",
        "putter": "putter",
    }
    name_counts: dict[tuple[str, str], int] = defaultdict(int)
    for head in heads:
        name_counts[(head["brand"], head["model"])] += 1
    for head in heads:
        if name_counts[(head["brand"], head["model"])] > 1 and head["club_type"] != "driver":
            head["model"] = f"{head['model']} {labels[head['club_type']]}"
    for head in heads:
        head["id"] = _slug(head["brand"], head["model"], head["club_type"])
    _dedupe_ids(heads, limit=60)
    heads.sort(key=lambda head: (head["brand"], head["club_type"], head["model"]))
    return heads


def _shafts(rows: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        brand = (row.get("brand") or "").strip()
        model = (row.get("model") or "").strip()
        if brand and model:
            grouped[(brand, model)].append(row)

    shafts: list[dict] = []
    for (brand, model), items in grouped.items():
        weights: dict[str, float] = {}
        ranks: dict[str, int] = {}
        torques: list[float] = []
        launches: list[str] = []
        spins: list[str] = []
        for item in items:
            flex = _map_flex(item.get("flex"))
            weight = _first_float(item.get("weight_g"))
            torque = _first_float(item.get("torque_deg"))
            if torque is not None:
                torques.append(torque)
            if item.get("launch"):
                launches.append(item["launch"])
            if item.get("spin"):
                spins.append(item["spin"])
            if flex is None or weight is None:
                continue
            rank = _flex_rank(item.get("flex") or "")
            if flex not in weights or rank < ranks[flex]:
                weights[flex] = weight
                ranks[flex] = rank
        if not weights:
            continue
        launch = _band(launches[0] if launches else "")
        spin = _band(spins[0] if spins else "")
        profile = {"low": "control", "high": "distance"}.get(launch, "neutral")
        sample = items[0]
        tip = (sample.get("tip_type") or "").lower()
        material = (sample.get("material") or sample.get("category") or "").lower()
        length = _first_float(sample.get("length_raw_in"))
        name = model.lower()
        if material == "steel" or "iron" in tip:
            families = ["iron", "wedge"]
        elif "hybrid" in name or (length is not None and length <= 42):
            families = ["hybrid", "utility_iron"]
        else:
            families = ["driver", "fairway"]
            if min(weights.values()) >= 65:
                families.append("hybrid")
        torque = round(sum(torques) / len(torques), 2) if torques else None
        shafts.append(
            {
                "id": _slug(brand, model, limit=72),
                "brand": brand,
                "model": model[:120],
                "families": families,
                "profile": profile,
                "launch": launch,
                "spin": spin,
                "flex_weights": {flex: weights[flex] for flex in _FLEX_ORDER if flex in weights},
                "torque": torque,
                "blurb": (sample.get("notes") or "Published shaft spec.").split("|")[0].strip()[:400],
            }
        )
    if not any("hybrid" in shaft["families"] for shaft in shafts):
        for shaft in shafts:
            if "driver" in shaft["families"]:
                shaft["families"].append("hybrid")
    shafts.append(
        {
            "id": "stock-putter-shaft",
            "brand": "Stock",
            "model": "Putter stability",
            "families": ["putter"],
            "profile": "neutral",
            "launch": "mid",
            "spin": "low",
            "flex_weights": {"R": 110.0},
            "torque": 1.0,
            "blurb": "The source file has no putter shafts. Every bag uses this stock shaft.",
        }
    )
    shafts.sort(key=lambda shaft: (shaft["brand"], shaft["model"]))
    _dedupe_ids(shafts, limit=72)
    return shafts


def build_catalog(path: Path | None = None) -> dict:
    source = path or CATALOG_PATH
    with source.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    heads = _heads([row for row in rows if row.get("record_type") == "head"])
    shafts = _shafts([row for row in rows if row.get("record_type") == "shaft"])
    driver_brands = {head["brand"] for head in heads if head["club_type"] == "driver"}
    names = sorted({head["brand"] for head in heads} | {shaft["brand"] for shaft in shafts})
    brands = []
    for name in names:
        count = sum(1 for head in heads if head["brand"] == name)
        shaft_count = sum(1 for shaft in shafts if shaft["brand"] == name)
        if name == "Stock":
            blurb = "Stand-in putter shaft. The catalog file does not list one."
        elif count:
            blurb = f"{count} club heads from the supplied catalog."
        else:
            blurb = f"{shaft_count} shafts from the supplied catalog."
        brands.append(
            {
                "id": _slug(name, limit=32),
                "name": name,
                "country": "",
                "has_driver": name in driver_brands,
                "blurb": blurb,
            }
        )
    return {"brands": brands, "heads": heads, "shafts": shafts}
