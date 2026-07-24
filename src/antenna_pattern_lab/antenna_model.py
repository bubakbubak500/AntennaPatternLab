from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import hashlib
import json
from math import cos, pi, radians, sin, sqrt
import re
from typing import Iterable


MODEL_SCHEMA = "apl-nec-model/1"
SPEED_OF_LIGHT_M_S = 299_792_458.0


@dataclass(frozen=True, slots=True)
class Point3D:
    x_m: float
    y_m: float
    z_m: float


@dataclass(frozen=True, slots=True)
class Wire:
    tag: int
    start: Point3D
    end: Point3D
    segments: int
    radius_m: float
    label: str = ""

    @property
    def length_m(self) -> float:
        return sqrt(
            (self.end.x_m - self.start.x_m) ** 2
            + (self.end.y_m - self.start.y_m) ** 2
            + (self.end.z_m - self.start.z_m) ** 2
        )


@dataclass(frozen=True, slots=True)
class Excitation:
    wire_tag: int
    segment: int
    voltage_real: float = 1.0
    voltage_imag: float = 0.0


@dataclass(frozen=True, slots=True)
class WireLoad:
    wire_tag: int
    first_segment: int
    last_segment: int
    resistance_ohm: float = 0.0
    inductance_h: float = 0.0
    capacitance_f: float = 0.0


@dataclass(frozen=True, slots=True)
class Ground:
    kind: str = "real"
    relative_permittivity: float = 13.0
    conductivity_s_m: float = 0.005


@dataclass(frozen=True, slots=True)
class FrequencySweep:
    start_hz: int = 14_000_000
    stop_hz: int = 14_350_000
    steps: int = 8

    @property
    def step_hz(self) -> float:
        return 0.0 if self.steps <= 1 else (self.stop_hz - self.start_hz) / (self.steps - 1)

    def frequencies_hz(self) -> tuple[int, ...]:
        if self.steps <= 1:
            return (self.start_hz,)
        return tuple(round(self.start_hz + index * self.step_hz) for index in range(self.steps))


@dataclass(frozen=True, slots=True)
class ModelIssue:
    severity: str
    code: str
    message: str
    wire_tag: int | None = None


