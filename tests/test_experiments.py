import pytest

from antenna_pattern_lab.experiments import (
    AlternationProtocol,
    ExperimentGoal,
    recommend_next_experiment,
)
from antenna_pattern_lab.profiles import AntennaProfile


def test_ab_protocol_requires_confirmation_before_each_interval():
    protocol = AlternationProtocol(10, 20, interval_seconds=3)
    assert protocol.start() == 10
    assert protocol.state == "awaiting_confirmation"
    assert protocol.confirm_switch() == 10
    assert protocol.tick(2) is None
    assert protocol.remaining_seconds == 1
    assert protocol.tick() == 20
    assert protocol.state == "awaiting_confirmation"
    assert protocol.confirm_switch() == 20
    assert protocol.remaining_seconds == 3


def test_ab_protocol_rejects_same_profile_and_can_stop():
    with pytest.raises(ValueError):
        AlternationProtocol(1, 1, 60)
    protocol = AlternationProtocol(1, 2, 60)
    protocol.start()
    protocol.stop()
    assert protocol.state == "idle"
    assert protocol.active_profile_id is None


def test_goal_validates_range_and_swr():
    goal = ExperimentGoal("20m", 90, 1000, 3000, 1.8)
    assert goal.validated() is goal
    with pytest.raises(ValueError):
        ExperimentGoal("20m", 360, 1000, 3000, 1.8).validated()
    with pytest.raises(ValueError):
        ExperimentGoal("20m", 90, 3000, 1000, 1.8).validated()


def test_recommendation_uses_model_only_to_choose_contrast_without_gain_claim():
    profiles = [
        AntennaProfile(id=1, name="Vertical", antenna_type="vertical"),
        AntennaProfile(
            id=2, name="Dipole", antenna_type="dipole", orientation_deg=90,
            wire_length_m=10.7,
        ),
        AntennaProfile(
            id=3, name="Yagi", antenna_type="yagi", orientation_deg=90,
            element_count=5,
        ),
    ]
    result = recommend_next_experiment(
        profiles, ExperimentGoal("20m", 90, 1000, 3000, 1.7)
    )
    assert result is not None
    assert result.profile_a_id == 2
    assert result.profile_b_id in (1, 3)
    assert result.basis == "model_contrast"
    assert "verify_swr" in result.notes
    assert "no_gain_claim" in result.notes


def test_recommendation_requires_two_profiles():
    goal = ExperimentGoal("40m", 0, 0, 1000, 2.0)
    assert recommend_next_experiment([], goal) is None
