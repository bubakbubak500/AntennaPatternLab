from datetime import datetime, timedelta, timezone

from antenna_pattern_lab.analysis import LocatedSpot
from antenna_pattern_lab.campaigns import MeasurementCampaign
from antenna_pattern_lab.domain import Spot
from antenna_pattern_lab.measurement_planner import recommend_measurement_window


def _campaign() -> MeasurementCampaign:
    return MeasurementCampaign(
        id=1,
        name="20m vertical",
        objective="Fill directional evidence",
        tx_call="OK7PS",
        tx_grid="JN79",
        band="20m",
        mode="FT8",
        antenna_profile_id=2,
        antenna_profile_name="Vertical",
        notes="Stable power",
        started_at=datetime(2026, 7, 20, tzinfo=timezone.utc),
        target_spots=30,
        target_receivers=5,
        target_sectors=6,
        target_time_blocks=8,
    )


def _located(
    observed_at: datetime,
    receiver: str,
    bearing: float,
    distance: float,
) -> LocatedSpot:
    return LocatedSpot(
        spot=Spot(
            sequence=None,
            frequency_hz=14_074_000,
            mode="FT8",
            snr_db=-10,
            observed_at=observed_at,
            tx_call="OK7PS",
            tx_grid="JN79",
            rx_call=receiver,
            rx_grid="JO62",
            band="20m",
        ),
        distance_km=distance,
        bearing_deg=bearing,
    )


def test_recommendation_uses_observed_receiver_window_and_estimates_rate():
    base = datetime(2026, 7, 20, 18, 0, tzinfo=timezone.utc)
    located = [
        _located(
            base + timedelta(days=day, minutes=receiver_index * 3),
            f"RX{receiver_index}",
            15 + receiver_index * 30,
            700 + receiver_index * 800,
        )
        for day in range(4)
        for receiver_index in range(5)
    ]
    now = datetime(2026, 7, 23, 12, 0, tzinfo=timezone.utc)

    result = recommend_measurement_window(_campaign(), located, now)

    assert len(result.candidates) == 48
    assert result.recommended.report_count > 0
    assert result.recommended.unique_receivers == 5
    assert result.next_start_utc > now
    assert result.next_start_utc.tzinfo == timezone.utc
    assert 30 <= result.suggested_duration_minutes <= 120
    assert result.spot_rate_per_hour == 10
    assert result.estimated_hours_to_numeric_goal is not None
    assert result.target_bearings
    assert result.target_distance_codes
    assert result.confidence == "medium"


def test_empty_campaign_returns_low_confidence_future_slot():
    now = datetime(2026, 7, 23, 12, 0, tzinfo=timezone.utc)

    result = recommend_measurement_window(_campaign(), [], now)

    assert len(result.candidates) == 48
    assert result.confidence == "low"
    assert result.spot_rate_per_hour is None
    assert result.next_start_utc > now
    assert result.suggested_duration_minutes == 120
    assert set(result.missing_goal_parts) == {
        "spots",
        "receivers",
        "sectors",
        "time_blocks",
    }
