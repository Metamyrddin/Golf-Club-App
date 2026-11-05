"""Pure fitting calculations. No catalog, no I/O.

Each function cites the rule id from ``rulebook.RULES``. Medical changes are
applied by :func:`apply_medical` and must stay last in the pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.fitting.profile import GolferProfile
from app.fitting.rulebook import (
    AGE_DECLINE_PER_YEAR,
    AGE_PEAK_END,
    AGE_UNDER_18_DELTA,
    BASE_DRIVER_SS,
    BENCH_MPH_PER_RATIO,
    BMI_HIGH,
    BMI_LOW,
    BMI_VERY_HIGH,
    BODY_LENGTH_IN,
    BODY_LIE_DEG,
    CATEGORY_ORDER,
    CM_PER_INCH,
    EXPECTED_BENCH_RATIO,
    EXPECTED_SQUAT_RATIO,
    FITNESS_MPH,
    FLEX_ORDER,
    FLEX_UPPER,
    GRIP_ORDER,
    HAND_CM_BOUNDS,
    HANDICAP_WEIGHT_DEMOGRAPHICS_ONLY,
    HANDICAP_WEIGHT_WITH_FITNESS,
    LENGTH_CLAMP_IN,
    LENGTH_REFERENCE,
    LIE_CLAMP_DEG,
    MEDICAL_LOFT_CAP,
    MEDICAL_LOFT_DELTA,
    MEDICAL_WEIGHT_CAP,
    RHR_CENTER,
    RHR_CLAMP,
    RHR_MPH_PER_BPM,
    SQUAT_MPH_PER_RATIO,
    SS_CLAMP,
    STRENGTH_CLAMP,
    VO2_CENTER,
    VO2_CLAMP,
    VO2_MPH_PER_ML,
    WTF_EST_BODY_CM,
    starting_driver_loft,
)


import math


def _clamp(value: float, bounds: tuple[float, float]) -> float:
    return max(bounds[0], min(bounds[1], value))


def _round_step(value: float, step: float) -> float:
    """Round half away from zero so a +0.25 inch nudge is not banker's-rounded away."""
    if value == 0:
        return 0.0
    scaled = abs(value) / step
    rounded = math.floor(scaled + 0.5) * step
    # Avoid -0.0
    rounded = round(rounded, 4)
    return math.copysign(rounded, value)


def _round_quarter(value: float) -> float:
    return _round_step(value, 0.25)


def _round_half(value: float) -> float:
    return _round_step(value, 0.5)


def estimate_wrist_to_floor(profile: GolferProfile) -> tuple[float, bool]:
    """Rule WTF-EST. Returns (cm, estimated?).

    Rule LL-2: a measured value is returned untouched — height does not
    average it back toward the population line.
    """
    if profile.wrist_to_floor_cm:
        return float(profile.wrist_to_floor_cm), False
    ref = LENGTH_REFERENCE[profile.gender]
    ratio = ref["wtf_cm"] / ref["height_cm"]
    estimated = profile.height_cm * ratio
    tweak = WTF_EST_BODY_CM.get(profile.body_type or "", 0.0)
    return round(estimated + tweak, 1), True


def length_and_lie(
    profile: GolferProfile, wtf_cm: float
) -> tuple[float, float, str]:
    """Rules LL-1, LL-3, LL-4.

    Returns (length_delta_in, lie_delta_deg, lie_label).
    Positive length is longer than the gender standard. Positive lie is upright.
    """
    ref_wtf = LENGTH_REFERENCE[profile.gender]["wtf_cm"]
    wtf_inches = (wtf_cm - ref_wtf) / CM_PER_INCH
    body = profile.body_type or ""
    # LL-4 is applied before the clamp so the nudge cannot push past the chart.
    delta_in = _clamp(wtf_inches + BODY_LENGTH_IN.get(body, 0.0), LENGTH_CLAMP_IN)
    lie = _clamp(wtf_inches + BODY_LIE_DEG.get(body, 0.0), LIE_CLAMP_DEG)
    delta_in = _round_quarter(delta_in)
    lie = _round_half(lie)
    return delta_in, lie, lie_label(lie)


def lie_label(lie_delta_deg: float) -> str:
    if lie_delta_deg <= -1.5:
        return "flat"
    if lie_delta_deg <= -0.5:
        return "slightly flat"
    if lie_delta_deg < 0.5:
        return "standard"
    if lie_delta_deg < 1.5:
        return "slightly upright"
    return "upright"


def _age_delta(age: int) -> float:
    """Rule SS-2."""
    if age < 18:
        return AGE_UNDER_18_DELTA
    if age <= AGE_PEAK_END:
        return 0.0
    return -AGE_DECLINE_PER_YEAR * (age - AGE_PEAK_END)