@dataclass(frozen=True, slots=True)
class AntennaModel:
    name: str
    wires: tuple[Wire, ...]
    excitations: tuple[Excitation, ...]
    loads: tuple[WireLoad, ...] = ()
    ground: Ground = Ground()
    frequency: FrequencySweep = FrequencySweep()
    orientation_deg: float = 0.0
    notes: str = ""
    schema: str = MODEL_SCHEMA

    def canonical_dict(self) -> dict[str, object]:
        return asdict(self)

    def canonical_json(self) -> str:
        return json.dumps(
            self.canonical_dict(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

    @classmethod
    def from_json(cls, payload: str) -> "AntennaModel":
        raw = json.loads(payload)
        if raw.get("schema") != MODEL_SCHEMA:
            raise ValueError(f"Unsupported antenna-model schema: {raw.get('schema')!r}")
        wires = tuple(
            Wire(
                int(item["tag"]),
                Point3D(**item["start"]),
                Point3D(**item["end"]),
                int(item["segments"]),
                float(item["radius_m"]),
                str(item.get("label", "")),
            )
            for item in raw["wires"]
        )
        excitations = tuple(Excitation(**item) for item in raw["excitations"])
        loads = tuple(WireLoad(**item) for item in raw.get("loads", ()))
        return cls(
            name=str(raw["name"]),
            wires=wires,
            excitations=excitations,
            loads=loads,
            ground=Ground(**raw["ground"]),
            frequency=FrequencySweep(**raw["frequency"]),
            orientation_deg=float(raw.get("orientation_deg", 0.0)),
            notes=str(raw.get("notes", "")),
            schema=str(raw["schema"]),
        )

    def validate(self) -> tuple[ModelIssue, ...]:
        issues: list[ModelIssue] = []
        if self.schema != MODEL_SCHEMA:
            issues.append(ModelIssue("error", "schema", "Unsupported model schema."))
        if not self.name.strip():
            issues.append(ModelIssue("error", "name", "Model name is required."))
        if not self.wires:
            issues.append(ModelIssue("error", "wires", "At least one wire is required."))
        tags = [wire.tag for wire in self.wires]
        if any(tag <= 0 for tag in tags) or len(tags) != len(set(tags)):
            issues.append(ModelIssue("error", "wire_tags", "Wire tags must be unique positive integers."))
        by_tag = {wire.tag: wire for wire in self.wires}
        minimum_frequency = max(1, min(self.frequency.frequencies_hz()))
        wavelength = SPEED_OF_LIGHT_M_S / minimum_frequency
        for wire in self.wires:
            if wire.length_m <= 0:
                issues.append(ModelIssue("error", "zero_length", "Wire has zero length.", wire.tag))
            if wire.segments <= 0:
                issues.append(ModelIssue("error", "segments", "Segment count must be positive.", wire.tag))
            elif wire.segments % 2 == 0:
                issues.append(ModelIssue("warning", "even_segments", "Odd segment counts place feeds more predictably.", wire.tag))
            if wire.radius_m <= 0:
                issues.append(ModelIssue("error", "radius", "Wire radius must be positive.", wire.tag))
            segment_length = wire.length_m / max(1, wire.segments)
            if segment_length > wavelength * 0.1:
                issues.append(ModelIssue("warning", "coarse_segmentation", "Segments exceed 0.1 wavelength.", wire.tag))
            if wire.radius_m and segment_length / wire.radius_m < 2:
                issues.append(ModelIssue("error", "thick_wire", "Segment length must be at least twice the wire radius.", wire.tag))
            if self.ground.kind != "free_space" and min(wire.start.z_m, wire.end.z_m) < 0:
                issues.append(ModelIssue("error", "below_ground", "Wire geometry extends below ground.", wire.tag))
        if not self.excitations:
            issues.append(ModelIssue("error", "source", "At least one voltage source is required."))
        for source in self.excitations:
            wire = by_tag.get(source.wire_tag)
            if wire is None:
                issues.append(ModelIssue("error", "source_wire", "Source references a missing wire.", source.wire_tag))
            elif not 1 <= source.segment <= wire.segments:
                issues.append(ModelIssue("error", "source_segment", "Source segment is outside the wire.", source.wire_tag))
        for load in self.loads:
            wire = by_tag.get(load.wire_tag)
            if wire is None:
                issues.append(ModelIssue("error", "load_wire", "Load references a missing wire.", load.wire_tag))
            elif not (1 <= load.first_segment <= load.last_segment <= wire.segments):
                issues.append(ModelIssue("error", "load_segments", "Load segment range is invalid.", load.wire_tag))
        if self.frequency.start_hz <= 0 or self.frequency.stop_hz < self.frequency.start_hz:
            issues.append(ModelIssue("error", "frequency", "Frequency sweep is invalid."))
        if not 1 <= self.frequency.steps <= 999:
            issues.append(ModelIssue("error", "frequency_steps", "Frequency steps must be between 1 and 999."))
        if self.ground.kind not in {"free_space", "perfect", "real"}:
            issues.append(ModelIssue("error", "ground", "Ground must be free-space, perfect, or real."))
        if self.ground.kind == "real" and (
            self.ground.relative_permittivity < 1 or self.ground.conductivity_s_m < 0
        ):
            issues.append(ModelIssue("error", "ground_values", "Real-ground parameters are invalid."))
        for left_index, left in enumerate(self.wires):
            for right in self.wires[left_index + 1 :]:
                if _near(left.start, right.start) or _near(left.start, right.end) or _near(left.end, right.start) or _near(left.end, right.end):
                    continue
                if _segments_cross_approximately(left, right):
                    issues.append(ModelIssue("warning", "unconnected_crossing", f"Wires {left.tag} and {right.tag} cross without a shared endpoint."))
        return tuple(issues)

    def to_nec(self) -> str:
        errors = [issue for issue in self.validate() if issue.severity == "error"]
        if errors:
            raise ValueError("; ".join(issue.message for issue in errors))
        lines = [
            f"CM APL-MODEL {self.schema} {self.sha256}",
            "CM NAME-JSON " + json.dumps(self.name, ensure_ascii=True),
            f"CM ORIENTATION-DEG {self.orientation_deg:.6f}",
            "CE",
        ]
        for wire in self.wires:
            if wire.label:
                lines.append(
                    f"CM WIRE-LABEL {wire.tag} "
                    + json.dumps(wire.label, ensure_ascii=True)
                )
            lines.append(
                "GW {tag:d} {segments:d} {x1:.17g} {y1:.17g} {z1:.17g} "
                "{x2:.17g} {y2:.17g} {z2:.17g} {radius:.17g}".format(
                    tag=wire.tag,
                    segments=wire.segments,
                    x1=wire.start.x_m,
                    y1=wire.start.y_m,
                    z1=wire.start.z_m,
                    x2=wire.end.x_m,
                    y2=wire.end.y_m,
                    z2=wire.end.z_m,
                    radius=wire.radius_m,
                )
            )
        lines.append("GE 0" if self.ground.kind != "free_space" else "GE 1")
        if self.ground.kind == "free_space":
            lines.append("GN -1")
        elif self.ground.kind == "perfect":
            lines.append("GN 1")
        else:
            lines.append(
                f"GN 2 0 0 0 {self.ground.relative_permittivity:.17g} "
                f"{self.ground.conductivity_s_m:.17g}"
            )
        for load in self.loads:
            lines.append(
                f"LD 0 {load.wire_tag} {load.first_segment} {load.last_segment} "
                f"{load.resistance_ohm:.17g} {load.inductance_h:.17g} "
                f"{load.capacitance_f:.17g}"
            )
        for source in self.excitations:
            lines.append(
                f"EX 0 {source.wire_tag} {source.segment} 0 "
                f"{source.voltage_real:.17g} {source.voltage_imag:.17g}"
            )
        lines.append(
            f"FR 0 {self.frequency.steps} 0 0 "
            f"{self.frequency.start_hz / 1e6:.17g} "
            f"{self.frequency.step_hz / 1e6:.17g}"
        )
        # 19 elevations × 73 azimuths includes both principal cuts and supports
        # a rotatable 3-D plot without requesting a solver-specific extension.
        lines.extend(("RP 0 19 73 1000 0 0 5 5", "EN"))
        return "\n".join(lines) + "\n"

    def transformed(self, *, height_delta_m: float = 0.0, orientation_deg: float | None = None, ground: Ground | None = None) -> "AntennaModel":
        target_orientation = self.orientation_deg if orientation_deg is None else orientation_deg
        angle = radians(target_orientation - self.orientation_deg)
        cosine, sine = cos(angle), sin(angle)

        def point(value: Point3D) -> Point3D:
            return Point3D(
                value.x_m * cosine - value.y_m * sine,
                value.x_m * sine + value.y_m * cosine,
                value.z_m + height_delta_m,
            )

        return replace(
            self,
            wires=tuple(replace(wire, start=point(wire.start), end=point(wire.end)) for wire in self.wires),
            orientation_deg=target_orientation % 360.0,
            ground=ground or self.ground,
        )


def antenna_template(kind: str, *, frequency_hz: int = 14_074_000, height_m: float = 10.0, orientation_deg: float = 0.0) -> AntennaModel:
    wavelength = SPEED_OF_LIGHT_M_S / frequency_hz
    radius = 0.001
    sweep = FrequencySweep(round(frequency_hz * 0.985), round(frequency_hz * 1.015), 9)
    kind = kind.strip().lower().replace("-", "_")
    if kind == "dipole":
        half = wavelength * 0.475 / 2
        wires = (
            Wire(1, Point3D(-half, 0, height_m), Point3D(0, 0, height_m), 11, radius, "left"),
            Wire(2, Point3D(0, 0, height_m), Point3D(half, 0, height_m), 11, radius, "right"),
        )
        source = Excitation(1, 11)
        name = "Half-wave dipole"
    elif kind in {"inverted_v", "invertedv"}:
        half = wavelength * 0.475 / 2
        end_height = max(0.5, height_m * 0.35)
        wires = (
            Wire(1, Point3D(-half * 0.82, 0, end_height), Point3D(0, 0, height_m), 11, radius, "left leg"),
            Wire(2, Point3D(0, 0, height_m), Point3D(half * 0.82, 0, end_height), 11, radius, "right leg"),
        )
        source = Excitation(1, 11)
        name = "Inverted-V"
    elif kind == "vertical":
        length = wavelength * 0.238
        wires = [Wire(1, Point3D(0, 0, 0.02), Point3D(0, 0, length), 21, radius, "radiator")]
        for index in range(4):
            angle = 2 * pi * index / 4
            wires.append(Wire(index + 2, Point3D(0, 0, 0.02), Point3D(length * cos(angle), length * sin(angle), 0.02), 11, radius, f"radial {index + 1}"))
        wires = tuple(wires)
        source = Excitation(1, 1)
        name = "Quarter-wave vertical"
    elif kind == "loop":
        side = wavelength / 4
        z = height_m
        corners = (
            Point3D(-side / 2, 0, z - side / 2),
            Point3D(-side / 2, 0, z + side / 2),
            Point3D(side / 2, 0, z + side / 2),
            Point3D(side / 2, 0, z - side / 2),
        )
        wires = tuple(Wire(i + 1, corners[i], corners[(i + 1) % 4], 11, radius, f"side {i + 1}") for i in range(4))
        source = Excitation(1, 6)
        name = "Full-wave loop"
    elif kind == "yagi":
        lengths = (0.505, 0.475, 0.455)
        positions = (-0.2, 0.0, 0.25)
        wires = tuple(
            Wire(index + 1, Point3D(position * wavelength, -factor * wavelength / 2, height_m), Point3D(position * wavelength, factor * wavelength / 2, height_m), 21, radius, ("reflector", "driven", "director")[index])
            for index, (factor, position) in enumerate(zip(lengths, positions))
        )
        source = Excitation(2, 11)
        name = "3-element Yagi"
    else:
        raise ValueError(f"Unknown antenna template: {kind}")
    model = AntennaModel(name, tuple(wires), (source,), ground=Ground(), frequency=sweep)
    return model.transformed(orientation_deg=orientation_deg)


def parse_nec_deck(text: str, *, name: str = "Imported NEC model") -> AntennaModel:
    wires: list[Wire] = []
    excitations: list[Excitation] = []
    loads: list[WireLoad] = []
    ground = Ground("free_space")
    frequency = FrequencySweep()
    orientation = 0.0
    parsed_name = name
    wire_labels: dict[int, str] = {}
    unsupported: set[str] = set()
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        fields = re.split(r"[\s,]+", line)
        card = fields[0].upper()
        if card == "CM":
            body = line[2:].strip()
            if body.upper().startswith("NAME-JSON "):
                parsed_name = str(json.loads(body.split(None, 1)[1]))
            elif body.upper().startswith("NAME "):
                parsed_name = body[5:].strip() or parsed_name
            elif body.upper().startswith("ORIENTATION-DEG "):
                orientation = float(body.split(None, 1)[1])
            elif body.upper().startswith("WIRE-LABEL "):
                match = re.match(r"WIRE-LABEL\s+(\d+)\s+(.+)", body, re.IGNORECASE)
                if match:
                    wire_labels[int(match.group(1))] = str(json.loads(match.group(2)))
        elif card in {"CE", "EN", "RP"}:
            continue
        elif card == "GW" and len(fields) >= 10:
            wires.append(
                Wire(
                    int(fields[1]),
                    Point3D(float(fields[3]), float(fields[4]), float(fields[5])),
                    Point3D(float(fields[6]), float(fields[7]), float(fields[8])),
                    int(fields[2]),
                    float(fields[9]),
                    wire_labels.get(int(fields[1]), ""),
                )
            )
        elif card == "GE":
            continue
        elif card == "GN":
            kind = int(fields[1])
            if kind == -1:
                ground = Ground("free_space")
            elif kind == 1:
                ground = Ground("perfect")
            elif kind == 2 and len(fields) >= 7:
                ground = Ground("real", float(fields[5]), float(fields[6]))
            else:
                unsupported.add(card)
        elif card == "EX" and len(fields) >= 7 and int(fields[1]) == 0:
            excitations.append(Excitation(int(fields[2]), int(fields[3]), float(fields[5]), float(fields[6])))
        elif card == "LD" and len(fields) >= 8 and int(fields[1]) == 0:
            loads.append(WireLoad(int(fields[2]), int(fields[3]), int(fields[4]), float(fields[5]), float(fields[6]), float(fields[7])))
        elif card == "FR" and len(fields) >= 7 and int(fields[1]) == 0:
            steps = int(fields[2])
            start = round(float(fields[5]) * 1e6)
            step = float(fields[6]) * 1e6
            frequency = FrequencySweep(start, round(start + max(0, steps - 1) * step), steps)
        else:
            unsupported.add(card)
    if unsupported:
        raise ValueError("Unsupported NEC2 cards in editable subset: " + ", ".join(sorted(unsupported)))
    model = AntennaModel(parsed_name, tuple(wires), tuple(excitations), tuple(loads), ground, frequency, orientation)
    errors = [issue.message for issue in model.validate() if issue.severity == "error"]
    if errors:
        raise ValueError("Invalid NEC model: " + "; ".join(errors))
    return model


def model_limits() -> tuple[str, ...]:
    return (
        "Wire-only NEC2 geometry (GW); no patches, buildings, or volumetric solids.",
        "Voltage sources (EX 0), series RLC loads (LD 0), and free/perfect/real ground.",
        "No real coax/feed-line model, terrain profile, optimization engine, or NEC4 extensions.",
    )


def _near(left: Point3D, right: Point3D, tolerance: float = 1e-6) -> bool:
    return sqrt((left.x_m - right.x_m) ** 2 + (left.y_m - right.y_m) ** 2 + (left.z_m - right.z_m) ** 2) <= tolerance


def _segments_cross_approximately(left: Wire, right: Wire) -> bool:
    # Cheap bounding-box warning only. NEC connectivity is endpoint-based; the
    # warning deliberately errs on the side of asking the operator to inspect.
    def bounds(wire: Wire, axis: str) -> tuple[float, float]:
        values = (getattr(wire.start, axis), getattr(wire.end, axis))
        return min(values), max(values)

    return all(
        max(bounds(left, axis)[0], bounds(right, axis)[0])
        <= min(bounds(left, axis)[1], bounds(right, axis)[1])
        for axis in ("x_m", "y_m", "z_m")
    )
