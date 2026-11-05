"""Assemble three full bags from a profile and the v1 catalog.

The rule functions in ``specs.py`` decide the target. This module only
matches those targets to real heads and shafts and writes the rationale.
"""

from __future__ import annotations

from app.catalog.data import get_catalog
from app.fitting.profile import GolferProfile
from app.fitting.rulebook import (
    BASE_SHAFT_WEIGHT,
    BRAND_ORDER,
    DISCLAIMER,
    FLEX_ORDER,
    PROFILE_WEIGHT_BIAS,
    SET_CATEGORY_SHIFT,
    SET_LAUNCH,
    SET_LOFT_BIAS,
    SET_SHAFT_PROFILE,
    STANDARD_LENGTH_IN,
)
from app.fitting.specs import (
    apply_medical,
    base_driver_loft,
    estimate_category,
    estimate_grip,
    estimate_swing_speed,
    estimate_wrist_to_floor,
    flex_for_speed,
    length_and_lie,
    shift_category,
)

BRAND_ALIASES = {
    "titleist": "Titleist",
    "taylormade": "TaylorMade",
    "taylor": "TaylorMade",
    "taylormadegolf": "TaylorMade",
    "callaway": "Callaway",
    "callawaygolf": "Callaway",
}


def canonical_brand(name: str | None) -> str | None:
    """Rule BRAND-1 alias match. Unknown strings are ignored, not guessed."""
    if not name:
        return None
    key = "".join(ch for ch in name.lower() if ch.isalnum())
    return BRAND_ALIASES.get(key)


def assign_brands(profile: GolferProfile) -> dict:
    """Rule BRAND-1. Preference wins over the current bag; the other two differ."""
    stated = None
    source = None
    for candidate in list(profile.preferred_brands or []) + [profile.current_brand]:
        brand = canonical_brand(candidate)
        if brand:
            stated = brand
            source = "preferred" if candidate in (profile.preferred_brands or []) else "current"
            break
    preference_stated = stated is not None
    preference = stated or "Titleist"
    rest = [brand for brand in BRAND_ORDER if brand != preference]
    return {
        "distance": rest[0],
        "control": rest[1],
        "preference": preference,
        "preference_stated": preference_stated,
        "preference_source": source,
        "current": canonical_brand(profile.current_brand),
    }


def _cat_index(category: str) -> int:
    order = [
        "super_game_improvement",
        "game_improvement",
        "players_distance",
        "players",
    ]
    return order.index(category) if category in order else 1


def _snap_loft(target: float, options: list[float]) -> float:
    """Nearest offered loft. Ties go to the higher loft (easier launch)."""
    return min(options, key=lambda loft: (abs(loft - target), -loft))


def pick_head(
    heads: list[dict],
    club_type: str,
    category: str,
    launch: str,
    target_loft: float | None,
) -> dict:
    """Closest head in this brand for the slot. Score is explained in SHAFT-1's neighbour."""
    pool = [head for head in heads if head["club_type"] == club_type]
    if not pool:
        raise LookupError(f"No {club_type} head in catalog slice")

    def score(head: dict) -> float:
        value = 0.0
        if head["category"] in {
            "super_game_improvement",
            "game_improvement",
            "players_distance",
            "players",
        }:
            value -= abs(_cat_index(head["category"]) - _cat_index(category)) * 20
        if head["launch"] == launch:
            value += 18
        elif head["launch"] == "mid":
            value += 6
        lofts = head.get("lofts") or []
        if target_loft is not None and lofts:
            error = min(abs(loft - target_loft) for loft in lofts)
            value -= error * 8
        return value

    return max(pool, key=score)


