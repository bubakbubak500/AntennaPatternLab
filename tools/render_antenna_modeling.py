"""Render the real NEC2 workbench in representative states for visual QA."""

from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from matplotlib import get_data_path
from PySide6.QtCore import QSettings
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

import antenna_pattern_lab.antenna_modeling_dialog as workbench_module
from antenna_pattern_lab.antenna_model import antenna_template
from antenna_pattern_lab.antenna_modeling_dialog import AntennaModelingDialog
from antenna_pattern_lab.nec_runner import (
    CurrentSample,
    ImpedancePoint,
    NecRunResult,
    RadiationSample,
)
from antenna_pattern_lab.storage import SpotRepository
from antenna_pattern_lab.theme import DesignStyle, ThemeController, ThemePreference


OUTPUT = Path(
    os.environ.get(
        "APL_UI_CAPTURE_DIR",
        Path(__file__).resolve().parents[1] / "docs" / "ui" / "after",
    )
)


def result_for(model):
    frequencies = (13_900_000, 14_000_000, 14_074_000, 14_200_000, 14_300_000)
    impedance = tuple(
        ImpedancePoint(
            frequency,
            48 + index * 3,
            (index - 2) * 9,
            1.03 + abs(index - 2) * 0.18,
        )
        for index, frequency in enumerate(frequencies)
    )
    radiation = tuple(
        RadiationSample(
            14_074_000,
            theta,
            phi,
            7.1
            - abs(theta - 60) / 12
            - 8 * abs(__import__("math").sin(__import__("math").radians(phi))),
        )
        for theta in range(0, 91, 5)
        for phi in range(0, 360, 5)
    )
    currents = tuple(
        CurrentSample(14_074_000, 1 if segment <= 11 else 2, segment, 0.01 + segment / 1000, -30 + segment * 3)
        for segment in range(1, 23)
    )
    return NecRunResult(
        model.sha256,
        r"C:\Users\operator\AppData\Local\Programs\OpenNEC\bin\onec.exe",
        "onec 2.2.0",
        ("onec.exe", "-f", "original", "-o", "model.out", "model.nec"),
        datetime(2026, 7, 24, 12, tzinfo=timezone.utc),
        0.42,
        "a" * 64,
        "b" * 64,
        impedance,
        radiation,
        currents,
        "normal NEC output",
    )


def main() -> int:
    application = QApplication.instance() or QApplication(sys.argv)
    matplotlib_fonts = Path(get_data_path()) / "fonts" / "ttf"
    for filename in ("DejaVuSans.ttf", "DejaVuSansMono.ttf"):
        QFontDatabase.addApplicationFont(str(matplotlib_fonts / filename))
    QFont.insertSubstitution("Sans Serif", "DejaVu Sans")
    QFont.insertSubstitution("monospace", "DejaVu Sans Mono")
    application.setFont(QFont("DejaVu Sans"))
    OUTPUT.mkdir(parents=True, exist_ok=True)
    workbench_module.detect_opennec = lambda: Path(
        r"C:\Users\operator\AppData\Local\Programs\OpenNEC\bin\onec.exe"
    )
    scenarios = (
        ("cze-light-model-1180x720", "CZE", DesignStyle.MONITOR, ThemePreference.LIGHT, (1180, 720), 0),
        ("eng-dark-results-1366x850", "ENG", DesignStyle.MONITOR, ThemePreference.DARK, (1366, 850), 1),
        ("cze-light-radiation3d-1180x720", "CZE", DesignStyle.MONITOR, ThemePreference.LIGHT, (1180, 720), 2),
        ("eng-dark-radiation3d-1366x850", "ENG", DesignStyle.MONITOR, ThemePreference.DARK, (1366, 850), 2),
        ("eng-dark-radiation3d-1920x1080", "ENG", DesignStyle.MONITOR, ThemePreference.DARK, (1920, 1080), 2),
        ("cze-light-candidates-1180x720", "CZE", DesignStyle.MONITOR, ThemePreference.LIGHT, (1180, 720), 3),
        ("eng-classic-radiation3d-1180x720", "ENG", DesignStyle.CLASSIC, ThemePreference.SYSTEM, (1180, 720), 2),
    )
    with tempfile.TemporaryDirectory(prefix="antenna-modeling-ui-", ignore_cleanup_errors=True) as directory:
        for suffix, language, style, theme, size, tab in scenarios:
            settings = QSettings(
                str(Path(directory) / f"{suffix}.ini"),
                QSettings.Format.IniFormat,
            )
            settings.setValue("ui/design_style", style.value)
            settings.setValue("ui/theme", theme.value)
            controller = ThemeController(settings)
            repository = SpotRepository(Path(directory) / f"{suffix}.sqlite3")
            model = antenna_template("yagi", height_m=12)
            stored = repository.save_nec_model(model)
            result = result_for(model)
            repository.save_nec_run(stored.id, result, label="Independent baseline")
            for offset, kind in ((-2, "real"), (0, "perfect"), (2, "free_space")):
                candidate = model.transformed(height_delta_m=offset)
                candidate = __import__("dataclasses").replace(
                    candidate,
                    name=f"{model.name} · Δh {offset:+g} m · {kind}",
                    ground=__import__("dataclasses").replace(candidate.ground, kind=kind),
                )
                saved_candidate = repository.save_nec_model(candidate)
                repository.save_nec_run(
                    saved_candidate.id,
                    __import__("dataclasses").replace(
                        result,
                        model_sha256=candidate.sha256,
                        output_sha256=f"{offset + 3:x}" * 64,
                    ),
                    purpose="assisted_candidate",
                    label=f"Δh {offset:+g} m · {kind}",
                )
            dialog = AntennaModelingDialog(repository, language)
            dialog._load_model(model)
            dialog.result = result
            dialog._render_result()
            dialog._candidate_runs = [
                (run, float(run.label.split()[1]), run.label.split()[-1])
                for run in repository.list_nec_runs(purpose="assisted_candidate")
            ]
            dialog._render_candidates()
            dialog.resize(*size)
            dialog.show()
            application.processEvents()
            dialog.tabs.setCurrentIndex(tab)
            application.processEvents()
            destination = OUTPUT / f"dialog-antenna-modeling-{suffix}.png"
            if not dialog.grab().save(str(destination)):
                raise RuntimeError(f"Could not save {destination}")
            print(destination)
            dialog.close()
            controller.deleteLater()
            application.processEvents()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
