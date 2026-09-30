import math

from data_io import to_minutes
from distance import haversine_km, road_km


def test_to_minutes_0930():
    assert to_minutes("09:30") == 570


def test_same_point_zero_distance():
    assert haversine_km(17.45, 78.28, 17.45, 78.28) < 1e-6
    assert road_km(17.45, 78.28, 17.45, 78.28) < 1e-6


def test_distance_symmetry():
    a = road_km(17.45, 78.28, 17.46, 78.29)
    b = road_km(17.46, 78.29, 17.45, 78.28)
    assert math.isclose(a, b, rel_tol=1e-9)
