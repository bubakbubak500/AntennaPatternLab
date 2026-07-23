from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import mimetypes
import os
from pathlib import Path
import shutil
import sqlite3
from typing import Iterable

from .campaigns import CampaignAttachment, CampaignLogEntry, MeasurementCampaign
from .domain import Spot
from .experiments import TxSessionSummary
from .exposure import ActivityWindow, ExposureObservation
from .profiles import AntennaProfile


class DatabaseMigrationError(RuntimeError):
    pass


class SpotRepository:
    MAX_ATTACHMENT_BYTES = 50 * 1024 * 1024
    SCHEMA_VERSION = 2
    BACKUP_RETENTION = 5

    def __init__(self, database_path: str | Path):
        self.path = Path(database_path)
        self.attachments_path = self.path.parent / f"{self.path.stem}-campaign-files"
        self.backups_path = self.path.parent / f"{self.path.stem}-backups"
        self.last_backup_path: Path | None = None
        self.migration_performed = False
        self.path.parent.mkdir(parents=True, exist_ok=True)
        migration_required = self._prepare_migration()
        self.initialize()
        self.migration_performed = migration_required

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS spots (
                    id INTEGER PRIMARY KEY,
                    source_key TEXT NOT NULL UNIQUE,
                    sequence INTEGER,
                    frequency_hz INTEGER NOT NULL,
                    mode TEXT NOT NULL,
                    snr_db INTEGER NOT NULL,
                    observed_at TEXT NOT NULL,
                    tx_call TEXT NOT NULL,
                    tx_grid TEXT NOT NULL,
                    rx_call TEXT NOT NULL,
                    rx_grid TEXT NOT NULL,
                    band TEXT NOT NULL
                )
                """
            )
            columns = {
                row[1] for row in connection.execute("PRAGMA table_info(spots)").fetchall()
            }
            if "tx_session_id" not in columns:
                connection.execute("ALTER TABLE spots ADD COLUMN tx_session_id INTEGER")
            if "campaign_id" not in columns:
                connection.execute("ALTER TABLE spots ADD COLUMN campaign_id INTEGER")
            if "source" not in columns:
                connection.execute(
                    "ALTER TABLE spots ADD COLUMN source TEXT NOT NULL "
                    "DEFAULT 'pskreporter'"
                )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS measurement_campaigns (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    objective TEXT NOT NULL DEFAULT '',
                    tx_call TEXT NOT NULL,
                    tx_grid TEXT NOT NULL,
                    band TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    antenna_profile_id INTEGER,
                    notes TEXT NOT NULL DEFAULT '',
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    target_spots INTEGER NOT NULL DEFAULT 100,
                    target_receivers INTEGER NOT NULL DEFAULT 10,
                    target_sectors INTEGER NOT NULL DEFAULT 8,
                    target_time_blocks INTEGER NOT NULL DEFAULT 6,
                    created_at TEXT NOT NULL
                )
                """
            )
            campaign_columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(measurement_campaigns)"
                ).fetchall()
            }
            for column, definition in (
                ("target_spots", "INTEGER NOT NULL DEFAULT 100"),
                ("target_receivers", "INTEGER NOT NULL DEFAULT 10"),
                ("target_sectors", "INTEGER NOT NULL DEFAULT 8"),
                ("target_time_blocks", "INTEGER NOT NULL DEFAULT 6"),
            ):
                if column not in campaign_columns:
                    connection.execute(
                        f"ALTER TABLE measurement_campaigns "
                        f"ADD COLUMN {column} {definition}"
                    )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS campaign_log_entries (
                    id INTEGER PRIMARY KEY,
                    campaign_id INTEGER NOT NULL,
                    recorded_at TEXT NOT NULL,
                    category TEXT NOT NULL,
                    text TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS campaign_log_campaign_idx "
                "ON campaign_log_entries(campaign_id, recorded_at DESC)"
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS campaign_attachments (
                    id INTEGER PRIMARY KEY,
                    campaign_id INTEGER NOT NULL,
                    original_name TEXT NOT NULL,
                    relative_path TEXT NOT NULL,
                    media_type TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    sha256 TEXT NOT NULL,
                    added_at TEXT NOT NULL,
                    notes TEXT NOT NULL DEFAULT '',
                    UNIQUE(campaign_id, sha256)
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS campaign_attachment_campaign_idx "
                "ON campaign_attachments(campaign_id, added_at DESC)"
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS antenna_profiles (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    antenna_type TEXT NOT NULL DEFAULT '',
                    apex_height_m REAL,
                    end_height_m REAL,
                    orientation_deg REAL,
                    power_w REAL,
                    tuner_enabled INTEGER NOT NULL DEFAULT 0,
                    wire_length_m REAL,
                    radial_count INTEGER,
                    radial_length_m REAL,
                    element_count INTEGER,
                    boom_length_m REAL,
                    transformer_ratio TEXT NOT NULL DEFAULT '',
                    notes TEXT NOT NULL DEFAULT '',
                    archived INTEGER NOT NULL DEFAULT 0,
                    revision INTEGER NOT NULL DEFAULT 1,
                    predecessor_id INTEGER,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            profile_columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(antenna_profiles)").fetchall()
            }
            for column, definition in (
                ("wire_length_m", "REAL"),
                ("radial_count", "INTEGER"),
                ("radial_length_m", "REAL"),
                ("element_count", "INTEGER"),
                ("boom_length_m", "REAL"),
                ("transformer_ratio", "TEXT NOT NULL DEFAULT ''"),
                ("revision", "INTEGER NOT NULL DEFAULT 1"),
                ("predecessor_id", "INTEGER"),
            ):
                if column not in profile_columns:
                    connection.execute(
                        f"ALTER TABLE antenna_profiles ADD COLUMN {column} {definition}"
                    )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS tx_sessions (
                    id INTEGER PRIMARY KEY,
                    instance_id TEXT NOT NULL,
                    de_call TEXT NOT NULL,
                    de_grid TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    dial_frequency_hz INTEGER NOT NULL,
                    tx_frequency_hz INTEGER NOT NULL,
                    tx_message TEXT NOT NULL,
                    configuration_name TEXT NOT NULL,
                    antenna_profile_id INTEGER,
                    rig_frequency_hz INTEGER,
                    rig_mode TEXT,
                    rig_ptt INTEGER,
                    started_at TEXT NOT NULL,
                    ended_at TEXT
                )
                """
            )
            session_columns = {
                row[1] for row in connection.execute("PRAGMA table_info(tx_sessions)").fetchall()
            }
            if "antenna_profile_id" not in session_columns:
                connection.execute(
                    "ALTER TABLE tx_sessions ADD COLUMN antenna_profile_id INTEGER"
                )
            if "campaign_id" not in session_columns:
                connection.execute(
                    "ALTER TABLE tx_sessions ADD COLUMN campaign_id INTEGER"
                )
            for column, sql_type in (
                ("rig_frequency_hz", "INTEGER"),
                ("rig_mode", "TEXT"),
                ("rig_ptt", "INTEGER"),
                ("rig_power_fraction", "REAL"),
                ("rig_swr", "REAL"),
                ("rotator_start_azimuth_deg", "REAL"),
                ("rotator_start_elevation_deg", "REAL"),
                ("rotator_end_azimuth_deg", "REAL"),
                ("rotator_end_elevation_deg", "REAL"),
                ("rotator_max_deviation_deg", "REAL"),
            ):
                if column not in session_columns:
                    connection.execute(
                        f"ALTER TABLE tx_sessions ADD COLUMN {column} {sql_type}"
                    )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS tx_sessions_match_idx "
                "ON tx_sessions(de_call, mode, started_at, ended_at)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS spots_filter_idx "
                "ON spots(tx_call, band, mode, observed_at DESC)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS spots_campaign_idx "
                "ON spots(campaign_id, observed_at DESC)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS tx_sessions_campaign_idx "
                "ON tx_sessions(campaign_id, started_at DESC)"
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS receiver_activity (
                    receiver_call TEXT NOT NULL,
                    receiver_grid TEXT NOT NULL,
                    band TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    window_start TEXT NOT NULL,
                    report_count INTEGER NOT NULL DEFAULT 1,
                    PRIMARY KEY(receiver_call, band, mode, window_start)
                )
                """
            )
            connection.execute(f"PRAGMA user_version = {self.SCHEMA_VERSION}")

    @property
    def schema_version(self) -> int:
        if not self.path.exists():
            return 0
        connection = sqlite3.connect(self.path, timeout=10)
        try:
            return int(connection.execute("PRAGMA user_version").fetchone()[0])
        finally:
            connection.close()

    def integrity_status(self) -> str:
        if not self.path.exists():
            return "missing"
        connection = None
        try:
            connection = sqlite3.connect(self.path, timeout=10)
            rows = connection.execute("PRAGMA quick_check").fetchall()
        except sqlite3.Error as exc:
            return f"error: {exc}"
        finally:
            if connection is not None:
                connection.close()
        messages = [str(row[0]) for row in rows]
        return "ok" if messages == ["ok"] else "; ".join(messages)

    def list_database_backups(self) -> list[Path]:
        if not self.backups_path.exists():
            return []
        return sorted(
            self.backups_path.glob(f"{self.path.stem}-pre-schema-*.sqlite3"),
            key=lambda item: item.name,
            reverse=True,
        )

    def _prepare_migration(self) -> bool:
        if not self.path.exists() or self.path.stat().st_size == 0:
            return False
        connection = None
        try:
            uri = self.path.resolve().as_uri() + "?mode=ro"
            connection = sqlite3.connect(uri, uri=True, timeout=10)
            old_version = int(
                connection.execute("PRAGMA user_version").fetchone()[0]
            )
            integrity = [
                str(row[0])
                for row in connection.execute("PRAGMA quick_check").fetchall()
            ]
        except (OSError, sqlite3.Error) as exc:
            raise DatabaseMigrationError(
                f"Database cannot be checked before migration: {exc}"
            ) from exc
        finally:
            if connection is not None:
                connection.close()
        if integrity != ["ok"]:
            raise DatabaseMigrationError(
                "Database integrity check failed before migration: "
                + "; ".join(integrity)
            )
        if old_version > self.SCHEMA_VERSION:
            raise DatabaseMigrationError(
                f"Database schema {old_version} is newer than supported "
                f"schema {self.SCHEMA_VERSION}."
            )
        if old_version == self.SCHEMA_VERSION:
            return False
        self.last_backup_path = self._create_pre_migration_backup(old_version)
        self._prune_database_backups()
        return True

    def _create_pre_migration_backup(self, old_version: int) -> Path:
        self.backups_path.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        target = self.backups_path / (
            f"{self.path.stem}-pre-schema-v{old_version}-to-v"
            f"{self.SCHEMA_VERSION}-{timestamp}.sqlite3"
        )
        temporary = target.with_suffix(target.suffix + ".part")
        source = destination = verification = None
        try:
            source = sqlite3.connect(self.path, timeout=10)
            destination = sqlite3.connect(temporary, timeout=10)
            source.backup(destination)
            destination.close()
            destination = None
            source.close()
            source = None
            verification = sqlite3.connect(temporary, timeout=10)
            result = [
                str(row[0])
                for row in verification.execute("PRAGMA quick_check").fetchall()
            ]
            verification.close()
            verification = None
            if result != ["ok"]:
                raise DatabaseMigrationError(
                    "Backup integrity check failed: " + "; ".join(result)
                )
            os.replace(temporary, target)
            return target
        except (OSError, sqlite3.Error) as exc:
            raise DatabaseMigrationError(
                f"Pre-migration backup failed: {exc}"
            ) from exc
        finally:
            for connection in (verification, destination, source):
                if connection is not None:
                    connection.close()
            if temporary.exists():
                try:
                    temporary.unlink()
                except OSError:
                    pass

    def _prune_database_backups(self) -> None:
        for stale in self.list_database_backups()[self.BACKUP_RETENTION :]:
            try:
                stale.unlink()
            except OSError:
                # Retention failure must not invalidate a verified new backup.
                pass

    def add(self, spot: Spot) -> bool:
        with self._connect() as connection:
            tx_session_id = self._match_tx_session(connection, spot)
            campaign_id = self._match_campaign(connection, spot, tx_session_id)
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO spots (
                    source_key, sequence, frequency_hz, mode, snr_db, observed_at,
                    tx_call, tx_grid, rx_call, rx_grid, band, tx_session_id,
                    campaign_id, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    spot.source_key,
                    spot.sequence,
                    spot.frequency_hz,
                    spot.mode,
                    spot.snr_db,
                    spot.observed_at.isoformat(),
                    spot.tx_call,
                    spot.tx_grid,
                    spot.rx_call,
                    spot.rx_grid,
                    spot.band,
                    tx_session_id,
                    campaign_id,
                    spot.source,
                ),
            )
            return cursor.rowcount == 1

    def add_many(self, spots: Iterable[Spot]) -> int:
        return sum(self.add(spot) for spot in spots)

    def list_spots(
        self,
        *,
        tx_call: str = "",
        band: str = "",
        mode: str = "",
        source: str = "",
        campaign_id: int | None = None,
        limit: int = 5000,
    ) -> list[Spot]:
        clauses, parameters = [], []
        if tx_call:
            clauses.append("tx_call = ?")
            parameters.append(tx_call.upper())
        if band and band != "+":
            clauses.append("band = ?")
            parameters.append(band.lower())
        if mode and mode != "+":
            clauses.append("mode = ?")
            parameters.append(mode.upper())
        if source and source != "all":
            clauses.append("source = ?")
            parameters.append(source.lower())
        if campaign_id is not None:
            clauses.append("campaign_id = ?")
            parameters.append(campaign_id)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        parameters.append(limit)
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM spots{where} ORDER BY observed_at DESC LIMIT ?", parameters
            ).fetchall()
        return [_row_to_spot(row) for row in rows]

    def list_spots_for_profile(
        self,
        profile_id: int,
        *,
        band: str = "",
        mode: str = "",
        limit: int = 20_000,
    ) -> list[Spot]:
        clauses = ["t.antenna_profile_id = ?"]
        parameters: list[object] = [profile_id]
        if band and band != "+":
            clauses.append("s.band = ?")
            parameters.append(band.lower())
        if mode and mode != "+":
            clauses.append("s.mode = ?")
            parameters.append(mode.upper())
        parameters.append(limit)
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT s.* FROM spots s
                JOIN tx_sessions t ON t.id = s.tx_session_id
                WHERE {' AND '.join(clauses)}
                ORDER BY s.observed_at ASC LIMIT ?
                """,
                parameters,
            ).fetchall()
        return [_row_to_spot(row) for row in rows]

    def start_campaign(self, campaign: MeasurementCampaign) -> MeasurementCampaign:
        campaign = campaign.validated()
        if campaign.id is not None or campaign.ended_at is not None:
            raise ValueError("A new campaign must be active and have no ID.")
        with self._connect() as connection:
            active = connection.execute(
                "SELECT id FROM measurement_campaigns WHERE ended_at IS NULL LIMIT 1"
            ).fetchone()
            if active is not None:
                raise ValueError("Another measurement campaign is already active.")
            cursor = connection.execute(
                """
                INSERT INTO measurement_campaigns (
                    name, objective, tx_call, tx_grid, band, mode,
                    antenna_profile_id, notes, started_at, ended_at,
                    target_spots, target_receivers, target_sectors,
                    target_time_blocks, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?)
                """,
                (
                    campaign.name,
                    campaign.objective,
                    campaign.tx_call,
                    campaign.tx_grid,
                    campaign.band,
                    campaign.mode,
                    campaign.antenna_profile_id,
                    campaign.notes,
                    campaign.started_at.isoformat(),
                    campaign.target_spots,
                    campaign.target_receivers,
                    campaign.target_sectors,
                    campaign.target_time_blocks,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            campaign_id = int(cursor.lastrowid)
        return self.get_campaign(campaign_id)

    def finish_campaign(
        self, campaign_id: int, ended_at: datetime | None = None
    ) -> MeasurementCampaign:
        finished_at = ended_at or datetime.now(timezone.utc)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT started_at, ended_at FROM measurement_campaigns WHERE id = ?",
                (campaign_id,),
            ).fetchone()
            if row is None:
                raise ValueError("Measurement campaign does not exist.")
            if row["ended_at"] is None:
                if finished_at < datetime.fromisoformat(row["started_at"]):
                    raise ValueError("Campaign end cannot precede its start.")
                connection.execute(
                    "UPDATE measurement_campaigns SET ended_at = ? WHERE id = ?",
                    (finished_at.isoformat(), campaign_id),
                )
        return self.get_campaign(campaign_id)

    def get_campaign(self, campaign_id: int) -> MeasurementCampaign:
        campaigns = self._campaign_query("WHERE c.id = ?", (campaign_id,))
        if not campaigns:
            raise ValueError("Measurement campaign does not exist.")
        return campaigns[0]

    def active_campaign(self) -> MeasurementCampaign | None:
        campaigns = self._campaign_query(
            "WHERE c.ended_at IS NULL ORDER BY c.started_at DESC LIMIT 1", ()
        )
        return campaigns[0] if campaigns else None

    def list_campaigns(self, limit: int = 500) -> list[MeasurementCampaign]:
        return self._campaign_query(
            "ORDER BY c.started_at DESC LIMIT ?", (limit,)
        )

    def _campaign_query(
        self, suffix: str, parameters: tuple[object, ...]
    ) -> list[MeasurementCampaign]:
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT
                    c.*,
                    COALESCE(p.name, '') AS antenna_profile_name,
                    (SELECT COUNT(*) FROM spots s WHERE s.campaign_id = c.id)
                        AS spot_count,
                    (SELECT COUNT(DISTINCT s.rx_call) FROM spots s
                        WHERE s.campaign_id = c.id) AS unique_receivers,
                    (SELECT COUNT(*) FROM tx_sessions t WHERE t.campaign_id = c.id)
                        AS tx_session_count
                FROM measurement_campaigns c
                LEFT JOIN antenna_profiles p ON p.id = c.antenna_profile_id
                {suffix}
                """,
                parameters,
            ).fetchall()
        return [_row_to_campaign(row) for row in rows]

    def campaign_id_for_spot(self, spot: Spot) -> int | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT campaign_id FROM spots WHERE source_key = ?",
                (spot.source_key,),
            ).fetchone()
        return None if row is None else row[0]

    def add_campaign_log_entry(self, entry: CampaignLogEntry) -> CampaignLogEntry:
        entry = entry.validated()
        if entry.id is not None:
            raise ValueError("A new campaign log entry must not have an ID.")
        with self._connect() as connection:
            campaign = connection.execute(
                "SELECT 1 FROM measurement_campaigns WHERE id = ?",
                (entry.campaign_id,),
            ).fetchone()
            if campaign is None:
                raise ValueError("Measurement campaign does not exist.")
            cursor = connection.execute(
                """
                INSERT INTO campaign_log_entries (
                    campaign_id, recorded_at, category, text
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    entry.campaign_id,
                    entry.recorded_at.isoformat(),
                    entry.category,
                    entry.text,
                ),
            )
            entry_id = int(cursor.lastrowid)
        return CampaignLogEntry(
            id=entry_id,
            campaign_id=entry.campaign_id,
            recorded_at=entry.recorded_at,
            category=entry.category,
            text=entry.text,
        )

    def list_campaign_log_entries(
        self, campaign_id: int, limit: int = 1000
    ) -> list[CampaignLogEntry]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM campaign_log_entries
                WHERE campaign_id = ?
                ORDER BY recorded_at DESC, id DESC
                LIMIT ?
                """,
                (campaign_id, limit),
            ).fetchall()
        return [_row_to_campaign_log_entry(row) for row in rows]

    def import_campaign_attachment(
        self,
        campaign_id: int,
        source_path: str | Path,
        notes: str = "",
    ) -> CampaignAttachment:
        source = Path(source_path)
        if not source.is_file():
            raise ValueError("Attachment source file does not exist.")
        size_bytes = source.stat().st_size
        if size_bytes > self.MAX_ATTACHMENT_BYTES:
            raise ValueError("Attachment exceeds the 50 MB limit.")
        with self._connect() as connection:
            campaign = connection.execute(
                "SELECT 1 FROM measurement_campaigns WHERE id = ?",
                (campaign_id,),
            ).fetchone()
        if campaign is None:
            raise ValueError("Measurement campaign does not exist.")

        digest = _file_sha256(source)
        with self._connect() as connection:
            existing = connection.execute(
                """
                SELECT * FROM campaign_attachments
                WHERE campaign_id = ? AND sha256 = ?
                """,
                (campaign_id, digest),
            ).fetchone()
        if existing is not None:
            attachment = _row_to_campaign_attachment(existing)
            if self.verify_campaign_attachment(attachment) != "ok":
                self._copy_verified_attachment(
                    source,
                    self.campaign_attachment_path(attachment),
                    digest,
                )
            return attachment

        suffix = source.suffix.lower()
        if not suffix or len(suffix) > 12 or not suffix[1:].isalnum():
            suffix = ".bin"
        relative_path = Path(f"campaign-{campaign_id}") / f"{digest}{suffix}"
        destination = self._safe_attachment_path(relative_path)
        self._copy_verified_attachment(source, destination, digest)

        media_type = mimetypes.guess_type(source.name)[0] or "application/octet-stream"
        added_at = datetime.now(timezone.utc)
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO campaign_attachments (
                    campaign_id, original_name, relative_path, media_type,
                    size_bytes, sha256, added_at, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    campaign_id,
                    source.name,
                    relative_path.as_posix(),
                    media_type,
                    size_bytes,
                    digest,
                    added_at.isoformat(),
                    notes.strip(),
                ),
            )
            attachment_id = int(cursor.lastrowid)
        return self.get_campaign_attachment(attachment_id)

    def get_campaign_attachment(self, attachment_id: int) -> CampaignAttachment:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM campaign_attachments WHERE id = ?",
                (attachment_id,),
            ).fetchone()
        if row is None:
            raise ValueError("Campaign attachment does not exist.")
        return _row_to_campaign_attachment(row)

    def list_campaign_attachments(
        self, campaign_id: int
    ) -> list[CampaignAttachment]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM campaign_attachments
                WHERE campaign_id = ?
                ORDER BY added_at DESC, id DESC
                """,
                (campaign_id,),
            ).fetchall()
        return [_row_to_campaign_attachment(row) for row in rows]

    def campaign_attachment_path(self, attachment: CampaignAttachment) -> Path:
        return self._safe_attachment_path(Path(attachment.relative_path))

    def verify_campaign_attachment(self, attachment: CampaignAttachment) -> str:
        try:
            path = self.campaign_attachment_path(attachment)
        except ValueError:
            return "unsafe_path"
        if not path.is_file():
            return "missing"
        if path.stat().st_size != attachment.size_bytes:
            return "size_mismatch"
        return "ok" if _file_sha256(path) == attachment.sha256 else "hash_mismatch"

    def _safe_attachment_path(self, relative_path: Path) -> Path:
        root = self.attachments_path.resolve()
        candidate = (root / relative_path).resolve()
        if not candidate.is_relative_to(root):
            raise ValueError("Attachment path leaves the managed storage.")
        return candidate

    @staticmethod
    def _copy_verified_attachment(
        source: Path, destination: Path, expected_sha256: str
    ) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".part")
        try:
            shutil.copyfile(source, temporary)
            if _file_sha256(temporary) != expected_sha256:
                raise OSError("Attachment copy verification failed.")
            os.replace(temporary, destination)
        finally:
            if temporary.exists():
                temporary.unlink()

    def known_receiver_fields(self, band: str = "", limit: int = 12) -> list[str]:
        clauses = ["length(rx_grid) >= 2"]
        parameters: list[object] = []
        if band and band != "+":
            clauses.append("band = ?")
            parameters.append(band.lower())
        parameters.append(limit)
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT upper(substr(rx_grid, 1, 2)) AS field, COUNT(*) AS reports
                FROM spots WHERE {' AND '.join(clauses)}
                GROUP BY field ORDER BY reports DESC LIMIT ?
                """,
                parameters,
            ).fetchall()
        return [row["field"] for row in rows]

    def record_receiver_activity(self, spot: Spot) -> None:
        timestamp = int(spot.observed_at.timestamp())
        window = datetime.fromtimestamp(timestamp - timestamp % 300, tz=timezone.utc)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO receiver_activity (
                    receiver_call, receiver_grid, band, mode, window_start, report_count
                ) VALUES (?, ?, ?, ?, ?, 1)
                ON CONFLICT(receiver_call, band, mode, window_start) DO UPDATE SET
                    receiver_grid = excluded.receiver_grid,
                    report_count = receiver_activity.report_count + 1
                """,
                (
                    spot.rx_call,
                    spot.rx_grid,
                    spot.band,
                    spot.mode,
                    window.isoformat(),
                ),
            )

    def list_receiver_activity(self, band: str = "", mode: str = "FT8") -> list[ActivityWindow]:
        clauses, parameters = [], []
        if band and band != "+":
            clauses.append("band = ?")
            parameters.append(band.lower())
        if mode and mode != "+":
            clauses.append("mode = ?")
            parameters.append(mode.upper())
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM receiver_activity{where} ORDER BY window_start",
                parameters,
            ).fetchall()
        return [
            ActivityWindow(
                receiver_call=row["receiver_call"],
                receiver_grid=row["receiver_grid"],
                band=row["band"],
                mode=row["mode"],
                window_start=datetime.fromisoformat(row["window_start"]),
                report_count=row["report_count"],
            )
            for row in rows
        ]

    def list_exposure_observations(
        self, *, profile_id: int | None = None, band: str = "", mode: str = "FT8"
    ) -> list[ExposureObservation]:
        sessions = self.list_tx_sessions(limit=20_000)
        activity = self.list_receiver_activity(band=band, mode=mode)
        with self._connect() as connection:
            detection_rows = connection.execute(
                """
                SELECT tx_session_id, rx_call FROM spots
                WHERE tx_session_id IS NOT NULL
                """
            ).fetchall()
        detections = {(row["tx_session_id"], row["rx_call"]) for row in detection_rows}
        observations = []
        for session in sessions:
            if profile_id is not None and session.profile_id != profile_id:
                continue
            if mode and mode != "+" and session.mode != mode.upper():
                continue
            if band and band != "+" and _band_for_frequency(session.frequency_hz) != band:
                continue
            session_end = session.ended_at or session.started_at
            lower = session.started_at - timedelta(minutes=5)
            upper = session_end + timedelta(minutes=5)
            seen_receivers = set()
            for window in activity:
                if window.receiver_call in seen_receivers:
                    continue
                window_end = window.window_start + timedelta(minutes=5)
                if window.window_start > upper or window_end < lower:
                    continue
                seen_receivers.add(window.receiver_call)
                observations.append(
                    ExposureObservation(
                        session_id=session.id,
                        profile_id=session.profile_id,
                        receiver_call=window.receiver_call,
                        receiver_grid=window.receiver_grid,
                        detected=(session.id, window.receiver_call) in detections,
                        observed_at=session.started_at,
                    )
                )
        return observations

    def count(self) -> int:
        with self._connect() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM spots").fetchone()[0])

    def clear(self) -> int:
        """Delete all stored spots and return the number of removed rows."""
        with self._connect() as connection:
            count = int(connection.execute("SELECT COUNT(*) FROM spots").fetchone()[0])
            connection.execute("DELETE FROM spots")
            connection.execute("DELETE FROM tx_sessions")
            return count

    def start_tx_session(
        self,
        *,
        instance_id: str,
        de_call: str,
        de_grid: str,
        mode: str,
        dial_frequency_hz: int,
        tx_frequency_hz: int,
        tx_message: str,
        configuration_name: str,
        antenna_profile_id: int | None,
        rig_frequency_hz: int | None,
        rig_mode: str | None,
        rig_ptt: int | None,
        started_at: datetime,
        rig_power_fraction: float | None = None,
        rig_swr: float | None = None,
        campaign_id: int | None = None,
        rotator_azimuth_deg: float | None = None,
        rotator_elevation_deg: float | None = None,
    ) -> int:
        with self._connect() as connection:
            if campaign_id is None:
                campaign_id = self._match_campaign_values(
                    connection,
                    de_call,
                    _band_for_frequency(tx_frequency_hz),
                    mode,
                    started_at,
                )
            cursor = connection.execute(
                """
                INSERT INTO tx_sessions (
                    instance_id, de_call, de_grid, mode, dial_frequency_hz,
                    tx_frequency_hz, tx_message, configuration_name, started_at
                    , antenna_profile_id, rig_frequency_hz, rig_mode, rig_ptt,
                    rig_power_fraction, rig_swr, campaign_id,
                    rotator_start_azimuth_deg, rotator_start_elevation_deg
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    instance_id,
                    de_call.upper(),
                    de_grid.upper(),
                    mode.upper(),
                    dial_frequency_hz,
                    tx_frequency_hz,
                    tx_message,
                    configuration_name,
                    started_at.isoformat(),
                    antenna_profile_id,
                    rig_frequency_hz,
                    rig_mode,
                    rig_ptt,
                    rig_power_fraction,
                    rig_swr,
                    campaign_id,
                    rotator_azimuth_deg,
                    rotator_elevation_deg,
                ),
            )
            return int(cursor.lastrowid)

    def finish_tx_session(
        self,
        session_id: int,
        ended_at: datetime,
        *,
        rotator_azimuth_deg: float | None = None,
        rotator_elevation_deg: float | None = None,
        rotator_max_deviation_deg: float | None = None,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE tx_sessions
                SET ended_at = ?,
                    rotator_end_azimuth_deg = ?,
                    rotator_end_elevation_deg = ?,
                    rotator_max_deviation_deg = ?
                WHERE id = ? AND ended_at IS NULL
                """,
                (
                    ended_at.isoformat(),
                    rotator_azimuth_deg,
                    rotator_elevation_deg,
                    rotator_max_deviation_deg,
                    session_id,
                ),
            )

    def tx_session_count(self) -> int:
        with self._connect() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM tx_sessions").fetchone()[0])

    def list_tx_sessions(self, limit: int = 1000) -> list[TxSessionSummary]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    t.id, t.started_at, t.ended_at, t.antenna_profile_id,
                    COALESCE(p.name, '') AS profile_name,
                    t.mode, t.tx_frequency_hz,
                    t.rotator_start_azimuth_deg,
                    t.rotator_start_elevation_deg,
                    t.rotator_end_azimuth_deg,
                    t.rotator_end_elevation_deg,
                    t.rotator_max_deviation_deg,
                    p.power_w,
                    COUNT(s.id) AS spot_count,
                    COUNT(DISTINCT s.rx_call) AS unique_receivers,
                    AVG(s.snr_db) AS average_snr_db
                FROM tx_sessions t
                LEFT JOIN antenna_profiles p ON p.id = t.antenna_profile_id
                LEFT JOIN spots s ON s.tx_session_id = t.id
                GROUP BY t.id
                ORDER BY t.started_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            TxSessionSummary(
                id=row["id"],
                started_at=datetime.fromisoformat(row["started_at"]),
                ended_at=(
                    datetime.fromisoformat(row["ended_at"]) if row["ended_at"] else None
                ),
                profile_id=row["antenna_profile_id"],
                profile_name=row["profile_name"],
                mode=row["mode"],
                frequency_hz=row["tx_frequency_hz"],
                rotator_start_azimuth_deg=row["rotator_start_azimuth_deg"],
                rotator_start_elevation_deg=row["rotator_start_elevation_deg"],
                rotator_end_azimuth_deg=row["rotator_end_azimuth_deg"],
                rotator_end_elevation_deg=row["rotator_end_elevation_deg"],
                rotator_max_deviation_deg=row["rotator_max_deviation_deg"],
                power_w=row["power_w"],
                spot_count=row["spot_count"],
                unique_receivers=row["unique_receivers"],
                average_snr_db=row["average_snr_db"],
            )
            for row in rows
        ]

    def tx_session_profile_id(self, session_id: int) -> int | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT antenna_profile_id FROM tx_sessions WHERE id = ?", (session_id,)
            ).fetchone()
        return None if row is None else row[0]

    def save_antenna_profile(self, profile: AntennaProfile) -> AntennaProfile:
        profile = profile.validated()
        now = datetime.now().astimezone().isoformat()
        with self._connect() as connection:
            if profile.id is None:
                cursor = connection.execute(
                    """
                    INSERT INTO antenna_profiles (
                        name, antenna_type, apex_height_m, end_height_m,
                        orientation_deg, power_w, tuner_enabled, notes,
                        wire_length_m, radial_count, radial_length_m,
                        element_count, boom_length_m, transformer_ratio,
                        archived, revision, predecessor_id, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        profile.name,
                        profile.antenna_type,
                        profile.apex_height_m,
                        profile.end_height_m,
                        profile.orientation_deg,
                        profile.power_w,
                        int(profile.tuner_enabled),
                        profile.notes,
                        profile.wire_length_m,
                        profile.radial_count,
                        profile.radial_length_m,
                        profile.element_count,
                        profile.boom_length_m,
                        profile.transformer_ratio,
                        int(profile.archived),
                        1,
                        None,
                        now,
                        now,
                    ),
                )
                profile_id = int(cursor.lastrowid)
            else:
                current_row = connection.execute(
                    "SELECT * FROM antenna_profiles WHERE id = ?",
                    (profile.id,),
                ).fetchone()
                if current_row is None:
                    raise ValueError("Antenna profile does not exist.")
                current = _row_to_profile(current_row)
                if current.archived:
                    raise ValueError("An archived antenna profile cannot be changed.")
                if _profile_content(current) == _profile_content(profile):
                    return current
                revision = current.revision + 1
                archived_name = _revisioned_profile_name(
                    connection, current.name, current.revision, current.id
                )
                connection.execute(
                    """
                    UPDATE antenna_profiles
                    SET name = ?, archived = 1, updated_at = ?
                    WHERE id = ?
                    """,
                    (archived_name, now, current.id),
                )
                cursor = connection.execute(
                    """
                    INSERT INTO antenna_profiles (
                        name, antenna_type, apex_height_m, end_height_m,
                        orientation_deg, power_w, tuner_enabled, notes,
                        wire_length_m, radial_count, radial_length_m,
                        element_count, boom_length_m, transformer_ratio,
                        archived, revision, predecessor_id, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?)
                    """,
                    (
                        profile.name,
                        profile.antenna_type,
                        profile.apex_height_m,
                        profile.end_height_m,
                        profile.orientation_deg,
                        profile.power_w,
                        int(profile.tuner_enabled),
                        profile.notes,
                        profile.wire_length_m,
                        profile.radial_count,
                        profile.radial_length_m,
                        profile.element_count,
                        profile.boom_length_m,
                        profile.transformer_ratio,
                        revision,
                        current.id,
                        now,
                        now,
                    ),
                )
                profile_id = int(cursor.lastrowid)
        return self.get_antenna_profile(profile_id)

    def get_antenna_profile(self, profile_id: int) -> AntennaProfile:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM antenna_profiles WHERE id = ?", (profile_id,)
            ).fetchone()
        if row is None:
            raise ValueError("Antenna profile does not exist.")
        return _row_to_profile(row)

    def list_antenna_profiles(self, include_archived: bool = False) -> list[AntennaProfile]:
        where = "" if include_archived else " WHERE archived = 0"
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM antenna_profiles{where} ORDER BY name COLLATE NOCASE"
            ).fetchall()
        return [_row_to_profile(row) for row in rows]

    def archive_antenna_profile(self, profile_id: int) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE antenna_profiles SET archived = 1, updated_at = ? WHERE id = ?",
                (datetime.now().astimezone().isoformat(), profile_id),
            )

    def spot_tx_session_id(self, spot: Spot) -> int | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT tx_session_id FROM spots WHERE source_key = ?", (spot.source_key,)
            ).fetchone()
        return None if row is None else row[0]

    @staticmethod
    def _match_tx_session(connection: sqlite3.Connection, spot: Spot) -> int | None:
        lower = (spot.observed_at - timedelta(seconds=10)).isoformat()
        upper = (spot.observed_at + timedelta(seconds=10)).isoformat()
        row = connection.execute(
            """
            SELECT id FROM tx_sessions
            WHERE de_call = ? AND mode = ?
              AND started_at <= ?
              AND (ended_at IS NULL OR ended_at >= ?)
              AND ABS(tx_frequency_hz - ?) <= 3000
            ORDER BY started_at DESC LIMIT 1
            """,
            (spot.tx_call, spot.mode, upper, lower, spot.frequency_hz),
        ).fetchone()
        return None if row is None else int(row[0])

    @classmethod
    def _match_campaign(
        cls,
        connection: sqlite3.Connection,
        spot: Spot,
        tx_session_id: int | None,
    ) -> int | None:
        if tx_session_id is not None:
            row = connection.execute(
                "SELECT campaign_id FROM tx_sessions WHERE id = ?",
                (tx_session_id,),
            ).fetchone()
            if row is not None and row["campaign_id"] is not None:
                return int(row["campaign_id"])
        return cls._match_campaign_values(
            connection,
            spot.tx_call,
            spot.band,
            spot.mode,
            spot.observed_at,
        )

    @staticmethod
    def _match_campaign_values(
        connection: sqlite3.Connection,
        tx_call: str,
        band: str,
        mode: str,
        observed_at: datetime,
    ) -> int | None:
        timestamp = observed_at.isoformat()
        row = connection.execute(
            """
            SELECT id FROM measurement_campaigns
            WHERE tx_call = ? AND band = ? AND mode = ?
              AND started_at <= ?
              AND (ended_at IS NULL OR ended_at >= ?)
            ORDER BY started_at DESC LIMIT 1
            """,
            (
                tx_call.strip().upper(),
                band.strip().lower(),
                mode.strip().upper(),
                timestamp,
                timestamp,
            ),
        ).fetchone()
        return None if row is None else int(row["id"])


