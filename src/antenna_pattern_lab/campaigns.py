from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from .analysis import LocatedSpot
from .geo import maidenhead_to_latlon


@dataclass(frozen=True, slots=True)
class MeasurementCampaign:
    id: int | None
    name: str
    objective: str
    tx_call: str
    tx_grid: str
    band: str
    mode: str
    antenna_profile_id: int | None
    antenna_profile_name: str
    notes: str
    started_at: datetime
    target_spots: int = 100
    target_receivers: int = 10
    target_sectors: int = 8
    target_time_blocks: int = 6
    ended_at: datetime | None = None
    spot_count: int = 0
    unique_receivers: int = 0
    tx_session_count: int = 0

    def validated(self) -> "MeasurementCampaign":
        name = self.name.strip()
        if not name:
            raise ValueError("Campaign name is required.")
        if not self.tx_call.strip():
            raise ValueError("Campaign callsign is required.")
        if not self.tx_grid.strip():
            raise ValueError("Campaign TX grid is required.")
        if not self.band.strip() or not self.mode.strip():
            raise ValueError("Campaign band and mode are required.")
        if self.target_spots < 1:
            raise ValueError("Campaign spot target must be positive.")
        if self.target_receivers < 1:
            raise ValueError("Campaign receiver target must be positive.")
        if not 1 <= self.target_sectors <= 12:
            raise ValueError("Campaign sector target must be between 1 and 12.")
        if self.target_time_blocks < 1:
            raise ValueError("Campaign time-block target must be positive.")
        if self.ended_at is not None and self.ended_at < self.started_at:
            raise ValueError("Campaign end cannot precede its start.")
        return replace(
            self,
            name=name,
            objective=self.objective.strip(),
            tx_call=self.tx_call.strip().upper(),
            tx_grid=self.tx_grid.strip().upper(),
            band=self.band.strip().lower(),
            mode=self.mode.strip().upper(),
            notes=self.notes.strip(),
        )

    @property
    def active(self) -> bool:
        return self.ended_at is None

    @property
    def duration_seconds(self) -> float:
        end = self.ended_at or datetime.now(self.started_at.tzinfo)
        return max(0.0, (end - self.started_at).total_seconds())


@dataclass(frozen=True, slots=True)
class CampaignMetadataCheck:
    complete_count: int
    total_count: int
    missing: tuple[str, ...]

    @property
    def percent(self) -> int:
        return round(100 * self.complete_count / self.total_count)

    @property
    def complete(self) -> bool:
        return not self.missing


@dataclass(frozen=True, slots=True)
class CampaignProgress:
    spot_count: int
    unique_receivers: int
    supported_sector_count: int
    time_block_count: int
    met: tuple[str, ...]
    missing: tuple[str, ...]

    @property
    def complete(self) -> bool:
        return not self.missing

    @property
    def met_count(self) -> int:
        return len(self.met)


def assess_campaign_progress(
    campaign: MeasurementCampaign,
    located: list[LocatedSpot],
) -> CampaignProgress:
    receivers = len({item.spot.rx_call for item in located})
    time_blocks = len(
        {
            int(item.spot.observed_at.timestamp()) // (30 * 60)
            for item in located
        }
    )
    sectors: list[list[LocatedSpot]] = [[] for _ in range(12)]
    for item in located:
        sectors[min(int(item.bearing_deg // 30), 11)].append(item)
    supported_sectors = sum(
        len(items) >= 3 and len({item.spot.rx_call for item in items}) >= 2
        for items in sectors
    )
    checks = (
        ("spots", len(located) >= campaign.target_spots),
        ("receivers", receivers >= campaign.target_receivers),
        ("sectors", supported_sectors >= campaign.target_sectors),
        ("time_blocks", time_blocks >= campaign.target_time_blocks),
    )
    return CampaignProgress(
        spot_count=len(located),
        unique_receivers=receivers,
        supported_sector_count=supported_sectors,
        time_block_count=time_blocks,
        met=tuple(key for key, complete in checks if complete),
        missing=tuple(key for key, complete in checks if not complete),
    )


def assess_campaign_metadata(
    campaign: MeasurementCampaign,
    profile_power_w: float | None,
) -> CampaignMetadataCheck:
    try:
        maidenhead_to_latlon(campaign.tx_grid)
        grid_valid = True
    except ValueError:
        grid_valid = False
    checks = (
        ("name", bool(campaign.name.strip())),
        ("objective", bool(campaign.objective.strip())),
        ("callsign", bool(campaign.tx_call.strip())),
        ("grid", grid_valid),
        ("band", bool(campaign.band.strip())),
        ("mode", bool(campaign.mode.strip())),
        ("profile", campaign.antenna_profile_id is not None),
        ("power", profile_power_w is not None and profile_power_w > 0),
        ("conditions", bool(campaign.notes.strip())),
    )
    missing = tuple(key for key, complete in checks if not complete)
    return CampaignMetadataCheck(len(checks) - len(missing), len(checks), missing)


LOG_CATEGORIES = (
    "setup",
    "environment",
    "antenna_change",
    "power",
    "observation",
    "issue",
)


@dataclass(frozen=True, slots=True)
class CampaignLogEntry:
    id: int | None
    campaign_id: int
    recorded_at: datetime
    category: str
    text: str

    def validated(self) -> "CampaignLogEntry":
        category = self.category.strip().lower()
        if category not in LOG_CATEGORIES:
            raise ValueError("Unknown campaign log category.")
        text = self.text.strip()
        if not text:
            raise ValueError("Campaign log text is required.")
        if self.campaign_id < 1:
            raise ValueError("Campaign ID is required.")
        return replace(self, category=category, text=text)


@dataclass(frozen=True, slots=True)
class CampaignAttachment:
    id: int | None
    campaign_id: int
    original_name: str
    relative_path: str
    media_type: str
    size_bytes: int
    sha256: str
    added_at: datetime
    notes: str = ""

    def validated(self) -> "CampaignAttachment":
        original_name = self.original_name.strip()
        if not original_name:
            raise ValueError("Attachment name is required.")
        if self.campaign_id < 1:
            raise ValueError("Campaign ID is required.")
        if self.size_bytes < 0:
            raise ValueError("Attachment size cannot be negative.")
        digest = self.sha256.strip().lower()
        if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
            raise ValueError("Attachment SHA-256 is invalid.")
        return replace(
            self,
            original_name=original_name,
            media_type=self.media_type.strip() or "application/octet-stream",
            sha256=digest,
            notes=self.notes.strip(),
        )
