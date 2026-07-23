from __future__ import annotations

from dataclasses import dataclass
from math import cos, log10, pi, radians, sin
from statistics import median
from typing import Iterable

from .profiles import AntennaProfile, normalize_antenna_type

SPEED_OF_LIGHT_M_S = 299_792_458.0


@dataclass(frozen=True, slots=True)
class ModelPoint:
    bearing_deg: float
    relative_gain_db: float


@dataclass(frozen=True, slots=True)
class AzimuthModel:
    points: tuple[ModelPoint, ...]
    model_name: str
    assumptions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CalibrationPoint:
    bearing_deg: float
    measured_relative_db: float
    model_relative_db: float
    residual_db: float
    count: int


def calibrate_azimuth_model(
    model: AzimuthModel,
    located_spots: Iterable,
    sector_width_deg: int = 30,
    min_samples: int = 3,
) -> tuple[CalibrationPoint, ...]:
    """Compare relative model shape with profile-assigned empirical sectors."""
    if sector_width_deg <= 0 or 360 % sector_width_deg:
        raise ValueError("Sector width must divide 360.")
    buckets = [[] for _ in range(360 // sector_width_deg)]
    for item in located_spots:
        buckets[min(int(item.bearing_deg // sector_width_deg), len(buckets) - 1)].append(item)
    medians = [
        float(median(item.spot.snr_db for item in bucket)) if len(bucket) >= min_samples else None
        for bucket in buckets
    ]
    available = [value for value in medians if value is not None]
    if len(available) < 2:
        return ()
    measured_peak = max(available)
    result = []
    for index, (bucket, measured) in enumerate(zip(buckets, medians)):
        if measured is None:
            continue
        bearing = index * sector_width_deg + sector_width_deg / 2
        model_point = min(
            model.points,
            key=lambda point: abs(((point.bearing_deg - bearing + 180) % 360) - 180),
        )
        measured_relative = measured - measured_peak
        result.append(
            CalibrationPoint(
                bearing_deg=bearing,
                measured_relative_db=measured_relative,
                model_relative_db=model_point.relative_gain_db,
                residual_db=measured_relative - model_point.relative_gain_db,
                count=len(bucket),
            )
        )
    return tuple(result)


def theoretical_azimuth_model(
    profile: AntennaProfile, frequency_hz: int, step_deg: int = 5
) -> AzimuthModel | None:
    """Return a deliberately simplified free-space horizontal pattern.

    This model provides a geometric reference only. It does not model ground,
    terrain, feed line, losses, common-mode current, elevation angle, or ionosphere.
    """
    if frequency_hz <= 0:
        raise ValueError("Frequency must be positive.")
    if step_deg <= 0 or 360 % step_deg:
        raise ValueError("Angular step must be a positive divisor of 360.")
    antenna_type = normalize_antenna_type(profile.antenna_type)
    bearings = list(range(0, 360, step_deg))
    orientation = float(profile.orientation_deg or 0.0)
    wavelength = SPEED_OF_LIGHT_M_S / frequency_hz

    if antenna_type == "vertical":
        amplitudes = [1.0 for _ in bearings]
        name = "vertical"
        assumptions = ("ideal_symmetry", "no_elevation_radials")
    elif antenna_type in ("dipole", "efhw", "efrw", "inverted_v"):
        length = profile.wire_length_m or wavelength / 2.0
        electrical_half_length = pi * length / wavelength
        amplitudes = []
        for bearing in bearings:
            alpha = radians((bearing - orientation) % 360)
            denominator = abs(sin(alpha))
            if denominator < 1e-6:
                amplitude = 0.0
            else:
                amplitude = abs(
                    (cos(electrical_half_length * cos(alpha)) - cos(electrical_half_length))
                    / denominator
                )
            if antenna_type == "inverted_v":
                amplitude = 0.72 * amplitude + 0.28
            elif antenna_type == "efrw":
                # Unknown current distribution is represented by a broader floor.
                amplitude = 0.85 * amplitude + 0.15
            amplitudes.append(amplitude)
        name = "wire"
        assumptions = (
            "sinusoidal_current",
            "free_space_horizontal",
            "no_feed_common_mode",
        )
    elif antenna_type == "yagi":
        elements = max(2, int(profile.element_count or 3))
        exponent = 1.2 + elements / 3.0
        front_to_back_db = min(25.0, 6.0 + elements * 2.0)
        rear_floor = 10 ** (-front_to_back_db / 20.0)
        amplitudes = []
        for bearing in bearings:
            delta = radians((bearing - orientation) % 360)
            forward = max(0.0, (1.0 + cos(delta)) / 2.0) ** exponent
            amplitudes.append(rear_floor + (1.0 - rear_floor) * forward)
        name = "yagi"
        assumptions = (
            "ideal_phasing",
            "elements_control_shape",
            "no_boom_solution",
        )
    else:
        return None

    peak = max(amplitudes) or 1.0
    points = tuple(
        ModelPoint(float(bearing), max(-30.0, 20.0 * log10(max(amplitude / peak, 1e-6))))
        for bearing, amplitude in zip(bearings, amplitudes)
    )
    return AzimuthModel(
        points=points,
        model_name=name,
        assumptions=assumptions,
    )


def representative_frequency_hz(band: str, mode: str = "FT8") -> int:
    ft8 = {
        "80m": 3_573_000,
        "40m": 7_074_000,
        "30m": 10_136_000,
        "20m": 14_074_000,
        "17m": 18_100_000,
        "15m": 21_074_000,
        "12m": 24_915_000,
        "10m": 28_074_000,
    }
    wspr = {
        "80m": 3_568_600,
        "40m": 7_038_600,
        "30m": 10_138_700,
        "20m": 14_095_600,
        "17m": 18_104_600,
        "15m": 21_094_600,
        "12m": 24_924_600,
        "10m": 28_124_600,
    }
    table = wspr if mode.upper() == "WSPR" else ft8
    return table.get(band, table["20m"])