def _row_to_spot(row: sqlite3.Row) -> Spot:
    return Spot(
        sequence=row["sequence"],
        frequency_hz=row["frequency_hz"],
        mode=row["mode"],
        snr_db=row["snr_db"],
        observed_at=datetime.fromisoformat(row["observed_at"]),
        tx_call=row["tx_call"],
        tx_grid=row["tx_grid"],
        rx_call=row["rx_call"],
        rx_grid=row["rx_grid"],
        band=row["band"],
        source=row["source"],
    )


def _row_to_campaign(row: sqlite3.Row) -> MeasurementCampaign:
    return MeasurementCampaign(
        id=row["id"],
        name=row["name"],
        objective=row["objective"],
        tx_call=row["tx_call"],
        tx_grid=row["tx_grid"],
        band=row["band"],
        mode=row["mode"],
        antenna_profile_id=row["antenna_profile_id"],
        antenna_profile_name=row["antenna_profile_name"],
        notes=row["notes"],
        started_at=datetime.fromisoformat(row["started_at"]),
        target_spots=row["target_spots"],
        target_receivers=row["target_receivers"],
        target_sectors=row["target_sectors"],
        target_time_blocks=row["target_time_blocks"],
        ended_at=(
            datetime.fromisoformat(row["ended_at"]) if row["ended_at"] else None
        ),
        spot_count=row["spot_count"],
        unique_receivers=row["unique_receivers"],
        tx_session_count=row["tx_session_count"],
    )


