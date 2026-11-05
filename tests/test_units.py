"""US units round-trip. The chart never sees feet or pounds."""

from app.units import cm_to_ft_in, cm_to_inches, ft_in_to_cm, inches_to_cm, kg_to_lb, lb_to_kg


def test_height_round_trip():
    cm = ft_in_to_cm(5, 11)
    feet, inches = cm_to_ft_in(cm)
    assert feet == 5
    assert inches == 11


def test_weight_and_wrist_round_trip():
    assert kg_to_lb(lb_to_kg(190)) == 190
    assert cm_to_inches(inches_to_cm(35)) == 35
    assert kg_to_lb(lb_to_kg(265)) == 265
