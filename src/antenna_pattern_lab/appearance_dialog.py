from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QVBoxLayout

from .design_system import ThemeToggle
from .theme import DesignStyle, ThemePreference


class AppearanceDialog(QDialog):
    def __init__(
        self,
        design_style: DesignStyle,
        preference: ThemePreference,
        language: str = "CZE",
        parent=None,
    ):
        super().__init__(parent)
        czech = language == "CZE"
        self.setWindowTitle("Vzhled aplikace" if czech else "Application appearance")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)
        intro = QLabel(
            "Původní vzhled zůstává dostupný. Monitor nabízí kompaktní technický motiv."
            if czech
            else "The original appearance remains available. Monitor provides the compact technical theme."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)
        form = QFormLayout()
        self.design_style = QComboBox()
        self.design_style.addItem("Classic", DesignStyle.CLASSIC)
        self.design_style.addItem("Monitor", DesignStyle.MONITOR)
        self.design_style.setCurrentIndex(self.design_style.findData(design_style))
        self.theme = ThemeToggle()
        self.theme.set_preference(preference)
        form.addRow("Vzhled" if czech else "Design", self.design_style)
        form.addRow("Motiv" if czech else "Theme", self.theme)
        layout.addLayout(form)
        hint = QLabel(
            "Volba „Podle systému“ reaguje na změny motivu Windows bez restartu."
            if czech
            else "Follow system reacts to Windows theme changes without restarting."
        )
        hint.setObjectName("Metadata")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self) -> tuple[DesignStyle, ThemePreference]:
        return self.design_style.currentData(), self.theme.currentData()
