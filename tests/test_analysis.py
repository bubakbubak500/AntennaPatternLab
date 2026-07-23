from dataclasses import replace
from datetime import datetime, timedelta, timezone

from antenna_pattern_lab.analysis import (
    LocatedSpot,
    control_group_adjusted_sector_profile,
    filter_located_spots,
    receiver_balanced_sector_profile,
    receiver_stability,
    sector_profile,
    sector_quality,
    smooth_sector_pattern,
    time_normalized_sector_profile,
    trend_adjusted_sector_profile,
)
from antenna_pattern_lab.domain import Spot


def make_located(bearing: float, snr: int, distance: float = 1000) -> LocatedSpot:
    return LocatedSpot(
        spot=Spot(
            sequence=None,
            frequency_hz=14_074_000,
            mode="FT8",
            snr_db=snr,
            observed_at=datetime.now(timezone.utc),
            tx_call="OK7PS",
            tx_grid="JN79",
            rx_call=f"RX{bearing}",
            rx_grid="JO62",
            band="20m",
        ),
        distance_km=distance,
        bearing_deg=bearing,
    )


def test_sector_profile_uses_median_and_counts():
    profile = sector_profile([make_located(2, -20), make_located(8, -4), make_located(15, -10)])
    assert profile[0].count == 2
    assert profile[0].median_snr_db == -12
    assert profile[1].count == 1
    assert profile[1].best_snr_db == -10
    assert profile[0].confidence_low_db is None  # only two observations


def test_smooth_sector_pattern_uses_power_domain_and_keeps_large_gaps_unknown():
    profile = sector_profile(
        [make_located(2, -20), make_located(8, -10), make_located(92, -5)],
        10,
    )
    curve = smooth_sector_pattern(
        profile, step_deg=5, kernel_width_deg=20, max_gap_deg=55
    )
    by_bearing = {point.bearing_deg: point for point in curve}
    assert by_bearing[5.0].level_db is not None
    assert by_bearing[45.0].level_db is not None
    assert by_bearing[180.0].level_db is None
    assert by_bearing[180.0].support == 0
    # Linear power averaging gives stronger observations their physical weight.
    assert by_bearing[45.0].level_db > -12.5