def _strength_delta(profile: GolferProfile) -> float:
    """Rule SS-3. Missing lifts contribute nothing — they are not zeros."""
    parts: list[float] = []
    if profile.squat_kg and profile.weight_kg:
        ratio = profile.squat_kg / profile.weight_kg
        expected = EXPECTED_SQUAT_RATIO[profile.gender]
        parts.append((ratio - expected) * SQUAT_MPH_PER_RATIO)
    if profile.bench_press_kg and profile.weight_kg:
        ratio = profile.bench_press_kg / profile.weight_kg
        expected = EXPECTED_BENCH_RATIO[profile.gender]
        parts.append((ratio - expected) * BENCH_MPH_PER_RATIO)
    if not parts:
        return 0.0
    return _clamp(sum(parts), STRENGTH_CLAMP)


def _cardio_delta(profile: GolferProfile) -> float:
    """Rule SS-4. Average of the proxies that were actually supplied."""
    signals: list[float] = []
    if profile.fitness_level:
        level = min(5, max(1, int(profile.fitness_level)))
        signals.append(FITNESS_MPH[level])
    if profile.vo2_max:
        signals.append(_clamp((profile.vo2_max - VO2_CENTER) * VO2_MPH_PER_ML, VO2_CLAMP))
    if profile.resting_hr:
        signals.append(_clamp((RHR_CENTER - profile.resting_hr) * RHR_MPH_PER_BPM, RHR_CLAMP))
    if not signals:
        return 0.0
    return sum(signals) / len(signals)


def _bmi_delta(profile: GolferProfile, strength: float) -> float:
    """Rule SS-5."""
    if not profile.weight_kg or not profile.height_cm:
        return 0.0
    metres = profile.height_cm / 100.0
    bmi = profile.weight_kg / (metres * metres)
    if bmi >= BMI_VERY_HIGH:
        adj = -2.5
    elif bmi >= BMI_HIGH:
        adj = -1.0
    elif bmi < BMI_LOW:
        adj = -1.0
    else:
        adj = 0.0
    if strength > 6 and adj < 0 and bmi >= BMI_HIGH:
        adj *= 0.5
    return adj


def _handicap_implied_ss(profile: GolferProfile) -> float:
    """Rule SS-6 implied speed from handicap index."""
    handicap = profile.handicap if profile.handicap is not None else 18.0
    if profile.gender == "female":
        return _clamp(90.0 - handicap * 0.95, (52.0, 100.0))
    return _clamp(112.0 - handicap * 1.15, (65.0, 120.0))


@dataclass
class SpeedEstimate:
    mph: float
    source: str  # measured | blended | estimated
    metric_mph: float
    strength_mph: float
    cardio_mph: float
    age_mph: float
    bmi_mph: float
    handicap_implied_mph: float | None
    notes: list[str] = field(default_factory=list)


def estimate_swing_speed(profile: GolferProfile) -> SpeedEstimate:
    """Rules SS-0 through SS-6. Returns the speed used for flex and loft."""
    base = BASE_DRIVER_SS[profile.gender]
    age = _age_delta(profile.age)
    strength = _strength_delta(profile)
    cardio = _cardio_delta(profile)
    bmi = _bmi_delta(profile, strength)
    metric = _clamp(base + age + strength + cardio + bmi, SS_CLAMP)
    notes: list[str] = []
    implied = (
        _handicap_implied_ss(profile) if profile.handicap is not None else None
    )

    if profile.swing_speed_mph:
        # SS-0. Still report the metric estimate so a fitter can see the gap.
        mph = _clamp(profile.swing_speed_mph, SS_CLAMP)
        source = "measured"
        notes.append(
            f"Using the measured driver speed of {mph:.0f} mph instead of the "
            f"{metric:.0f} mph estimate."
        )
    elif implied is not None:
        # SS-6.
        fitness_known = strength != 0 or cardio != 0
        weight = (
            HANDICAP_WEIGHT_WITH_FITNESS
            if fitness_known
            else HANDICAP_WEIGHT_DEMOGRAPHICS_ONLY
        )
        mph = _clamp((1 - weight) * metric + weight * implied, SS_CLAMP)
        source = "blended"
        notes.append(
            f"Handicap {profile.handicap:g} implies about {implied:.0f} mph, "
            f"blended at {weight:.0%} with the age/strength estimate of {metric:.0f} mph."
        )
    else:
        mph = metric
        source = "estimated"
        if strength == 0 and cardio == 0:
            notes.append(
                "No strength or cardio data, so speed is age and gender only "
                "(plus BMI if weight was given)."
            )

    return SpeedEstimate(
        mph=round(mph, 1),
        source=source,
        metric_mph=round(metric, 1),
        strength_mph=round(strength, 1),
        cardio_mph=round(cardio, 1),
        age_mph=round(age, 1),
        bmi_mph=round(bmi, 1),
        handicap_implied_mph=round(implied, 1) if implied is not None else None,
        notes=notes,
    )


