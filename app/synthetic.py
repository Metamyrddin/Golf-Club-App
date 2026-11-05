"""Synthetic labelled golfers.

The generator does not invent a second fitting opinion. It draws a realistic
profile, then labels it with :func:`app.fitting.engine.recommend` so the
labels cannot drift from the rules. Target size is 8,000–15,000 rows.
"""

from __future__ import annotations

import random

from app.fitting.engine import recommend
from app.fitting.profile import GolferProfile

MEDICAL_POOL = ["shoulder", "back", "wrist", "elbow", "arthritis", "low_bone_density"]
BODY_TYPES = ["ectomorph", "mesomorph", "endomorph", "athletic", "average", "heavy"]
BRANDS = ["Titleist", "TaylorMade", "Callaway"]


def _clipped_gauss(rng: random.Random, mu: float, sigma: float, low: float, high: float) -> float:
    value = rng.gauss(mu, sigma)
    return max(low, min(high, value))


def sample_profile(rng: random.Random) -> GolferProfile:
    """Draw one golfer. Optional fields are missing at realistic rates."""
    roll = rng.random()
    if roll < 0.68:
        gender = "male"
    elif roll < 0.97:
        gender = "female"
    else:
        gender = "unspecified"

    if gender == "female":
        age = int(_clipped_gauss(rng, 44, 14, 14, 90))
        height = _clipped_gauss(rng, 165, 6.5, 142, 190)
        weight = _clipped_gauss(rng, 68, 12, 45, 120)
    elif gender == "male":
        age = int(_clipped_gauss(rng, 46, 14, 14, 90))
        height = _clipped_gauss(rng, 178, 7.0, 155, 210)
        weight = _clipped_gauss(rng, 86, 13, 55, 145)
    else:
        age = int(_clipped_gauss(rng, 45, 14, 16, 85))
        height = _clipped_gauss(rng, 172, 8, 150, 200)
        weight = _clipped_gauss(rng, 78, 14, 50, 130)

    body = rng.choice(BODY_TYPES)
    # Heavier body types carry a bit more weight. Keeps the joint distribution honest.
    if body in {"endomorph", "heavy"}:
        weight = min(weight * rng.uniform(1.05, 1.18), 150)
    if body == "ectomorph":
        weight = max(weight * rng.uniform(0.84, 0.95), 45)

    profile = GolferProfile(
        age=age,
        height_cm=round(height, 1),
        gender=gender,
        weight_kg=round(weight, 1),
        body_type=body,
    )

    # 72% have a measured wrist-to-floor near the population line, with noise.
    if rng.random() < 0.72:
        ratio = {"male": 87 / 178, "female": 81 / 165, "unspecified": 84 / 172}[gender]
        noise = rng.gauss(0, 2.4)
        if body == "ectomorph":
            noise -= 1.2
        if body in {"endomorph", "heavy"}:
            noise += 1.0
        profile.wrist_to_floor_cm = round(max(55, min(115, height * ratio + noise)), 1)

    if rng.random() < 0.45:
        # Hand length roughly tracks height. Men ~19 cm at 178 cm.
        profile.hand_size_cm = round(_clipped_gauss(rng, height * 0.108, 0.8, 14, 25), 1)

    # Strength is missing more often in older golfers.
    strength_rate = 0.55 if age < 55 else 0.28
    if rng.random() < strength_rate:
        if gender == "female":
            squat_ratio = _clipped_gauss(rng, 0.95, 0.28, 0.4, 1.8)
            bench_ratio = _clipped_gauss(rng, 0.48, 0.15, 0.2, 1.1)
        else:
            squat_ratio = _clipped_gauss(rng, 1.2, 0.35, 0.45, 2.4)
            bench_ratio = _clipped_gauss(rng, 0.85, 0.25, 0.3, 1.8)
        profile.squat_kg = round(weight * squat_ratio, 1)
        if rng.random() < 0.85:
            profile.bench_press_kg = round(weight * bench_ratio, 1)

    if rng.random() < 0.5:
        profile.fitness_level = rng.choices([1, 2, 3, 4, 5], weights=[8, 18, 40, 24, 10])[0]
    if rng.random() < 0.22:
        profile.vo2_max = round(_clipped_gauss(rng, 38 if gender != "female" else 34, 6, 20, 65), 1)
    if rng.random() < 0.3:
        profile.resting_hr = int(_clipped_gauss(rng, 68, 8, 42, 100))

    if rng.random() < 0.62:
        # Amateur handicap, mode around 16, a few plus-golfers and a few high ones.
        profile.handicap = round(_clipped_gauss(rng, 16, 8, -2, 45), 1)

    # A measured speed is uncommon; most golfers only have a handicap or nothing.
    if rng.random() < 0.12:
        center = 95 if gender == "male" else 75
        profile.swing_speed_mph = round(_clipped_gauss(rng, center, 8, 55, 125), 1)

    if rng.random() < 0.48:
        profile.current_brand = rng.choice(BRANDS)
    if rng.random() < 0.55:
        profile.preferred_brands = rng.sample(BRANDS, k=1 if rng.random() < 0.75 else 2)

    if rng.random() < 0.22:
        k = 1 if rng.random() < 0.7 else 2
        profile.medical_flags = rng.sample(MEDICAL_POOL, k=k)
        if rng.random() < 0.4:
            profile.medical_notes = "Occasional stiffness. Cleared by their own physician to play."

    return profile


def label_profile(profile: GolferProfile) -> dict:
    """Compact label stored next to the profile. The full bags are reproducible."""
    result = recommend(profile)
    target = result["target"]
    return {
        "flex": target["flex"],
        "flex_before_medical": target["flex_before_medical"],
        "length_delta_in": target["length_delta_in"],
        "lie_delta_deg": target["lie_delta_deg"],
        "lie_label": target["lie_label"],
        "grip": target["grip"],
        "head_category": target["head_category"],
        "swing_speed_mph": target["swing_speed_mph"],
        "swing_speed_source": target["swing_speed_source"],
        "sets": [
            {
                "id": bag["id"],
                "brand": bag["brand"],
                "driver": next(c["head"]["model"] for c in bag["clubs"] if c["slot"] == "driver"),
                "driver_loft": next(c["loft"] for c in bag["clubs"] if c["slot"] == "driver"),
                "flex_consistent": bag["flex_consistent"],
            }
            for bag in result["sets"]
        ],
    }


def generate(n: int, seed: int = 42) -> list[dict]:
    rng = random.Random(seed)
    rows = []
    for index in range(n):
        profile = sample_profile(rng)
        rows.append(
            {
                "id": f"syn-{seed}-{index:05d}",
                "profile": profile.to_dict(),
                "label": label_profile(profile),
            }
        )
    return rows
