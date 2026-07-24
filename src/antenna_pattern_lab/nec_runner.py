from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from math import sqrt
import os
from pathlib import Path
import re
import subprocess
import tempfile
import threading
import time

from .antenna_model import AntennaModel
from .dependencies import detect_opennec


RUN_SCHEMA = "apl-nec-run/1"


class NecRunError(RuntimeError):
    pass


class NecRunCancelled(NecRunError):
    pass


@dataclass(frozen=True, slots=True)
class ImpedancePoint:
    frequency_hz: int
    resistance_ohm: float
    reactance_ohm: float
    swr_50: float


@dataclass(frozen=True, slots=True)
class RadiationSample:
    frequency_hz: int
    theta_deg: float
    phi_deg: float
    gain_db: float


@dataclass(frozen=True, slots=True)
class CurrentSample:
    frequency_hz: int
    wire_tag: int
    segment: int
    magnitude_a: float
    phase_deg: float


@dataclass(frozen=True, slots=True)
class NecRunResult:
    model_sha256: str
    engine_path: str
    engine_version: str
    command: tuple[str, ...]
    started_at: datetime
    duration_seconds: float
    input_sha256: str
    output_sha256: str
    impedance: tuple[ImpedancePoint, ...]
    radiation: tuple[RadiationSample, ...]
    currents: tuple[CurrentSample, ...]
    output_text: str
    schema: str = RUN_SCHEMA

    def canonical_dict(self, *, include_output: bool = True) -> dict[str, object]:
        raw = asdict(self)
        raw["started_at"] = self.started_at.isoformat()
        if not include_output:
            raw.pop("output_text", None)
        return raw

    def canonical_json(self) -> str:
        return json.dumps(self.canonical_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_json(cls, payload: str) -> "NecRunResult":
        raw = json.loads(payload)
        if raw.get("schema") != RUN_SCHEMA:
            raise ValueError(f"Unsupported NEC run schema: {raw.get('schema')!r}")
        raw["command"] = tuple(raw["command"])
        raw["started_at"] = datetime.fromisoformat(raw["started_at"])
        raw["impedance"] = tuple(ImpedancePoint(**item) for item in raw["impedance"])
        raw["radiation"] = tuple(RadiationSample(**item) for item in raw["radiation"])
        raw["currents"] = tuple(CurrentSample(**item) for item in raw["currents"])
        return cls(**raw)

    @property
    def frequencies_hz(self) -> tuple[int, ...]:
        return tuple(dict.fromkeys(point.frequency_hz for point in self.impedance))

    def radiation_at(self, frequency_hz: int | None = None) -> tuple[RadiationSample, ...]:
        target = frequency_hz or (self.frequencies_hz[0] if self.frequencies_hz else None)
        return tuple(item for item in self.radiation if target is None or item.frequency_hz == target)


def select_azimuth_cut(
    samples: tuple[RadiationSample, ...] | list[RadiationSample],
) -> tuple[float | None, tuple[RadiationSample, ...]]:
    """Choose the azimuth plane containing the run's absolute peak gain.

    A ground model has zero far-field gain exactly on the horizon
    (``theta=90°``), so treating the horizon as the universal azimuth cut would
    discard otherwise valid patterns. The peak-elevation plane is explicit and
    reproducible for each frequency.
    """
    usable = [item for item in samples if item.gain_db > -900]
    if not usable:
        return None, ()
    peak = max(usable, key=lambda item: item.gain_db)
    theta = peak.theta_deg
    rows = tuple(
        sorted(
            (item for item in usable if abs(item.theta_deg - theta) <= 0.2),
            key=lambda item: item.phi_deg,
        )
    )
    return theta, rows


def run_opennec(
    model: AntennaModel,
    *,
    executable: str | Path | None = None,
    cancel_event: threading.Event | None = None,
    timeout_seconds: float = 180.0,
) -> NecRunResult:
    path = Path(executable) if executable else detect_opennec()
    if path is None or not path.is_file():
        raise NecRunError("OpenNEC is not installed or could not be detected.")
    deck = model.to_nec()
    input_digest = hashlib.sha256(deck.encode("utf-8")).hexdigest()
    version = opennec_version(path)
    started = datetime.now(timezone.utc)
    monotonic_started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="apl-opennec-") as raw_directory:
        directory = Path(raw_directory)
        input_path = directory / "model.nec"
        output_path = directory / "model.out"
        input_path.write_text(deck, encoding="ascii")
        command = (str(path), "-f", "original", "-o", output_path.name, input_path.name)
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        process = subprocess.Popen(
            command,
            cwd=directory,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creation_flags,
        )
        while process.poll() is None:
            if cancel_event is not None and cancel_event.is_set():
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                raise NecRunCancelled("OpenNEC calculation was cancelled.")
            if time.monotonic() - monotonic_started > timeout_seconds:
                process.kill()
                raise NecRunError(f"OpenNEC exceeded the {timeout_seconds:.0f} s timeout.")
            time.sleep(0.05)
        stdout, stderr = process.communicate()
        if process.returncode:
            detail = (stderr or stdout).strip()
            raise NecRunError(f"OpenNEC failed with exit code {process.returncode}: {detail[:1000]}")
        if output_path.exists():
            output = output_path.read_text(encoding="utf-8", errors="replace")
        else:
            output = stdout
        if not output.strip():
            raise NecRunError("OpenNEC produced no readable output.")
    impedance, radiation, currents = parse_opennec_result(output)
    if not impedance and not radiation:
        raise NecRunError("OpenNEC output contains neither impedance nor radiation results.")
    return NecRunResult(
        model.sha256,
        str(path.resolve()),
        version,
        command,
        started,
        time.monotonic() - monotonic_started,
        input_digest,
        hashlib.sha256(output.encode("utf-8")).hexdigest(),
        impedance,
        radiation,
        currents,
        output,
    )


