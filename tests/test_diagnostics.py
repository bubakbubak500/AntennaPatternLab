import json

from antenna_pattern_lab.dependencies import DependencyStatus
from antenna_pattern_lab.diagnostics import build_diagnostic_report, diagnostic_json


def test_live_readiness_requires_the_complete_chain():
    report = build_diagnostic_report(
        app_version="0.17.0",
        database_path="C:/Data/spots.sqlite3",
        spot_count=12,
        tx_session_count=2,
        callsign="ok7ps",
        tx_grid="jn79",
        band="20m",
        mode="FT8",
        mqtt_state="connected",
        wsjtx_state="connected",
        wsjtx_operating_state="rx",
        hamlib_state="disabled",
        hamlib_enabled=False,
        database_schema_version=1,
        database_integrity="ok",
        database_backup_path="C:/Data/spots-backups/pre.sqlite3",
        database_migration_performed=True,
        dependencies=(
            DependencyStatus("hamlib", "Hamlib", False, None, "https://example.test"),
            DependencyStatus("wsjtx", "WSJT-X", True, None, "https://example.test"),
        ),
    )
    assert report["readiness"]["live_chain_verified"]
    assert report["configuration"]["callsign"] == "OK7PS"
    assert report["database"]["integrity"] == "ok"
    assert report["database"]["migration_performed_at_startup"]
    assert report["readiness"]["database_integrity_ok"]
    encoded = diagnostic_json(report)
    assert json.loads(encoded)["counts"]["spots"] == 12
    assert "credentials" not in report


def test_missing_heartbeat_keeps_live_chain_unverified():
    report = build_diagnostic_report(
        app_version="0.17.0", database_path="db", spot_count=1, tx_session_count=1,
        callsign="OK7PS", tx_grid="JN79", band="20m", mode="FT8",
        mqtt_state="connected", wsjtx_state="waiting", wsjtx_operating_state="",
        hamlib_state="disabled", hamlib_enabled=False, dependencies=(),
    )
    assert not report["readiness"]["wsjtx_heartbeat_received"]
    assert not report["readiness"]["live_chain_verified"]
