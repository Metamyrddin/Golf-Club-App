"""Bag shape, diversity, and the edge cases a fitter will actually see."""

from app.fitting.engine import recommend
from app.fitting.profile import GolferProfile

REQUIRED_SLOTS = {"driver", "fairway", "long_club", "irons", "wedge", "putter"}


def _bags(profile: GolferProfile) -> dict:
    return recommend(profile.normalized())


def _assert_full_bag(result: dict) -> None:
    assert len(result["sets"]) == 3
    ids = [bag["id"] for bag in result["sets"]]
    assert ids == ["distance", "control", "preference"]
    brands = [bag["brand"] for bag in result["sets"]]
    assert len(set(brands)) == 3
    for bag in result["sets"]:
        slots = {club["slot"] for club in bag["clubs"]}
        assert REQUIRED_SLOTS <= slots
        wedges = [club for club in bag["clubs"] if club["slot"] == "wedge"]
        assert 2 <= len(wedges) <= 3
        assert bag["rationale"]
        assert len(bag["rationale"]) > 80
        for club in bag["clubs"]:
            assert club["head"]["model"]
            assert club["shaft"]["model"]
            if club["slot"] != "putter":
                assert club["lie_label"] == result["target"]["lie_label"]
        # Flex family is the target flex except where the note says otherwise.
        if bag["flex_consistent"]:
            for club in bag["clubs"]:
                if club["slot"] != "putter":
                    assert club["flex"] == result["target"]["flex"]


def test_three_diverse_bags_for_a_plain_profile():
    result = _bags(GolferProfile(age=46, height_cm=180, weight_kg=86, gender="male", handicap=14))
    _assert_full_bag(result)
    assert result["target"]["flex"] in {"R", "S", "A"}
    drivers = [next(c for c in bag["clubs"] if c["slot"] == "driver") for bag in result["sets"]]
    lofts = [club["loft"] for club in drivers]
    assert lofts[0] >= lofts[2]  # distance loft at least the neutral bag


def test_brand_preference_beats_current_set():
    result = _bags(
        GolferProfile(
            age=40,
            height_cm=178,
            gender="male",
            preferred_brands=["Titleist"],
            current_brand="Callaway",
        )
    )
    _assert_full_bag(result)
    by_id = {bag["id"]: bag for bag in result["sets"]}
    assert by_id["preference"]["brand"] == "Titleist"
    assert "Callaway" in by_id["preference"]["rationale"]
    assert by_id["distance"]["brand"] != "Titleist"
    assert by_id["control"]["brand"] != "Titleist"


def test_no_brand_still_covers_three_houses():
    result = _bags(GolferProfile(age=35, height_cm=175, gender="female"))
    brands = {bag["brand"] for bag in result["sets"]}
    assert brands == {"Titleist", "TaylorMade", "Callaway"}
    assert any("Titleist" in bag["rationale"] for bag in result["sets"] if bag["id"] == "preference")


def test_injured_player_is_softened_and_explained():
    result = _bags(
        GolferProfile(
            age=22,
            height_cm=183,
            weight_kg=82,
            gender="male",
            squat_kg=180,
            bench_press_kg=120,
            medical_flags=["back", "arthritis"],
        )
    )
    target = result["target"]
    assert target["flex_before_medical"] == "X"
    assert target["flex"] == "S"
    assert target["grip"] == "midsize"
    assert target["medical_loft_delta"] == 1.0
    assert "MED-1" in result["rules_fired"]
    assert any("back" in note for note in target["medical_notes"])
    for bag in result["sets"]:
        assert "back" in bag["rationale"].lower() or "shoulder" in bag["rationale"].lower() or "flex" in bag["rationale"].lower()


def test_low_bone_density_blocks_players_heads():
    result = _bags(
        GolferProfile(
            age=30,
            height_cm=178,
            gender="male",
            handicap=0,
            swing_speed_mph=110,
            medical_flags=["low_bone_density"],
        )
    )
    assert result["target"]["head_category_before_medical"] == "players"
    assert result["target"]["head_category"] == "game_improvement"
    for bag in result["sets"]:
        irons = next(club for club in bag["clubs"] if club["slot"] == "irons")
        assert irons["head"]["category"] != "players"


def test_tall_and_short_edges_on_the_sheet():
    tall = _bags(GolferProfile(age=28, height_cm=208, gender="male", wrist_to_floor_cm=102))
    assert tall["target"]["length_delta_in"] == 2.0
    assert tall["target"]["lie_delta_deg"] == 4.0
    short = _bags(GolferProfile(age=68, height_cm=147, gender="female", wrist_to_floor_cm=70))
    assert short["target"]["length_delta_in"] == -2.0
    assert short["target"]["flex"] == "L"


def test_synthetic_label_matches_the_engine():
    from app.synthetic import label_profile, sample_profile
    import random

    rng = random.Random(3)
    for _ in range(15):
        profile = sample_profile(rng)
        label = label_profile(profile)
        result = recommend(profile)
        assert label["flex"] == result["target"]["flex"]
        assert label["length_delta_in"] == result["target"]["length_delta_in"]
        assert [bag["brand"] for bag in result["sets"]] == [item["brand"] for item in label["sets"]]