def _row_to_campaign_log_entry(row: sqlite3.Row) -> CampaignLogEntry:
    return CampaignLogEntry(
        id=row["id"],
        campaign_id=row["campaign_id"],
        recorded_at=datetime.fromisoformat(row["recorded_at"]),
        category=row["category"],
        text=row["text"],
    )


def _row_to_campaign_attachment(row: sqlite3.Row) -> CampaignAttachment:
    return CampaignAttachment(
        id=row["id"],
        campaign_id=row["campaign_id"],
        original_name=row["original_name"],
        relative_path=row["relative_path"],
        media_type=row["media_type"],
        size_bytes=row["size_bytes"],
        sha256=row["sha256"],
        added_at=datetime.fromisoformat(row["added_at"]),
        notes=row["notes"],
    )


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _row_to_profile(row: sqlite3.Row) -> AntennaProfile:
    return AntennaProfile(
        id=row["id"],
        name=row["name"],
        antenna_type=row["antenna_type"],
        apex_height_m=row["apex_height_m"],
        end_height_m=row["end_height_m"],
        orientation_deg=row["orientation_deg"],
        power_w=row["power_w"],
        tuner_enabled=bool(row["tuner_enabled"]),
        wire_length_m=row["wire_length_m"],
        radial_count=row["radial_count"],
        radial_length_m=row["radial_length_m"],
        element_count=row["element_count"],
        boom_length_m=row["boom_length_m"],
        transformer_ratio=row["transformer_ratio"],
        notes=row["notes"],
        archived=bool(row["archived"]),
        revision=row["revision"],
        predecessor_id=row["predecessor_id"],
    )