def pick_shaft(
    shafts: list[dict],
    family: str,
    flex: str,
    profile: str,
    weight_delta_g: float,
) -> tuple[dict, str, float]:
    """Rule SHAFT-1. Returns (shaft, flex_used, weight_g).

    Exact flex is worth more than the ideal profile, so a bag stays in one
    flex family unless that brand truly does not make it.
    """
    pool = [shaft for shaft in shafts if family in shaft["families"]]
    if not pool:
        raise LookupError(f"No {family} shaft in catalog slice")
    base = BASE_SHAFT_WEIGHT[family].get(flex, BASE_SHAFT_WEIGHT[family]["R"])
    target_weight = base + PROFILE_WEIGHT_BIAS[profile] + weight_delta_g
    want = FLEX_ORDER.index(flex)

    def flex_choice(shaft: dict) -> tuple[str, int]:
        best = min(
            shaft["flex_weights"],
            key=lambda name: abs(FLEX_ORDER.index(name) - want),
        )
        return best, abs(FLEX_ORDER.index(best) - want)

    def score(shaft: dict) -> float:
        best, steps = flex_choice(shaft)
        flex_score = {0: 80, 1: 30, 2: 10}.get(steps, 0)
        if shaft["profile"] == profile:
            profile_score = 25
        elif shaft["profile"] == "neutral":
            profile_score = 10
        else:
            profile_score = 0
        weight_score = -abs(shaft["flex_weights"][best] - target_weight) * 0.35
        return flex_score + profile_score + weight_score

    chosen = max(pool, key=score)
    used, _steps = flex_choice(chosen)
    return chosen, used, float(chosen["flex_weights"][used])


def _fairway_loft(swing_speed: float, orientation: str) -> tuple[str, float]:
    """Rule BAG-1 fairway choice."""
    if orientation == "distance" and swing_speed >= 85:
        return "3-wood", 15.0
    if orientation == "control":
        return "5-wood", 18.0
    if swing_speed >= 90:
        return "3-wood", 15.0
    return "5-wood", 18.0


def _long_club(
    orientation: str,
    category: str,
    swing_speed: float,
    avoid_heavy: bool,
) -> tuple[str, str, float]:
    """Return (club_type, label, loft) for the hybrid-or-long-iron slot."""
    forgiving = category in {"game_improvement", "super_game_improvement"}
    if orientation == "distance" or forgiving or swing_speed < 98 or avoid_heavy:
        loft = 22.0 if swing_speed < 90 else 19.0
        return "hybrid", f"{loft:.0f}° hybrid", loft
    return "utility_iron", "utility iron", 18.0


def _wedge_lofts(pw_loft: float, available: list[float]) -> list[tuple[str, float]]:
    """Gap / sand / lob snapped to lofts the wedge head actually offers."""
    targets = [
        ("Gap wedge", pw_loft + 4),
        ("Sand wedge", 54.0 if pw_loft + 4 <= 50 else 56.0),
        ("Lob wedge", 58.0 if pw_loft + 4 <= 50 else 60.0),
    ]
    chosen: list[tuple[str, float]] = []
    used: set[float] = set()
    for label, target in targets:
        loft = _snap_loft(target, available)
        if loft in used:
            remaining = [item for item in available if item not in used and item > loft]
            if remaining:
                loft = remaining[0]
        used.add(loft)
        chosen.append((label, loft))
    return chosen


def _putter_style(category: str, handicap: float | None, flags: list[str]) -> str:
    """Rule PUTT-1."""
    if "arthritis" in flags or category == "super_game_improvement":
        return "mallet"
    if handicap is not None and handicap > 20:
        return "mallet"
    return "blade"