def opennec_version(executable: str | Path) -> str:
    for argument in ("--version", "-v"):
        try:
            result = subprocess.run(
                (str(executable), argument),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=5,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        value = (result.stdout or result.stderr).strip().splitlines()
        if value:
            return value[0][:160]
    return "unknown"


def parse_opennec_result(text: str) -> tuple[tuple[ImpedancePoint, ...], tuple[RadiationSample, ...], tuple[CurrentSample, ...]]:
    frequencies: list[int] = []
    current_frequency = 0
    impedance: list[ImpedancePoint] = []
    radiation: list[RadiationSample] = []
    currents: list[CurrentSample] = []
    section = ""
    for line in text.splitlines():
        upper = line.upper()
        frequency_match = re.search(
            r"FREQUENCY\s*(?:=|:)?\s*"
            r"([-+]?\d+(?:\.\d+)?(?:E[-+]?\d+)?)\s*(MHZ|KHZ|HZ)?",
            upper,
        )
        if frequency_match:
            value = float(frequency_match.group(1))
            multiplier = {"HZ": 1, "KHZ": 1_000, "MHZ": 1_000_000}.get(frequency_match.group(2) or "MHZ", 1_000_000)
            current_frequency = round(value * multiplier)
            frequencies.append(current_frequency)
        if "ANTENNA INPUT PARAMETERS" in upper or "INPUT IMPEDANCE" in upper:
            section = "impedance"
            continue
        if "RADIATION PATTERNS" in upper:
            section = "radiation"
            continue
        if "CURRENTS AND LOCATION" in upper or "STRUCTURE CURRENTS" in upper:
            section = "currents"
            continue
        if section == "radiation" and any(
            marker in upper
            for marker in (
                "AVERAGE POWER GAIN",
                "NORMALIZED RECEIVING PATTERN",
                "DATA CARD NO.",
                "RUN TIME",
            )
        ):
            section = ""
            continue
        values = _numbers(line)
        if section == "radiation" and len(values) >= 5:
            theta, phi, gain = values[0], values[1], values[4]
            if -0.01 <= theta <= 180.01 and -0.01 <= phi <= 360.01 and gain > -900:
                radiation.append(RadiationSample(current_frequency, theta, phi % 360.0, gain))
        elif section == "impedance" and len(values) >= 2:
            # Normal NEC prints tag/segment followed by R and X; some frontends
            # print frequency, R and X. Recognize both without accepting headers.
            candidate = None
            if len(values) >= 8 and _integerish(values[0]) and _integerish(values[1]):
                # Normal NEC columns are tag, segment, voltage R/I, current
                # R/I, impedance R/X, admittance R/I, power.
                candidate = (values[6], values[7])
            elif len(values) >= 3 and current_frequency and abs(values[0] - current_frequency / 1e6) < 1:
                candidate = (values[1], values[2])
            if candidate is not None and all(abs(item) < 1e12 for item in candidate):
                resistance, reactance = candidate
                impedance.append(ImpedancePoint(current_frequency, resistance, reactance, _swr(resistance, reactance)))
                section = ""
        elif section == "currents" and len(values) >= 10 and _integerish(values[0]) and _integerish(values[1]):
            # Normal NEC structure-current rows start with SEG then TAG and
            # end with magnitude and phase.
            magnitude, phase = values[8], values[9]
            if magnitude >= 0 and abs(phase) <= 360:
                currents.append(CurrentSample(current_frequency, int(values[1]), int(values[0]), magnitude, phase))
    # Deduplicate parser overlap while preserving solver order.
    impedance = list(dict.fromkeys(impedance))
    radiation = list(dict.fromkeys(radiation))
    currents = list(dict.fromkeys(currents))
    return tuple(impedance), tuple(radiation), tuple(currents)


def _numbers(line: str) -> list[float]:
    values = re.findall(r"(?<![A-Za-z])[-+]?(?:\d+\.\d*|\d*\.\d+|\d+)(?:[Ee][-+]?\d+)?", line)
    try:
        return [float(value) for value in values]
    except ValueError:
        return []


def _integerish(value: float) -> bool:
    return abs(value - round(value)) < 1e-8


def _swr(resistance: float, reactance: float, reference: float = 50.0) -> float:
    denominator = (resistance + reference) ** 2 + reactance**2
    if denominator <= 0:
        return float("inf")
    gamma = sqrt(((resistance - reference) ** 2 + reactance**2) / denominator)
    return float("inf") if gamma >= 1 else (1 + gamma) / (1 - gamma)
