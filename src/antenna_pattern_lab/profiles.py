from __future__ import annotations

from dataclasses import dataclass

ANTENNA_TYPES = (
    "vertical",
    "efhw",
    "efrw",
    "dipole",
    "inverted_v",
    "yagi",
    "other",
)
WIRE_TYPES = frozenset(("efhw", "efrw", "dipole", "inverted_v"))


def normalize_antenna_type(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "vertikal": "vertical",
        "vertikál": "vertical",
        "invertedv": "inverted_v",
        "inv_v": "inverted_v",
        "dipól": "dipole",
    }
    normalized = aliases.get(normalized, normalized)
    return normalized if normalized in ANTENNA_TYPES else "other"


@dataclass(frozen=True, slots=True)
class AntennaProfile:
    id: int | None
    name: str
    antenna_type: str = ""
    apex_height_m: float | None = None
    end_height_m: float | None = None
    orientation_deg: float | None = None
    power_w: float | None = None
    tuner_enabled: bool = False
    wire_length_m: float | None = None
    radial_count: int | None = None
    radial_length_m: float | None = None
    element_count: int | None = None
    boom_length_m: float | None = None
    transformer_ratio: str = ""
    notes: str = ""
    archived: bool = False
    revision: int = 1
    predecessor_id: int | None = None

    def validated(self) -> "AntennaProfile":
        name = self.name.strip()
        if not name:
            raise ValueError("Profile name is required.")
        if self.orientation_deg is not None and not 0 <= self.orientation_deg < 360:
            raise ValueError("Orientation must be between 0 and 359.9 degrees.")
        antenna_type = normalize_antenna_type(self.antenna_type)
        for label, value in (
            ("Apex height", self.apex_height_m),
            ("End height", self.end_height_m),
            ("Power", self.power_w),
            ("Wire length", self.wire_length_m),
            ("Radial length", self.radial_length_m),
            ("Boom length", self.boom_length_m),
        ):
            if value is not None and value < 0:
                raise ValueError(f"{label} cannot be negative.")
        for label, value in (
            ("Radial count", self.radial_count),
            ("Element count", self.element_count),
        ):
            if value is not None and value < 1:
                raise ValueError(f"{label} must be at least one.")
        return AntennaProfile(
            id=self.id,
            name=name,
            antenna_type=antenna_type,
            apex_height_m=self.apex_height_m,
            end_height_m=self.end_height_m,
            orientation_deg=self.orientation_deg,
            power_w=self.power_w,
            tuner_enabled=self.tuner_enabled,
            wire_length_m=self.wire_length_m,
            radial_count=self.radial_count,
            radial_length_m=self.radial_length_m,
            element_count=self.element_count,
            boom_length_m=self.boom_length_m,
            transformer_ratio=self.transformer_ratio.strip(),
            notes=self.notes.strip(),
            archived=self.archived,
            revision=max(1, int(self.revision)),
            predecessor_id=self.predecessor_id,
        )


def expected_main_bearings(profile: AntennaProfile) -> tuple[float, ...]:
    """Return semantic reference bearings, never a claimed measured pattern."""
    if profile.orientation_deg is None:
        return ()
    orientation = profile.orientation_deg % 360
    antenna_type = normalize_antenna_type(profile.antenna_type)
    if antenna_type in WIRE_TYPES:
        # Profile orientation is the wire axis; simple free-space expectation
        # is broadside in both directions. Installation/ground can alter it.
        return ((orientation + 90) % 360, (orientation + 270) % 360)
    if antenna_type == "yagi":
        # For a Yagi orientation explicitly means forward boom bearing.
        return (orientation,)
    return ()