def _club(
    *,
    slot: str,
    label: str,
    head: dict,
    shaft: dict,
    shaft_flex: str,
    weight_g: float,
    loft: float | None,
    length_delta: float,
    lie_delta: float,
    lie_name: str,
    grip: str,
    gender: str,
    length_family: str,
    extra_notes: list[str] | None = None,
) -> dict:
    standard = STANDARD_LENGTH_IN[gender][length_family]
    delta = length_delta
    notes = list(extra_notes or [])
    if length_family == "putter":
        # PUTT-1: half the iron adjustment, still on a 1/4 inch grid.
        delta = round(length_delta / 2 * 4) / 4
        notes.append("Putter length uses half the iron adjustment. Confirm putter lie on its own.")
        lie_name = "confirm separately"
        lie_delta_out = None
    else:
        lie_delta_out = lie_delta
    return {
        "slot": slot,
        "label": label,
        "loft": loft,
        "length_delta_in": delta,
        "recommended_length_in": round(standard + delta, 2),
        "standard_length_in": standard,
        "lie_delta_deg": lie_delta_out,
        "lie_label": lie_name,
        "grip": grip,
        "flex": shaft_flex,
        "head": {
            "id": head["id"],
            "brand": head["brand"],
            "model": head["model"],
            "category": head["category"],
            "launch": head["launch"],
            "spin": head["spin"],
            "club_type": head["club_type"],
            "set_makeup": head.get("set_makeup"),
        },
        "shaft": {
            "id": shaft["id"],
            "brand": shaft["brand"],
            "model": shaft["model"],
            "flex": shaft_flex,
            "weight_g": weight_g,
            "profile": shaft["profile"],
            "launch": shaft["launch"],
            "torque": shaft["torque"],
        },
        "notes": notes,
    }


