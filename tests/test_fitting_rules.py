"""Golden checks for the published speed, length, lie, flex and medical rules."""

from app.fitting.profile import GolferProfile
from app.fitting.specs import (
    apply_medical,
    estimate_category,
    estimate_grip,
    estimate_swing_speed,
    estimate_wrist_to_floor,
    flex_for_speed,
    length_and_lie,
)


def _male(**kwargs) -> GolferProfile:
    base = dict(age=30, height_cm=178, weight_kg=80, gender="male")
    base.update(kwargs)
    return GolferProfile(**base).normalized()


def test_average_male_is_regular_and_standard_length():
    profile = _male()
    speed = estimate_swing_speed(profile)
    assert speed.mph == 95.0
    assert speed.source == "estimated"
    assert flex_for_speed(speed.mph) == "R"
    wtf, estimated = estimate_wrist_to_floor(profile)
    assert estimated is True
    assert wtf == 87.0
    length, lie, label = length_and_lie(profile, wtf)
    assert length == 0
    assert lie == 0
    assert label == "standard"
    assert estimate_grip(profile) == "standard"
    assert estimate_category(profile, speed.mph) == "game_improvement"


def test_average_female_is_a_flex():
    profile = GolferProfile(age=30, height_cm=165, gender="female", weight_kg=65).normalized()
    speed = estimate_swing_speed(profile)
    assert speed.mph == 76.0
    assert flex_for_speed(speed.mph) == "A"
    wtf, estimated = estimate_wrist_to_floor(profile)
    assert estimated and wtf == 81.0
    length, lie, _label = length_and_lie(profile, wtf)
    assert length == 0 and lie == 0


def test_strong_young_player_reaches_x():
    profile = _male(age=22, height_cm=183, weight_kg=82, squat_kg=180, bench_press_kg=120)
    speed = estimate_swing_speed(profile)
    assert speed.mph >= 105
    assert flex_for_speed(speed.mph) == "X"
    assert speed.strength_mph == 14.0  # clamped


def test_senior_without_strength_data_softens_and_does_not_crash():
    profile = _male(age=74, height_cm=175, weight_kg=78)
    speed = estimate_swing_speed(profile)
    assert speed.source == "estimated"
    assert any("age and gender" in note for note in speed.notes)
    assert flex_for_speed(speed.mph) == "A"
    assert 75 <= speed.mph < 85
    assert estimate_category(profile, speed.mph) == "super_game_improvement"


def test_very_tall_measured_wtf_clamps_length_and_lie():
    profile = _male(age=28, height_cm=208, wrist_to_floor_cm=102)
    wtf, estimated = estimate_wrist_to_floor(profile)
    assert estimated is False and wtf == 102
    length, lie, label = length_and_lie(profile, wtf)
    assert length == 2.0
    assert lie == 4.0
    assert label == "upright"


def test_very_short_woman_clamps_short_and_flat():
    profile = GolferProfile(age=68, height_cm=147, gender="female", wrist_to_floor_cm=70).normalized()
    length, lie, label = length_and_lie(profile, 70)
    assert length == -2.0
    assert lie == -4.0
    assert label == "flat"
    speed = estimate_swing_speed(profile)
    assert flex_for_speed(speed.mph) == "L"


def test_endomorph_nudge_is_modest():
    profile = _male(body_type="endomorph", wrist_to_floor_cm=87)
    length, lie, label = length_and_lie(profile, 87)
    assert length == 0.25
    assert lie == 0.5
    assert label == "slightly upright"


def test_measured_speed_overrides_estimate():
    profile = _male(age=74, swing_speed_mph=102)
    speed = estimate_swing_speed(profile)
    assert speed.source == "measured"
    assert speed.mph == 102
    assert flex_for_speed(speed.mph) == "S"


def test_handicap_blend_when_no_gym_data():
    profile = _male(handicap=10)
    speed = estimate_swing_speed(profile)
    assert speed.source == "blended"
    # 60% of (112 - 11.5 = 100.5) and 40% of 95 → 98.3
    assert speed.mph == 98.3
    assert flex_for_speed(speed.mph) == "S"


def test_medical_runs_last_and_will_not_leave_an_x_with_a_back_flag():
    result = apply_medical("X", "standard", "players", ["back", "arthritis"])
    assert result.applied
    assert result.flex == "S"
    assert result.grip == "midsize"
    assert result.loft_delta == 1.0
    assert result.weight_delta_g == -13
    assert result.category == "players"  # bone density, not back, moves the head
    bone = apply_medical("X", "midsize", "players", ["low_bone_density", "wrist"])
    # Bone density already left X, so the wrist rule does not soften a second step.
    assert bone.flex == "S"
    assert bone.category == "game_improvement"
    assert bone.grip == "jumbo"
    wrist_only = apply_medical("X", "standard", "players", ["wrist"])
    assert wrist_only.flex == "S"


def test_missing_optional_fields_do_not_invent_strength():
    profile = GolferProfile(age=40, height_cm=170, gender="unspecified").normalized()
    speed = estimate_swing_speed(profile)
    assert speed.strength_mph == 0
    assert speed.cardio_mph == 0
    assert speed.source == "estimated"
