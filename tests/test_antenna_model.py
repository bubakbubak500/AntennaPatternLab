import json

import pytest

from antenna_pattern_lab.antenna_model import (
    MODEL_SCHEMA,
    AntennaModel,
    Excitation,
    FrequencySweep,
    Ground,
    Point3D,
    Wire,
    antenna_template,
    model_limits,
    parse_nec_deck,
)


@pytest.mark.parametrize("kind", ("dipole", "inverted_v", "vertical", "loop", "yagi"))
def test_templates_are_valid_and_emit_supported_nec2(kind):
    model = antenna_template(kind)

    assert not [issue for issue in model.validate() if issue.severity == "error"]
    deck = model.to_nec()
    assert "GW " in deck
    assert "EX 0 " in deck
    assert "RP 0 19 73" in deck
    assert deck.endswith("EN\n")


def test_versioned_model_json_is_stable_and_round_trips():
    model = antenna_template("dipole", orientation_deg=37)
    restored = AntennaModel.from_json(model.canonical_json())

    assert restored == model
    assert restored.schema == MODEL_SCHEMA
    assert restored.sha256 == model.sha256
    assert json.loads(model.canonical_json())["orientation_deg"] == 37


def test_generated_nec_supported_subset_round_trips_without_geometry_loss():
    original = antenna_template("yagi", frequency_hz=21_074_000, height_m=12)
    restored = parse_nec_deck(original.to_nec())

    assert restored.name == original.name
    assert restored.wires == original.wires
    assert restored.excitations == original.excitations
    assert restored.frequency == original.frequency
    assert restored.ground == original.ground
    assert restored.orientation_deg == original.orientation_deg
    assert restored.sha256 == original.sha256


def test_generated_nec_preserves_unicode_name_in_ascii_deck():
    original = antenna_template("yagi")
    original = AntennaModel(
        "3-element Yagi · Δh −2 m · reálná zem",
        original.wires,
        original.excitations,
        original.loads,
        original.ground,
        original.frequency,
        original.orientation_deg,
    )

    deck = original.to_nec()
    restored = parse_nec_deck(deck)

    assert deck.isascii()
    assert "CM NAME-JSON" in deck
    assert restored.name == original.name
    assert restored.sha256 == original.sha256


def test_parser_refuses_unsupported_cards_instead_of_silently_losing_them():
    deck = antenna_template("dipole").to_nec().replace("EN\n", "SP 0 0 0 0\nEN\n")

    with pytest.raises(ValueError, match="SP"):
        parse_nec_deck(deck)


def test_validation_reports_nec2_geometry_and_source_failures():
    model = AntennaModel(
        "",
        (Wire(1, Point3D(0, 0, -1), Point3D(0, 0, -1), 2, 1.0),),
        (Excitation(9, 3),),
        ground=Ground("unsupported"),
        frequency=FrequencySweep(0, -1, 0),
    )
    codes = {issue.code for issue in model.validate()}

    assert {"name", "zero_length", "below_ground", "source_wire", "frequency", "frequency_steps", "ground"} <= codes
    assert len(model_limits()) == 3


def test_transform_changes_height_and_orientation_without_mutating_source():
    model = antenna_template("dipole")
    transformed = model.transformed(height_delta_m=3, orientation_deg=90)

    assert transformed.orientation_deg == 90
    assert min(wire.start.z_m for wire in transformed.wires) == 13
    assert transformed.wires[0].start.y_m < -1
    assert model.orientation_deg == 0