def _build_set(
    orientation: str,
    profile: GolferProfile,
    target: dict,
    brands: dict,
) -> dict:
    catalog = get_catalog()
    brand = brands[orientation]
    heads = [head for head in catalog["heads"] if head["brand"] == brand]
    shafts = [shaft for shaft in catalog["shafts"] if shaft["brand"] == brand]
    flex = target["flex"]
    # Set bias is applied to the pre-medical category, then capped by MED-1 so a
    # control bag cannot walk a low-bone-density golfer back into a players head.
    category = shift_category(
        target["head_category_before_medical"], SET_CATEGORY_SHIFT[orientation]
    )
    if _cat_index(category) > _cat_index(target["head_category"]):
        category = target["head_category"]
    launch = SET_LAUNCH[orientation]
    shaft_profile = SET_SHAFT_PROFILE[orientation]
    weight_delta = target["shaft_weight_delta_g"]
    raw_driver_loft = target["driver_loft_base"] + SET_LOFT_BIAS[orientation] + target["medical_loft_delta"]
    raw_driver_loft = max(7.5, min(16.0, raw_driver_loft))

    driver_head = pick_head(heads, "driver", category, launch, raw_driver_loft)
    driver_loft = _snap_loft(raw_driver_loft, driver_head["lofts"])
    driver_shaft, driver_flex, driver_weight = pick_shaft(
        shafts, "driver", flex, shaft_profile, weight_delta
    )

    fw_label, fw_loft_target = _fairway_loft(target["swing_speed_mph"], orientation)
    fw_head = pick_head(heads, "fairway_wood", category, launch, fw_loft_target)
    fw_loft = _snap_loft(fw_loft_target, fw_head["lofts"])
    fw_shaft, fw_flex, fw_weight = pick_shaft(
        shafts, "fairway", flex, shaft_profile, weight_delta
    )

    long_type, long_label, long_target = _long_club(
        orientation,
        target["head_category"],
        target["swing_speed_mph"],
        target["avoid_heavy"],
    )
    long_head = pick_head(heads, long_type, category, launch, long_target)
    long_loft = _snap_loft(long_target, long_head["lofts"])
    long_family = "hybrid" if long_type == "hybrid" else "utility_iron"
    long_shaft, long_flex, long_weight = pick_shaft(
        shafts, long_family, flex, shaft_profile, weight_delta
    )

    iron_head = pick_head(heads, "iron_set", category, launch, None)
    iron_shaft, iron_flex, iron_weight = pick_shaft(
        shafts, "iron", flex, shaft_profile, weight_delta
    )

    wedge_head = pick_head(heads, "wedge", category, "mid", None)
    wedge_shaft, wedge_flex, wedge_weight = pick_shaft(
        shafts, "wedge", flex, "control" if orientation == "control" else "neutral", weight_delta
    )
    wedges = _wedge_lofts(iron_head["pw_loft"], wedge_head["lofts"])

    putter_head = pick_head(heads, "putter", category, "mid", None)
    putter_shaft, putter_flex, putter_weight = pick_shaft(
        shafts, "putter", "R", "neutral", 0
    )
    style = _putter_style(target["head_category"], profile.handicap, profile.medical_flags)

    gender = profile.gender
    length_delta = target["length_delta_in"]
    lie_delta = target["lie_delta_deg"]
    lie_name = target["lie_label"]
    grip = target["grip"]

    clubs = [
        _club(
            slot="driver",
            label="Driver",
            head=driver_head,
            shaft=driver_shaft,
            shaft_flex=driver_flex,
            weight_g=driver_weight,
            loft=driver_loft,
            length_delta=length_delta,
            lie_delta=lie_delta,
            lie_name=lie_name,
            grip=grip,
            gender=gender,
            length_family="driver",
        ),
        _club(
            slot="fairway",
            label=fw_label,
            head=fw_head,
            shaft=fw_shaft,
            shaft_flex=fw_flex,
            weight_g=fw_weight,
            loft=fw_loft,
            length_delta=length_delta,
            lie_delta=lie_delta,
            lie_name=lie_name,
            grip=grip,
            gender=gender,
            length_family="fairway",
        ),
        _club(
            slot="long_club",
            label=long_label,
            head=long_head,
            shaft=long_shaft,
            shaft_flex=long_flex,
            weight_g=long_weight,
            loft=long_loft,
            length_delta=length_delta,
            lie_delta=lie_delta,
            lie_name=lie_name,
            grip=grip,
            gender=gender,
            length_family=long_family,
        ),
        _club(
            slot="irons",
            label=f"Irons {iron_head['set_makeup']}",
            head=iron_head,
            shaft=iron_shaft,
            shaft_flex=iron_flex,
            weight_g=iron_weight,
            loft=iron_head["pw_loft"],
            length_delta=length_delta,
            lie_delta=lie_delta,
            lie_name=lie_name,
            grip=grip,
            gender=gender,
            length_family="iron",
            extra_notes=[
                f"Loft shown is the pitching wedge ({iron_head['pw_loft']:.0f}°). "
                "Length shown is the 7-iron."
            ],
        ),
    ]
    for label, loft in wedges:
        clubs.append(
            _club(
                slot="wedge",
                label=label,
                head=wedge_head,
                shaft=wedge_shaft,
                shaft_flex=wedge_flex,
                weight_g=wedge_weight,
                loft=loft,
                length_delta=length_delta,
                lie_delta=lie_delta,
                lie_name=lie_name,
                grip=grip,
                gender=gender,
                length_family="wedge",
            )
        )
    clubs.append(
        _club(
            slot="putter",
            label=f"Putter ({style})",
            head=putter_head,
            shaft=putter_shaft,
            shaft_flex=putter_flex,
            weight_g=putter_weight,
            loft=style == "mallet" and 3.0 or 3.5,
            length_delta=length_delta,
            lie_delta=lie_delta,
            lie_name=lie_name,
            grip=grip,
            gender=gender,
            length_family="putter",
            extra_notes=[f"Order the {style} hosel/style of {putter_head['model']}."],
        )
    )

    flexes = {club["flex"] for club in clubs if club["slot"] != "putter"}
    consistent = flexes == {flex}
    mix_notes = []
    if not consistent:
        for club in clubs:
            if club["slot"] != "putter" and club["flex"] != flex:
                mix_notes.append(
                    f"{club['label']} is {club['flex']} flex because {brand} "
                    f"does not offer {club['shaft']['model']} in {flex}."
                )
    if putter_flex != flex:
        mix_notes.append(
            "The putter shaft is a stock stability shaft and is not part of the flex family."
        )

    return {
        "id": orientation,
        "name": {
            "distance": "Distance",
            "control": "Control",
            "preference": "Brand match",
        }[orientation],
        "brand": brand,
        "flex_family": flex,
        "flex_consistent": consistent,
        "mix_notes": mix_notes,
        "category_built": category,
        "clubs": clubs,
        "rationale": _rationale(orientation, profile, target, brands, clubs, category),
    }


