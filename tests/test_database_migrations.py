import sqlite3

import pytest

from antenna_pattern_lab.storage import DatabaseMigrationError, SpotRepository


def _create_legacy_database(path) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            "CREATE TABLE legacy_marker (id INTEGER PRIMARY KEY, value TEXT)"
        )
        connection.execute(
            "INSERT INTO legacy_marker (value) VALUES ('preserve me')"
        )
        connection.commit()
    finally:
        connection.close()


def _set_user_version(path, version: int) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.execute(f"PRAGMA user_version = {version}")
        connection.commit()
    finally:
        connection.close()


def test_new_database_sets_schema_without_unnecessary_backup(tmp_path):
    repository = SpotRepository(tmp_path / "new.sqlite3")

    assert repository.schema_version == SpotRepository.SCHEMA_VERSION
    assert repository.integrity_status() == "ok"
    assert not repository.migration_performed
    assert repository.last_backup_path is None
    assert repository.list_database_backups() == []


def test_legacy_database_is_backed_up_verified_and_only_migrated_once(tmp_path):
    path = tmp_path / "legacy.sqlite3"
    _create_legacy_database(path)

    repository = SpotRepository(path)

    assert repository.migration_performed
    assert repository.last_backup_path is not None
    assert repository.last_backup_path.exists()
    assert repository.schema_version == SpotRepository.SCHEMA_VERSION
    backup = sqlite3.connect(repository.last_backup_path)
    try:
        assert backup.execute(
            "SELECT value FROM legacy_marker"
        ).fetchone()[0] == "preserve me"
        assert backup.execute("PRAGMA quick_check").fetchone()[0] == "ok"
        assert backup.execute("PRAGMA user_version").fetchone()[0] == 0
    finally:
        backup.close()

    reopened = SpotRepository(path)
    assert not reopened.migration_performed
    assert reopened.last_backup_path is None
    assert reopened.list_database_backups() == repository.list_database_backups()


def test_newer_schema_is_refused_without_modifying_database(tmp_path):
    path = tmp_path / "future.sqlite3"
    _create_legacy_database(path)
    _set_user_version(path, SpotRepository.SCHEMA_VERSION + 1)

    with pytest.raises(DatabaseMigrationError, match="newer than supported"):
        SpotRepository(path)

    connection = sqlite3.connect(path)
    try:
        assert (
            connection.execute("PRAGMA user_version").fetchone()[0]
            == SpotRepository.SCHEMA_VERSION + 1
        )
        assert connection.execute(
            "SELECT value FROM legacy_marker"
        ).fetchone()[0] == "preserve me"
    finally:
        connection.close()
    assert not (tmp_path / "future-backups").exists()


def test_corrupt_database_is_refused_before_backup_or_migration(tmp_path):
    path = tmp_path / "corrupt.sqlite3"
    path.write_bytes(b"this is not sqlite")

    with pytest.raises(DatabaseMigrationError, match="cannot be checked"):
        SpotRepository(path)

    assert path.read_bytes() == b"this is not sqlite"
    assert not (tmp_path / "corrupt-backups").exists()


def test_backup_retention_keeps_five_newest_verified_copies(tmp_path):
    path = tmp_path / "retained.sqlite3"
    _create_legacy_database(path)
    for _index in range(7):
        _set_user_version(path, 0)
        SpotRepository(path)

    backups = SpotRepository(path).list_database_backups()
    assert len(backups) == SpotRepository.BACKUP_RETENTION
    assert all(backup.exists() for backup in backups)


def test_backup_failure_aborts_before_schema_or_data_are_changed(tmp_path, monkeypatch):
    path = tmp_path / "blocked.sqlite3"
    _create_legacy_database(path)

    def fail_backup(_repository, _old_version):
        raise DatabaseMigrationError("backup unavailable")

    monkeypatch.setattr(SpotRepository, "_create_pre_migration_backup", fail_backup)

    with pytest.raises(DatabaseMigrationError, match="backup unavailable"):
        SpotRepository(path)

    connection = sqlite3.connect(path)
    try:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 0
        assert connection.execute(
            "SELECT value FROM legacy_marker"
        ).fetchone()[0] == "preserve me"
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert "spots" not in tables
    finally:
        connection.close()


def test_schema_v1_spots_gain_psk_reporter_source_without_data_loss(tmp_path):
    path = tmp_path / "v1.sqlite3"
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            """
            CREATE TABLE spots (
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
                band TEXT NOT NULL,
                tx_session_id INTEGER,
                campaign_id INTEGER
            )
            """
        )
        connection.execute(
            """
            INSERT INTO spots (
                source_key, frequency_hz, mode, snr_db, observed_at,
                tx_call, tx_grid, rx_call, rx_grid, band
            ) VALUES (
                'legacy-spot', 14074000, 'FT8', -10,
                '2026-07-23T10:00:00+00:00',
                'OK7PS', 'JN79AA', 'DL1ABC', 'JO62QM', '20m'
            )
            """
        )
        connection.execute("PRAGMA user_version = 1")
        connection.commit()
    finally:
        connection.close()

    repository = SpotRepository(path)
    spots = repository.list_spots()

    assert repository.schema_version == 3
    assert repository.migration_performed
    assert len(spots) == 1
    assert spots[0].source == "pskreporter"
