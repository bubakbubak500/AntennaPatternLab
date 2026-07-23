from dataclasses import replace
from datetime import datetime, timedelta, timezone

from antenna_pattern_lab.analysis import (
    PairedSpot,
    ab_sector_profile,
    bootstrap_median_interval,
    compare_profile_spots,
    recommend_ab_measurement,
)
from antenna_pattern_lab.domain import Spot


def spot(rx, snr, minute, band="20m"):
    return Spot(
        sequence=None,
        frequency_hz=14_074_000,
        mode="FT8",
        snr_db=snr,
        observed_at=datetime(2026, 7, 22, 12, minute, tzinfo=timezone.utc),
        tx_call="OK7PS",
        tx_grid="JN79",
        rx_call=rx,
        rx_grid="JO62",
        band=band,
    )


def test_ab_comparison_pairs_same_receiver_in_time_window():
    a = [spot("DL1A", -12, 0), spot("G4A", -15, 10)]
    b = [spot("DL1A", -8, 5), spot("G4A", -16, 50)]
    result = compare_profile_spots(a, b, max_gap_seconds=20 * 60)
    assert len(result.pairs) == 1
    assert result.pairs[0].delta_db == 4
    assert result.median_delta_db == 4
    assert result.unique_receivers == 1


def test_ab_comparison_never_pairs_different_band():
    result = compare_profile_spots([spot("DL1A", -10, 0)], [spot("DL1A", -5, 1, "40m")])
    assert result.pairs == []


def test_bootstrap_interval_is_deterministic_and_requires_three_values():
    assert bootstrap_median_interval([1, 2]) == (None, None)
    first = bootstrap_median_interval([-2, 1, 3, 4, 5])
    assert first == bootstrap_median_interval([-2, 1, 3, 4, 5])
    assert first[0] <= 3 <= first[1]


def test_ab_sector_profile_keeps_directional_results_separate():
    pairs = [
        PairedSpot("DL1A", 10, 60, -10, -7),
        PairedSpot("DL2A", 20, 60, -12, -8),
        PairedSpot("G4A", 190, 60, -5, -8),
    ]
    sectors = ab_sector_profile(pairs, 90)
    assert sectors[0].count == 2
    assert sectors[0].median_delta_db == 3.5
    assert sectors[0].unique_receivers == 2
    assert sectors[2].median_delta_db == -3


def test_ab_result_gives_each_receiver_equal_weight():
    a = [spot("LOUD", -20 + index, index) for index in range(5)] + [spot("OTHER", -10, 10)]
    b = [spot("LOUD", -10 + index, index) for index in range(5)] + [spot("OTHER", -20, 10)]
    result = compare_profile_spots(a, b)
    assert result.pair_median_delta_db == 10
    assert result.median_delta_db == 0  # median of LOUD +10 and OTHER -10


def test_measurement_recommendation_estimates_remaining_collection_time():
    start = datetime(2026, 7, 22, 12, tzinfo=timezone.utc)
    pairs = [
        PairedSpot(
            f"RX{index % 4}", 10, 60, -10, -8, start + timedelta(minutes=index * 10)
        )
        for index in range(10)
    ]
    from antenna_pattern_lab.analysis import AbComparison

    comparison = AbComparison(pairs, 2, 4)
    recommendation = recommend_ab_measurement(comparison, target_pairs=20, target_receivers=6)
    assert recommendation.additional_pairs == 10
    assert recommendation.additional_receivers == 2
    assert recommendation.estimated_additional_hours is not None