def _rationale(
    orientation: str,
    profile: GolferProfile,
    target: dict,
    brands: dict,
    clubs: list[dict],
    built_category: str,
) -> str:
    driver = next(club for club in clubs if club["slot"] == "driver")
    fairway = next(club for club in clubs if club["slot"] == "fairway")
    long_club = next(club for club in clubs if club["slot"] == "long_club")
    irons = next(club for club in clubs if club["slot"] == "irons")
    wedges = [club for club in clubs if club["slot"] == "wedge"]
    putter = next(club for club in clubs if club["slot"] == "putter")
    speed = target["swing_speed_mph"]
    source = {
        "measured": "measured",
        "blended": "blended from your handicap and the physical estimate",
        "estimated": "estimated",
    }[target["swing_speed_source"]]

    sentences = [
        (
            f"Driver speed is {speed:.0f} mph ({source}), which maps to {target['flex_before_medical']} "
            f"flex before medical rules"
            + (
                f" and {target['flex']} flex after them."
                if target["flex"] != target["flex_before_medical"]
                else f", so the bag is built in {target['flex']}."
            )
        ),
        (
            f"Wrist-to-floor {target['wrist_to_floor_cm']:.0f} cm "
            f"({'estimated' if target['wrist_to_floor_estimated'] else 'measured'}) "
            f"puts length at {target['length_delta_in']:+.2f} in versus the "
            f"{profile.gender} standard and lie at {target['lie_delta_deg']:+.1f}° "
            f"({target['lie_label']}). Grip is {target['grip']}."
        ),
    ]
    if target["medical_notes"]:
        sentences.append(" ".join(target["medical_notes"]))
    else:
        sentences.append("No medical flags were supplied, so nothing was softened after the fit.")

    if orientation == "distance":
        sentences.append(
            f"This is the distance bag: {driver['head']['model']} at {driver['loft']:.1f}° "
            f"with the lighter {driver['shaft']['model']} ({driver['shaft']['weight_g']:.0f} g, "
            f"{driver['shaft']['flex']} flex), aimed at carry rather than a piercing flight. "
            f"The head category used here is {built_category.replace('_', ' ')}."
        )
    elif orientation == "control":
        sentences.append(
            f"This is the control bag: {driver['head']['model']} at {driver['loft']:.1f}° "
            f"with {driver['shaft']['model']} ({driver['shaft']['weight_g']:.0f} g), "
            f"a lower-launch, heavier profile in the same {target['flex']} family when the "
            f"catalog allows it. Head category built: {built_category.replace('_', ' ')}."
        )
    else:
        if brands["preference_stated"]:
            why = (
                f"Your stated {brands['preference_source']} brand is {brands['preference']}"
                + (
                    f"; the current bag ({brands['current']}) was not used for this set."
                    if brands["current"] and brands["current"] != brands["preference"]
                    else "."
                )
            )
        else:
            why = (
                "No brand preference or current set was given, so this neutral bag "
                "defaults to Titleist and the other two bags cover TaylorMade and Callaway."
            )
        sentences.append(
            f"This is the brand-match bag at the baseline spec — not the distance or "
            f"control bias. {why} Driver is {driver['head']['model']} at {driver['loft']:.1f}° "
            f"with {driver['shaft']['model']}."
        )

    wedge_lofts = "/".join(f"{club['loft']:.0f}°" for club in wedges)
    sentences.append(
        f"The rest of the bag is a {fairway['label']} ({fairway['head']['model']}), "
        f"a {long_club['label']} ({long_club['head']['model']}), "
        f"{irons['head']['model']} ({irons['head']['set_makeup']}) with "
        f"{irons['shaft']['model']}, wedges at {wedge_lofts} ({wedge_lofts and wedges[0]['head']['model']}), "
        f"and a {putter['label']}."
    )
    return " ".join(sentences)