def flex_for_speed(mph: float) -> str:
    """Rule FLEX-1."""
    for name, upper in FLEX_UPPER:
        if mph < upper:
            return name
    return "X"


def shift_flex(flex: str, steps: int) -> str:
    index = FLEX_ORDER.index(flex) + steps
    index = max(0, min(len(FLEX_ORDER) - 1, index))
    return FLEX_ORDER[index]


def estimate_grip(profile: GolferProfile) -> str:
    """Rule GRIP-1."""
    if profile.hand_size_cm:
        for name, upper in HAND_CM_BOUNDS:
            if profile.hand_size_cm < upper:
                return name
        return "jumbo"
    if profile.gender == "female":
        return "undersize" if profile.height_cm < 155 else "standard"
    if profile.gender == "male" and profile.height_cm >= 196:
        return "midsize"
    if profile.height_cm < 160:
        return "undersize"
    return "standard"


def shift_grip(grip: str, steps: int) -> str:
    index = GRIP_ORDER.index(grip) + steps
    index = max(0, min(len(GRIP_ORDER) - 1, index))
    return GRIP_ORDER[index]


def estimate_category(profile: GolferProfile, swing_speed: float) -> str:
    """Rule HC-1. Medical softening of category happens later, in MED-1."""
    if profile.handicap is not None:
        hcp = profile.handicap
        if hcp <= 5:
            return "players"
        if hcp <= 14:
            return "players_distance"
        if hcp <= 24:
            return "game_improvement"
        return "super_game_improvement"
    if swing_speed >= 102 and profile.age < 50:
        return "players_distance"
    if swing_speed < 82 or profile.age >= 68:
        return "super_game_improvement"
    return "game_improvement"


def shift_category(category: str, steps: int) -> str:
    if category not in CATEGORY_ORDER:
        return category
    index = CATEGORY_ORDER.index(category) + steps
    index = max(0, min(len(CATEGORY_ORDER) - 1, index))
    return CATEGORY_ORDER[index]


@dataclass
class MedicalResult:
    flex: str
    grip: str
    category: str
    loft_delta: float
    weight_delta_g: float
    avoid_heavy: bool
    applied: bool
    notes: list[str] = field(default_factory=list)


def apply_medical(
    flex: str,
    grip: str,
    category: str,
    flags: list[str],
) -> MedicalResult:
    """Rule MED-1. Call this after flex, grip, category and base loft exist.

    ``loft_delta`` is added to driver loft by the engine after the set bias,
    so a control bag's −1° does not erase a shoulder accommodation and a
    distance bag's +1.5° does not double it.
    """
    notes: list[str] = []
    flex_steps = 0
    grip_steps = 0
    weight = 0.0
    loft = 0.0
    avoid_heavy = False
    drop_players_heads = False

    has_trunk = "shoulder" in flags or "back" in flags
    if has_trunk:
        flex_steps -= 1
        weight -= 8
        loft += MEDICAL_LOFT_DELTA
        avoid_heavy = True
        which = " and ".join(n for n in ("shoulder", "back") if n in flags)
        notes.append(
            f"A {which} flag softens flex one step, drops about 8 g of shaft "
            "weight, adds 1° of driver loft, and avoids the heaviest heads."
        )
    if "elbow" in flags:
        weight -= 4
        notes.append("Elbow irritation trims about 4 g of shaft weight.")
    if "wrist" in flags:
        grip_steps += 1
        notes.append("A wrist flag steps the grip up one size.")
    if "arthritis" in flags:
        grip_steps += 1
        weight -= 5
        notes.append(
            "Arthritis steps the grip up one size and trims about 5 g so the "
            "club is easier to hold and to stop."
        )
    if "low_bone_density" in flags:
        flex_steps -= 1
        weight -= 10
        avoid_heavy = True
        drop_players_heads = True
        notes.append(
            "Low bone density softens flex one step, trims about 10 g, and "
            "keeps the bag in a game-improvement head rather than a players head."
        )

    new_flex = shift_flex(flex, flex_steps)
    # Wrist discomfort specifically does not stay in X, even if other flags
    # did not already soften it.
    if "wrist" in flags and new_flex == "X":
        new_flex = shift_flex(new_flex, -1)
        notes.append("X-flex is stepped down because of the wrist flag.")

    if drop_players_heads and category in {"players", "players_distance"}:
        category = "game_improvement"

    weight = max(MEDICAL_WEIGHT_CAP, weight)
    loft = min(MEDICAL_LOFT_CAP, loft)

    return MedicalResult(
        flex=new_flex,
        grip=shift_grip(grip, grip_steps),
        category=category,
        loft_delta=loft,
        weight_delta_g=weight,
        avoid_heavy=avoid_heavy,
        applied=bool(flags),
        notes=notes,
    )


def base_driver_loft(swing_speed: float) -> float:
    """Rule LOFT-1 wrapper so callers do not import the rulebook directly."""
    return starting_driver_loft(swing_speed)