def _profile_content(profile: AntennaProfile) -> tuple[object, ...]:
    return (
        profile.name,
        profile.antenna_type,
        profile.apex_height_m,
        profile.end_height_m,
        profile.orientation_deg,
        profile.power_w,
        profile.tuner_enabled,
        profile.wire_length_m,
        profile.radial_count,
        profile.radial_length_m,
        profile.element_count,
        profile.boom_length_m,
        profile.transformer_ratio,
        profile.notes,
    )


def _revisioned_profile_name(
    connection: sqlite3.Connection,
    name: str,
    revision: int,
    profile_id: int,
) -> str:
    candidate = f"{name} [v{revision}]"
    collision = connection.execute(
        "SELECT 1 FROM antenna_profiles WHERE name = ? AND id != ?",
        (candidate, profile_id),
    ).fetchone()
    # The row ID suffix is only needed when a user already used the conventional
    # revision label as an unrelated profile name.
    return f"{candidate} #{profile_id}" if collision is not None else candidate


def _band_for_frequency(frequency_hz: int) -> str:
    ranges = {
        "80m": (3_500_000, 4_000_000),
        "40m": (7_000_000, 7_300_000),
        "30m": (10_100_000, 10_150_000),
        "20m": (14_000_000, 14_350_000),
        "17m": (18_068_000, 18_168_000),
        "15m": (21_000_000, 21_450_000),
        "12m": (24_890_000, 24_990_000),
        "10m": (28_000_000, 29_700_000),
    }
    for band, (low, high) in ranges.items():
        if low <= frequency_hz <= high:
            return band
    return ""