def test_smooth_sector_pattern_wraps_cleanly_across_north():
    profile = sector_profile(
        [make_located(355, -8), make_located(5, -10)],
        10,
    )
    curve = smooth_sector_pattern(
        profile, step_deg=5, kernel_width_deg=15, max_gap_deg=45
    )
    assert curve[0].level_db is not None
    assert curve[-1].level_db == curve[0].level_db
    assert curve[len(curve) // 2].level_db is None


def test_sector_width_must_divide_circle():
    try:
        sector_profile([], 7)
    except ValueError as exc:
        assert "dělitel" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_sector_quality_requires_sample_count_and_receiver_diversity():
    assert sector_quality(0, 0) == (0.0, "none")
    assert sector_quality(4, 4)[1] == "low"
    assert sector_quality(5, 3)[1] == "medium"
    assert sector_quality(10, 5) == (1.0, "high")


def test_filter_located_spots_combines_time_and_distance():
    now = datetime(2026, 7, 23, 12, tzinfo=timezone.utc)
    recent_near = make_located(10, -10, 900)
    recent_near = LocatedSpot(
        spot=replace(recent_near.spot, observed_at=now - timedelta(hours=2)),
        distance_km=recent_near.distance_km,
        bearing_deg=recent_near.bearing_deg,
    )
    old_far = make_located(20, -5, 3500)
    result = filter_located_spots(
        [recent_near, old_far], hours=6, max_distance_km=1000, now=now
    )
    assert result == [recent_near]


def test_filter_located_spots_uses_approximate_tx_solar_time():
    base = make_located(10, -10, 900)
    daytime = LocatedSpot(
        spot=replace(
            base.spot,
            observed_at=datetime(2026, 7, 23, 10, tzinfo=timezone.utc),
        ),
        distance_km=base.distance_km,
        bearing_deg=base.bearing_deg,
    )
    # At 30° E, 10:00 UTC is approximately 12:00 local solar time.
    assert filter_located_spots(
        [daytime], solar_period="day", tx_longitude_deg=30
    ) == [daytime]
    assert filter_located_spots(
        [daytime], solar_period="night", tx_longitude_deg=30
    ) == []


def test_time_normalization_gives_each_block_equal_weight():
    start = datetime(2026, 7, 23, 10, tzinfo=timezone.utc)
    crowded = []
    for minute in range(5):
        item = make_located(10, -20, 1000)
        crowded.append(
            LocatedSpot(
                spot=replace(item.spot, observed_at=start + timedelta(minutes=minute)),
                distance_km=item.distance_km,
                bearing_deg=item.bearing_deg,
            )
        )
    later = make_located(10, 0, 1000)
    later = LocatedSpot(
        spot=replace(later.spot, observed_at=start + timedelta(minutes=35)),
        distance_km=later.distance_km,
        bearing_deg=later.bearing_deg,
    )
    raw = sector_profile([*crowded, later], 30)[0]
    normalized = time_normalized_sector_profile([*crowded, later], 30, 30)[0]
    assert raw.median_snr_db == -20
    assert normalized.median_snr_db == -10
    assert normalized.time_block_count == 2


def test_trend_adjustment_removes_shared_slow_drift():
    start = datetime(2026, 7, 23, 10, tzinfo=timezone.utc)
    items = []
    for block, drift in enumerate((-10, 0, 10)):
        for bearing, directional in ((10, -3), (190, 3)):
            item = make_located(bearing, drift + directional)
            items.append(
                LocatedSpot(
                    spot=replace(
                        item.spot,
                        observed_at=start + timedelta(minutes=30 * block),
                        rx_call=f"RX-{block}-{bearing}",
                    ),
                    distance_km=item.distance_km,
                    bearing_deg=item.bearing_deg,
                )
            )
    adjusted = trend_adjusted_sector_profile(items, 90, block_minutes=30)
    assert adjusted[0].median_snr_db == -3
    assert adjusted[2].median_snr_db == 3
    assert adjusted[0].time_block_count == 3


def test_receiver_balancing_caps_a_very_active_reporter_to_one_sector_vote():
    start = datetime(2026, 7, 23, 10, tzinfo=timezone.utc)
    active = []
    for index in range(21):
        item = make_located(10, -20)
        active.append(
            LocatedSpot(
                spot=replace(
                    item.spot,
                    observed_at=start + timedelta(seconds=index),
                    rx_call="ACTIVE",
                ),
                distance_km=item.distance_km,
                bearing_deg=item.bearing_deg,
            )
        )
    quiet = []
    for call, snr in (("QUIET-A", 0), ("QUIET-B", 2)):
        item = make_located(10, snr)
        quiet.append(
            LocatedSpot(
                spot=replace(item.spot, observed_at=start, rx_call=call),
                distance_km=item.distance_km,
                bearing_deg=item.bearing_deg,
            )
        )

    raw = sector_profile([*active, *quiet], 30)[0]
    balanced, stability = receiver_balanced_sector_profile(
        [*active, *quiet], 30
    )

    assert raw.median_snr_db == -20
    assert balanced[0].median_snr_db == 0
    assert balanced[0].count == 23
    assert balanced[0].unique_receivers == 3
    assert {item.receiver_call for item in stability} == {
        "ACTIVE",
        "QUIET-A",
        "QUIET-B",
    }


def test_receiver_stability_uses_concurrent_rx_and_detects_variability():
    start = datetime(2026, 7, 23, 10, tzinfo=timezone.utc)
    items = []
    for block, common in enumerate((-10, 0, 10, 4, -4)):
        for call, residual in (
            ("STABLE-A", 2),
            ("STABLE-B", -2),
            ("VARIABLE", (-10, 10, -10, 10, 0)[block]),
        ):
            item = make_located(10, common + residual)
            items.append(
                LocatedSpot(
                    spot=replace(
                        item.spot,
                        observed_at=start + timedelta(minutes=30 * block),
                        rx_call=call,
                    ),
                    distance_km=item.distance_km,
                    bearing_deg=item.bearing_deg,
                )
            )

    result = {item.receiver_call: item for item in receiver_stability(items)}

    assert result["STABLE-A"].comparable_blocks == 5
    assert result["STABLE-A"].stability_label == "stable"
    assert result["STABLE-A"].variability_mad_db <= 2
    assert result["STABLE-A"].reliability_weight >= 0.8
    assert result["VARIABLE"].stability_label == "unstable"
    assert result["VARIABLE"].variability_mad_db > 6
    assert result["VARIABLE"].reliability_weight < 0.5


def test_stable_angular_control_group_removes_shared_time_shift():
    start = datetime(2026, 7, 23, 10, tzinfo=timezone.utc)
    items = []
    directions = (
        ("RX-N", 10.0, -4),
        ("RX-E", 100.0, 2),
        ("RX-S", 190.0, -2),
        ("RX-W", 280.0, 4),
    )
    common_shifts = (-9, -3, 5, 7, 1)
    for block, shift in enumerate(common_shifts):
        for call, bearing, directional in directions:
            item = make_located(bearing, directional + shift)
            items.append(
                LocatedSpot(
                    spot=replace(
                        item.spot,
                        observed_at=start + timedelta(minutes=30 * block),
                        rx_call=call,
                    ),
                    distance_km=item.distance_km,
                    bearing_deg=bearing,
                )
            )

    profile, stability, group = control_group_adjusted_sector_profile(
        items, 90
    )

    assert group.ready
    assert group.reason_code == "ready"
    assert len(group.receiver_calls) == 4
    assert group.angular_sector_count == 4
    assert group.comparable_block_count == 5
    assert len(group.trend) == 5
    assert {item.stability_label for item in stability} == {"stable"}
    # The common shift is removed while directional differences are preserved.
    assert [sector.median_snr_db for sector in profile] == [-3, 3, -1, 5]


def test_control_group_refuses_stable_receivers_from_one_direction():
    start = datetime(2026, 7, 23, 10, tzinfo=timezone.utc)
    items = []
    for block in range(4):
        for index, call in enumerate(("RX-A", "RX-B", "RX-C")):
            item = make_located(10 + index, -10 + block + index)
            items.append(
                LocatedSpot(
                    spot=replace(
                        item.spot,
                        observed_at=start + timedelta(minutes=30 * block),
                        rx_call=call,
                    ),
                    distance_km=item.distance_km,
                    bearing_deg=item.bearing_deg,
                )
            )

    profile, _stability, group = control_group_adjusted_sector_profile(
        items, 30
    )

    assert not group.ready
    assert group.reason_code == "directions"
    assert group.angular_sector_count == 1
    assert group.trend == ()
    assert profile[0].median_snr_db is not None
