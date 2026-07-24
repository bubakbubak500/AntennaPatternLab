from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from statistics import median
from typing import Callable, Sequence

from .analysis import LocatedSpot
from .antenna_model import AntennaModel
from .nec_runner import NecRunResult, RadiationSample, select_azimuth_cut
from .propagation_intelligence import PropagationFeatures, expected_snr


FIT_SCHEMA = "apl-nec-assisted-fit/1"


@dataclass(frozen=True, slots=True)
class FitCandidate:
    model_id: int
    run_id: int
    height_delta_m: float
    ground_kind: str
    model: AntennaModel
    result: NecRunResult


@dataclass(frozen=True, slots=True)
class AssistedFitResult:
    candidate_model_id: int
    candidate_run_id: int
    height_delta_m: float
    orientation_deg: float
    ground_kind: str
    train_blocks: int
    test_blocks: int
    train_reports: int
    test_reports: int
    train_median_absolute_error_db: float
    test_median_absolute_error_db: float
    baseline_test_median_absolute_error_db: float
    warnings: tuple[str, ...]
    schema: str = FIT_SCHEMA

    def canonical_json(self) -> str:
        return json.dumps(
            asdict(self),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )


def assisted_fit(
    spots: Sequence[LocatedSpot],
    feature_for_spot: Callable[[LocatedSpot], PropagationFeatures],
    candidates: Sequence[FitCandidate],
    *,
    orientation_step_deg: int = 10,
    block_minutes: int = 30,
) -> AssistedFitResult:
    """Select on earlier time blocks and report accuracy on untouched blocks.

    Height and ground are represented by independently solved candidates.
    Orientation is rotated analytically because NEC azimuth output is invariant
    to the global coordinate rotation. The theoretical baseline remains stored
    separately; this result only records the assisted candidate and holdout
    evidence.
    """
    if not candidates:
        raise ValueError("At least one solved height/ground candidate is required.")
    if orientation_step_deg <= 0 or 360 % orientation_step_deg:
        raise ValueError("Orientation step must be a positive divisor of 360.")
    blocks: dict[int, list[tuple[LocatedSpot, float]]] = {}
    for item in spots:
        block = int(item.spot.observed_at.timestamp()) // (block_minutes * 60)
        residual = item.spot.snr_db - expected_snr(feature_for_spot(item)).expected_snr_db
        blocks.setdefault(block, []).append((item, residual))
    ordered_blocks = sorted(blocks)
    if len(ordered_blocks) < 2:
        raise ValueError("Assisted fitting requires at least two independent time blocks.")
    test_count = max(1, round(len(ordered_blocks) * 0.3))
    train_ids = set(ordered_blocks[:-test_count])
    test_ids = set(ordered_blocks[-test_count:])
    train_rows = [row for block in ordered_blocks if block in train_ids for row in blocks[block]]
    test_rows = [row for block in ordered_blocks if block in test_ids for row in blocks[block]]
    if not train_rows or not test_rows:
        raise ValueError("Training and validation partitions must both contain reports.")

    scored: list[tuple[float, FitCandidate, float, float]] = []
    for candidate in candidates:
        pattern = _azimuth_pattern(candidate.result)
        if len(pattern) < 2:
            continue
        for orientation in range(0, 360, orientation_step_deg):
            intercept = median(
                residual - _gain_at(pattern, item.bearing_deg - orientation)
                for item, residual in train_rows
            )
            train_mae = _mae(train_rows, pattern, orientation, intercept)
            scored.append((train_mae, candidate, float(orientation), intercept))
    if not scored:
        raise ValueError("Candidates contain no usable theta=90° azimuth pattern.")
    train_mae, best, orientation, intercept = min(
        scored,
        key=lambda item: (item[0], item[1].run_id, item[2]),
    )
    pattern = _azimuth_pattern(best.result)
    test_mae = _mae(test_rows, pattern, orientation, intercept)
    null_intercept = median(residual for _item, residual in train_rows)
    baseline_test_mae = float(
        median(abs(residual - null_intercept) for _item, residual in test_rows)
    )
    warnings = []
    if len(test_ids) < 2:
        warnings.append("validation uses only one untouched time block")
    if test_mae >= baseline_test_mae:
        warnings.append("assisted model does not improve the untouched validation data")
    return AssistedFitResult(
        best.model_id,
        best.run_id,
        best.height_delta_m,
        orientation,
        best.ground_kind,
        len(train_ids),
        len(test_ids),
        len(train_rows),
        len(test_rows),
        train_mae,
        test_mae,
        baseline_test_mae,
        tuple(warnings),
    )


def _azimuth_pattern(result: NecRunResult) -> tuple[tuple[float, float], ...]:
    frequencies = result.frequencies_hz
    target = frequencies[len(frequencies) // 2] if frequencies else None
    rows = [
        item
        for item in result.radiation
        if target is None or item.frequency_hz == target
    ]
    _theta, rows = select_azimuth_cut(rows)
    by_phi: dict[float, float] = {}
    for row in rows:
        by_phi[row.phi_deg % 360.0] = max(
            row.gain_db,
            by_phi.get(row.phi_deg % 360.0, float("-inf")),
        )
    if not by_phi:
        return ()
    peak = max(by_phi.values())
    return tuple((angle, gain - peak) for angle, gain in sorted(by_phi.items()))


def _gain_at(pattern: Sequence[tuple[float, float]], bearing_deg: float) -> float:
    target = bearing_deg % 360.0
    ordered = sorted((angle % 360.0, gain) for angle, gain in pattern)
    for index, right in enumerate(ordered):
        if target <= right[0]:
            left = ordered[index - 1] if index else (ordered[-1][0] - 360.0, ordered[-1][1])
            target_value = target if index else target
            span = right[0] - left[0]
            fraction = 0.0 if span == 0 else (target_value - left[0]) / span
            return left[1] + fraction * (right[1] - left[1])
    left = ordered[-1]
    right = (ordered[0][0] + 360.0, ordered[0][1])
    fraction = (target - left[0]) / (right[0] - left[0])
    return left[1] + fraction * (right[1] - left[1])


def _mae(
    rows: Sequence[tuple[LocatedSpot, float]],
    pattern: Sequence[tuple[float, float]],
    orientation: float,
    intercept: float,
) -> float:
    return float(
        median(
            abs(
                residual
                - (intercept + _gain_at(pattern, item.bearing_deg - orientation))
            )
            for item, residual in rows
        )
    )


def _angular_distance(left: float, right: float) -> float:
    return abs((left - right + 180.0) % 360.0 - 180.0)
