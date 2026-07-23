from __future__ import annotations

from datetime import datetime, timezone
import json
import platform
from typing import Iterable

from .dependencies import DependencyStatus


def build_diagnostic_report(
    *,
    app_version: str,
    database_path: str,
    spot_count: int,
    tx_session_count: int,
    callsign: str,
    tx_grid: str,
    band: str,
    mode: str,
    mqtt_state: str,
    wsjtx_state: str,
    wsjtx_operating_state: str,
    hamlib_state: str,
    hamlib_enabled: bool,
    dependencies: Iterable[DependencyStatus],
    rotator_state: str = "disabled",
    rotator_enabled: bool = False,
    database_schema_version: int | None = None,
    database_integrity: str | None = None,
    database_backup_path: str | None = None,
    database_migration_performed: bool = False,
) -> dict:
    tools = {
        item.key: {
            "found": item.found,
            "executable": str(item.executable) if item.executable else None,
        }
        for item in dependencies
    }
    readiness = {
        "mqtt_confirmed": mqtt_state == "connected",
        "wsjtx_heartbeat_received": wsjtx_state == "connected",
        "wsjtx_tx_seen": wsjtx_operating_state == "tx" or tx_session_count > 0,
        "hamlib_ready_or_optional": not hamlib_enabled or hamlib_state == "connected",
        "rotator_ready_or_optional": (
            not rotator_enabled or rotator_state == "connected"
        ),
        "database_integrity_ok": (
            database_integrity is None or database_integrity == "ok"
        ),
        "spots_received": spot_count > 0,
        "tx_sessions_recorded": tx_session_count > 0,
    }
    readiness["live_chain_verified"] = all(readiness.values())
    return {
        "schema": 2,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "application": {"name": "Antenna Pattern Lab", "version": app_version},
        "system": {"platform": platform.platform(), "architecture": platform.machine()},
        "configuration": {
            "callsign": callsign.strip().upper(),
            "tx_grid": tx_grid.strip().upper(),
            "band": band,
            "mode": mode,
            "database_path": database_path,
        },
        "counts": {"spots": spot_count, "tx_sessions": tx_session_count},
        "database": {
            "schema_version": database_schema_version,
            "integrity": database_integrity,
            "migration_performed_at_startup": database_migration_performed,
            "last_pre_migration_backup": database_backup_path,
        },
        "connections": {
            "mqtt": mqtt_state,
            "wsjtx": wsjtx_state,
            "wsjtx_operating": wsjtx_operating_state or None,
            "hamlib": hamlib_state,
            "hamlib_enabled": hamlib_enabled,
            "rotator": rotator_state,
            "rotator_enabled": rotator_enabled,
        },
        "external_tools": tools,
        "readiness": readiness,
        "privacy": "No spot rows, messages, credentials, or radio serial data are included.",
    }


def diagnostic_json(report: dict) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
