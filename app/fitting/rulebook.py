"""Published fitting constants and the plain-language rulebook.

A fitter auditing a recommendation should be able to open this file and
reproduce every number. The engine records the rule ids it actually applied.

Thresholds live here — do not re-hardcode them in the engine.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# SS-0 / SS-1 swing-speed model
# Population anchors are amateur driver speeds, not tour speeds.
# Male ~95 mph and female ~76 mph at age 30 with average strength is the
# "regular / senior-amateur" center of this chart, not a single-digit handicap.
# ---------------------------------------------------------------------------

BASE_DRIVER_SS = {
    "male": 95.0,
    "female": 76.0,
    "unspecified": 85.0,
}

# Expected gym ratios (1RM / body weight) for an average adult golfer.
# These are not strength-sport standards; they are the zero-point of SS-3.
EXPECTED_SQUAT_RATIO = {"male": 1.15, "female": 0.90, "unspecified": 1.00}
EXPECTED_BENCH_RATIO = {"male": 0.80, "female": 0.45, "unspecified": 0.60}

# SS-3 coefficients: mph added per 1.0 of ratio above the expected ratio.
SQUAT_MPH_PER_RATIO = 12.0  # +0.25 squat/BW ≈ +3 mph
BENCH_MPH_PER_RATIO = 6.0  # smaller; bench is a weak proxy for clubhead speed
STRENGTH_CLAMP = (-12.0, 14.0)

# SS-2: flat peak from 18–35, then 0.35 mph lost per year. Under 18: −4 mph.
AGE_PEAK_END = 35
AGE_DECLINE_PER_YEAR = 0.35
AGE_UNDER_18_DELTA = -4.0

# SS-4 cardio. Fitness is a 1–5 self report. VO2 and resting HR are optional
# lab/wearable proxies. When several are present they are averaged, not stacked.
FITNESS_MPH = {1: -4.0, 2: -2.0, 3: 0.0, 4: 2.0, 5: 3.5}
VO2_CENTER = 38.0
VO2_MPH_PER_ML = 0.18
VO2_CLAMP = (-4.0, 4.0)
RHR_CENTER = 65.0
RHR_MPH_PER_BPM = 0.12
RHR_CLAMP = (-3.0, 3.0)

# SS-5 body mass. A high BMI trims speed unless strength already explains it.
BMI_HIGH = 30.0
BMI_VERY_HIGH = 33.0
BMI_LOW = 19.0

# SS-6 handicap blend weights (handicap share of the final speed).
# More trust in the handicap when we have no strength and no cardio.
HANDICAP_WEIGHT_WITH_FITNESS = 0.45
HANDICAP_WEIGHT_DEMOGRAPHICS_ONLY = 0.60

SS_CLAMP = (50.0, 130.0)

# FLEX-1 driver-speed bands (mph). Inclusive lower bound, exclusive upper.
#   L  < 75
#   A  75–84.9
#   R  85–95.9
#   S  96–104.9
#   X  ≥ 105
FLEX_UPPER = (("L", 75.0), ("A", 85.0), ("R", 96.0), ("S", 105.0), ("X", 10_000.0))
FLEX_ORDER = ["L", "A", "R", "S", "X"]

# ---------------------------------------------------------------------------
# WTF-EST / LL length and lie
# Reference player wears standard length and standard lie.
# Men's wrist-to-floor anchor: 87 cm (34.25 in) at 178 cm tall.
# Women's anchor: 81 cm at 165 cm. Adjustments are vs that gender's standard,
# not vs a unisex men's 7-iron.
# ---------------------------------------------------------------------------

LENGTH_REFERENCE = {
    "male": {"height_cm": 178.0, "wtf_cm": 87.0},
    "female": {"height_cm": 165.0, "wtf_cm": 81.0},
    "unspecified": {"height_cm": 172.0, "wtf_cm": 84.0},
}

# WTF-EST body-type tweak applied ONLY when wrist-to-floor was not measured.
# Ectomorphs tend to have longer limbs (wrists hang lower). Heavier builds
# tend to have a slightly higher wrist relative to stature.
WTF_EST_BODY_CM = {
    "ectomorph": -1.5,
    "mesomorph": 0.0,
    "athletic": 0.0,
    "average": 0.0,
    "endomorph": 1.2,
    "heavy": 1.2,
}

CM_PER_INCH = 2.54
# LL-1: 1 inch of length per 1 inch of WTF away from the reference.
LENGTH_CLAMP_IN = (-2.0, 2.0)
# LL-3: 1° of lie per 1 inch of WTF. Positive = upright, negative = flat.
LIE_CLAMP_DEG = (-4.0, 4.0)

# LL-4 modest posture nudge on top of the WTF result, measured or estimated.
BODY_LENGTH_IN = {
    "ectomorph": 0.0,
    "mesomorph": 0.0,
    "athletic": 0.0,
    "average": 0.0,
    "endomorph": 0.25,
    "heavy": 0.25,
}
BODY_LIE_DEG = {
    "ectomorph": -0.5,
    "mesomorph": 0.0,
    "athletic": 0.0,
    "average": 0.0,
    "endomorph": 0.5,
    "heavy": 0.5,
}

# ---------------------------------------------------------------------------
# GRIP-1
# Hand length is wrist crease to tip of the middle finger, in centimetres.
# ---------------------------------------------------------------------------

GRIP_ORDER = ["undersize", "standard", "midsize", "jumbo"]
# Upper bounds: hand < bound → that size. Last size is the fallback.
HAND_CM_BOUNDS = (
    ("undersize", 16.8),
    ("standard", 21.6),
    ("midsize", 23.2),
    ("jumbo", 10_000.0),
)

# ---------------------------------------------------------------------------
# HC-1 head category. players_distance sits between GI and players.
# ---------------------------------------------------------------------------

CATEGORY_ORDER = [
    "super_game_improvement",
    "game_improvement",
    "players_distance",
    "players",
]

# LOFT-1 starting driver loft from speed, before set bias and before medical.
def starting_driver_loft(swing_speed: float) -> float:
    """Rule LOFT-1. Higher speed → less loft. This is a static start, not a fit."""
    if swing_speed >= 108:
        return 9.0
    if swing_speed >= 100:
        return 9.5
    if swing_speed >= 92:
        return 10.5
    if swing_speed >= 84:
        return 12.0
    if swing_speed >= 75:
        return 13.0
    return 14.0


# Set-level loft bias applied BEFORE medical (MED-1 is always last).
SET_LOFT_BIAS = {"distance": 1.5, "control": -1.0, "preference": 0.0}
SET_CATEGORY_SHIFT = {"distance": -1, "control": 1, "preference": 0}
SET_SHAFT_PROFILE = {
    "distance": "distance",
    "control": "control",
    "preference": "neutral",
}
SET_LAUNCH = {"distance": "high", "control": "low", "preference": "mid"}

# MED-1. Shoulder/back share one loft step so the two flags do not stack loft.
MEDICAL_LOFT_DELTA = 1.0
MEDICAL_LOFT_CAP = 2.0
MEDICAL_WEIGHT_CAP = -20.0  # grams, most negative allowed

# Shaft weight targets (grams) at each flex, before profile bias and medical.
# Profile bias: distance −6 g, control +6 g. Medical weight delta stacks after.
BASE_SHAFT_WEIGHT = {
    "driver": {"L": 42, "A": 48, "R": 55, "S": 65, "X": 70},
    "fairway": {"L": 50, "A": 55, "R": 62, "S": 70, "X": 75},
    "hybrid": {"L": 55, "A": 60, "R": 68, "S": 75, "X": 80},
    "utility_iron": {"L": 60, "A": 65, "R": 72, "S": 80, "X": 85},
    "iron": {"L": 70, "A": 82, "R": 100, "S": 112, "X": 122},
    "wedge": {"L": 90, "A": 100, "R": 112, "S": 122, "X": 128},
    "putter": {"L": 115, "A": 115, "R": 115, "S": 115, "X": 115},
}
PROFILE_WEIGHT_BIAS = {"distance": -6.0, "control": 6.0, "neutral": 0.0}

# Gender standard lengths, inches, BEFORE length_delta.
# Iron figure is the 7-iron. Putter receives half the iron delta (PUTT-1).
STANDARD_LENGTH_IN = {
    "male": {
        "driver": 45.75,
        "fairway": 43.25,
        "hybrid": 40.50,
        "utility_iron": 39.50,
        "iron": 37.00,
        "wedge": 35.50,
        "putter": 34.00,
    },
    "female": {
        "driver": 44.50,
        "fairway": 42.00,
        "hybrid": 39.25,
        "utility_iron": 38.50,
        "iron": 36.25,
        "wedge": 34.75,
        "putter": 33.00,
    },
    "unspecified": {
        "driver": 45.25,
        "fairway": 42.75,
        "hybrid": 40.00,
        "utility_iron": 39.00,
        "iron": 36.75,
        "wedge": 35.25,
        "putter": 33.50,
    },
}

BRAND_ORDER = [
    "Titleist",
    "TaylorMade",
    "Callaway",
    "Ping",
    "Mizuno",
    "Cobra",
    "Srixon",
    "Wilson",
    "PXG",
]

DISCLAIMER = (
    "Static starting point only. Confirm length and lie on a lie board, "
    "and confirm loft, spin and shaft on a launch monitor before anyone buys a set. "
    "This is not a medical clearance to play."
)


RULES: dict[str, str] = {
    "SS-0": (
        "A measured driver swing speed, when the golfer supplies one, replaces "
        "the estimate. Medical rules can still soften flex afterwards; they do "
        "not rewrite the measured speed."
    ),
    "SS-1": (
        "Driver swing speed starts at a gender anchor at age 30 with average "
        "strength (male 95 mph, female 76, unspecified 85). Age, strength, "
        "cardio and BMI then move that anchor. Missing inputs are skipped, "
        "not punished."
    ),
    "SS-2": (
        "Speed is treated as flat from 18 through 35. After 35 it declines "
        "0.35 mph per year. Under 18, subtract 4 mph from the age-30 anchor."
    ),
    "SS-3": (
        "Strength uses squat and bench relative to body weight. Each 1.0 of "
        "squat/BW above the gender expectation is +12 mph; each 1.0 of "
        "bench/BW is +6 mph. A missing lift is ignored. The pair is clamped "
        "to between −12 and +14 mph so one gym number cannot dominate the fit."
    ),
    "SS-4": (
        "Cardio is an average of whichever proxies exist: fitness 1–5 "
        "(−4 to +3.5 mph), VO2 max centred on 38 ml/kg/min, and resting heart "
        "rate centred on 65 bpm. Proxies are averaged so they do not stack."
    ),
    "SS-5": (
        "BMI under 19 or at least 30 trims estimated speed slightly. At BMI 33 "
        "or above the trim is 2.5 mph. If strength already added more than "
        "6 mph, a high-BMI penalty is halved — a strong heavier golfer still "
        "creates speed."
    ),
    "SS-6": (
        "When a handicap is present and speed was not measured, blend the "
        "metric estimate with a handicap-implied speed (male: 112 − 1.15×HCP; "
        "female: 90 − 0.95×HCP). Handicap counts for 60% if strength and cardio "
        "are both missing, otherwise 45%."
    ),
    "FLEX-1": (
        "Map driver mph to flex: L below 75, A 75–84.9, R 85–95.9, "
        "S 96–104.9, X at 105 and above. The same flex family is preferred "
        "on every full-swing club. A putter shaft is stock and is not a flex break."
    ),
    "WTF-EST": (
        "If wrist-to-floor was not measured, estimate it as height × (reference "
        "WTF / reference height) for that gender, then apply a small body-type "
        "limb adjustment (−1.5 cm ectomorph, +1.2 cm endomorph/heavy). A measured "
        "WTF is never rewritten by this estimate."
    ),
    "LL-1": (
        "Length comes first from wrist-to-floor versus the gender reference "
        "(men 87 cm, women 81 cm, unspecified 84 cm). One inch of WTF is one "
        "inch of length. Clamp to ±2 inches and round to ¼ inch. The adjustment "
        "is versus that gender's standard club, not versus a men's unisex standard."
    ),
    "LL-2": (
        "When both height and a measured WTF exist they can disagree (a tall "
        "player with long arms). WTF wins. Height is not averaged back in."
    ),
    "LL-3": (
        "Lie is one degree per inch of WTF away from the same reference. "
        "Higher WTF (shorter arms relative to stature, wrists higher at address) "
        "is more upright. Lower WTF is flatter. Clamp to ±4° and round to 0.5°."
    ),
    "LL-4": (
        "Body type is a modest nudge after WTF: endomorph/heavy +0.25 inch and "
        "+0.5° upright (posture and clearance); ectomorph −0.5° (slightly flatter); "
        "athletic, mesomorph and average add nothing. Lie is rounded to 0.5°."
    ),
    "GRIP-1": (
        "Grip size prefers measured hand length: under 16.8 cm undersize, "
        "under 21.6 cm standard, under 23.2 cm midsize, otherwise jumbo. "
        "Without a hand measurement, very short players go undersize, men "
        "196 cm or taller go midsize, and everyone else is standard."
    ),
    "HC-1": (
        "Head category from handicap when we have one: ≤5 players, ≤14 players "
        "distance, ≤24 game improvement, otherwise super game improvement. "
        "With no handicap: 102+ mph and under 50 is players distance; under "
        "82 mph or 68+ years is super game improvement; otherwise game improvement."
    ),
    "LOFT-1": (
        "Starting driver loft is 9° at 108+ mph, 9.5° at 100+, 10.5° at 92+, "
        "12° at 84+, 13° at 75+, else 14°, then snapped to a real loft in the "
        "chosen head."
    ),
    "SET-1": (
        "Three bags, on purpose. Distance: +1.5° driver loft, lighter high-launch "
        "shafts, one category step more forgiving. Control: −1.0° loft, heavier "
        "low-launch shafts, one step toward a players head. Preference: baseline "
        "spec in the preferred brand (or current brand, or Titleist if neither "
        "was stated). Length, lie, grip and flex family stay the same across bags."
    ),
    "BRAND-1": (
        "Stated preferred brand wins over the current bag. The other two "
        "orientations take the other two houses so the sheet is actually "
        "diverse. Names are matched loosely (taylor → TaylorMade)."
    ),
    "MED-1": (
        "Medical modifiers run last. Shoulder or back: one flex softer, about "
        "8 g less shaft weight, +1° driver loft, avoid heavy heads. Elbow: "
        "−4 g. Wrist: one grip size up, and leave X-flex if still there. "
        "Arthritis: one grip size up and −5 g. Low bone density: −10 g, one "
        "flex softer, and do not recommend a players or players-distance head. "
        "Flex cannot go below L. Grip cannot go past jumbo. Weight relief is "
        "capped at −20 g. Loft added for shoulder/back does not stack past +1° "
        "for those two flags together."
    ),
    "BAG-1": (
        "Every bag has a driver, one fairway (3-wood if the distance bag or "
        "the speed supports it, otherwise 5-wood), a hybrid or a utility iron, "
        "an iron set, gap/sand/lob wedges, and a putter. Hybrids replace long "
        "irons for distance bags, game-improvement categories, speeds under "
        "98 mph, or any back/shoulder/bone-density flag."
    ),
    "PUTT-1": (
        "Putter length receives half the iron length adjustment. Putter lie is "
        "not copied from the irons — confirm it separately. Mallet style for "
        "super game improvement, handicap over 20, or arthritis; otherwise a blade."
    ),
    "SHAFT-1": (
        "Within the chosen brand and flex family, pick the shaft whose job "
        "matches the bag (distance, control, or neutral) and whose weight is "
        "closest to the flex target plus the medical weight change. An exact "
        "flex match outranks a prettier profile in the wrong flex. Say so when "
        "a club has to leave the family."
    ),
}
