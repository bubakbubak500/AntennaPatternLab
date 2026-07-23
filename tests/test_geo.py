import pytest

from antenna_pattern_lab.geo import (
    great_circle_segments,
    grid_distance_and_bearing,
    maidenhead_to_latlon,
)


def test_maidenhead_known_square_center():
    latitude, longitude = maidenhead_to_latlon("JN79")
    assert latitude == pytest.approx(49.5)
    assert longitude == pytest.approx(15.0)


def test_longer_locator_is_more_precise():
    latitude, longitude = maidenhead_to_latlon("JN79AA")
    assert 49.0 < latitude < 49.05
    assert 14.0 < longitude < 14.09


@pytest.mark.parametrize("grid", ["", "JN7", "ZZ99", "JN7X", "JN79A1"])
def test_invalid_locator_is_rejected(grid):
    with pytest.raises(ValueError):
        maidenhead_to_latlon(grid)


def test_distance_and_bearing_are_plausible():
    distance, bearing = grid_distance_and_bearing("JN79", "FN42")
    assert 6000 < distance < 7000
    assert 285 < bearing < 310


def test_great_circle_is_split_at_antimeridian():
    segments = great_circle_segments((35.0, 170.0), (35.0, -170.0))
    assert len(segments) == 2
    assert all(
        abs(right[1] - left[1]) < 180
        for segment in segments
        for left, right in zip(segment, segment[1:])
    )