def recommend(profile: GolferProfile, catalog: dict | None = None) -> dict:
    """Return three bags plus the target spec a fitter can audit.

    ``catalog`` is accepted so tests can inject a slice; production uses
    :func:`app.catalog.data.get_catalog`.
    """
    del catalog  # the matcher reads the module catalog; argument reserved for later extension
    profile = profile.normalized()
    assumptions: list[str] = []
    rules = ["SS-1", "SS-2", "FLEX-1", "LL-1", "LL-2", "LL-3", "LL-4", "GRIP-1", "HC-1", "LOFT-1", "SET-1", "BRAND-1", "BAG-1", "PUTT-1", "SHAFT-1"]

    if profile.height_cm < 145 or profile.height_cm > 205:
        assumptions.append(
            "Height is outside the range this static chart was anchored on. "
            "Treat length and lie as a rough start and check them on a board."
        )
    wtf, estimated = estimate_wrist_to_floor(profile)
    if estimated:
        assumptions.append(
            "Wrist-to-floor was not measured, so it was estimated from height and "
            "body type (WTF-EST). A tape measure in golf posture will beat this."
        )
        rules.append("WTF-EST")

    length_delta, lie_delta, lie_name = length_and_lie(profile, wtf)
    speed = estimate_swing_speed(profile)
    assumptions.extend(speed.notes)
    if speed.source == "measured":
        rules.append("SS-0")
    if speed.strength_mph != 0:
        rules.append("SS-3")
    if speed.cardio_mph != 0:
        rules.append("SS-4")
    if speed.bmi_mph != 0:
        rules.append("SS-5")
    if speed.source == "blended":
        rules.append("SS-6")

    flex_before = flex_for_speed(speed.mph)
    grip = estimate_grip(profile)
    category = estimate_category(profile, speed.mph)
    loft = base_driver_loft(speed.mph)
    medical = apply_medical(flex_before, grip, category, profile.medical_flags)
    if medical.applied:
        rules.append("MED-1")

    brands = assign_brands(profile)
    target = {
        "gender": profile.gender,
        "age": profile.age,
        "height_cm": profile.height_cm,
        "weight_kg": profile.weight_kg,
        "body_type": profile.body_type,
        "wrist_to_floor_cm": wtf,
        "wrist_to_floor_estimated": estimated,
        "swing_speed_mph": speed.mph,
        "swing_speed_source": speed.source,
        "swing_speed_detail": {
            "metric_mph": speed.metric_mph,
            "age_mph": speed.age_mph,
            "strength_mph": speed.strength_mph,
            "cardio_mph": speed.cardio_mph,
            "bmi_mph": speed.bmi_mph,
            "handicap_implied_mph": speed.handicap_implied_mph,
        },
        "flex_before_medical": flex_before,
        "flex": medical.flex,
        "length_delta_in": length_delta,
        "lie_delta_deg": lie_delta,
        "lie_label": lie_name,
        "grip": medical.grip,
        "head_category": medical.category,
        "head_category_before_medical": category,
        "driver_loft_base": loft,
        "medical_loft_delta": medical.loft_delta,
        "shaft_weight_delta_g": medical.weight_delta_g,
        "avoid_heavy": medical.avoid_heavy,
        "medical_flags": list(profile.medical_flags),
        "medical_notes": medical.notes,
        "brands": brands,
    }

    sets = [
        _build_set(orientation, profile, target, brands)
        for orientation in ("distance", "control", "preference")
    ]
    return {
        "target": target,
        "assumptions": assumptions,
        "rules_fired": rules,
        "sets": sets,
        "disclaimer": DISCLAIMER,
    }
