from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
)


TEXT = {
    "CZE": {
        "title": "Nastavení komunikace",
        "intro": "Síťové a rádiové rozhraní běží na pozadí. Změny se použijí po uložení.",
        "wsjtx_host": "WSJT-X adresa",
        "wsjtx_port": "WSJT-X UDP port",
        "forward": "UDP forward",
        "forward_hint": "Volitelné cíle oddělené čárkou, např. 127.0.0.1:2238",
        "hamlib": "Sledovat rádio přes Hamlib rigctld",
        "hamlib_port": "Hamlib TCP port",
        "rotator": "Sledovat rotátor přes Hamlib rotctld (jen čtení)",
        "rotator_port": "rotctld TCP port",
        "activity": "Dokládat aktivní RX expozici",
    },
    "ENG": {
        "title": "Communication settings",
        "intro": "Network and radio interfaces run in the background. Changes apply after saving.",
        "wsjtx_host": "WSJT-X address",
        "wsjtx_port": "WSJT-X UDP port",
        "forward": "UDP forwarding",
        "forward_hint": "Optional comma-separated targets, e.g. 127.0.0.1:2238",
        "hamlib": "Monitor radio through Hamlib rigctld",
        "hamlib_port": "Hamlib TCP port",
        "rotator": "Monitor rotator through Hamlib rotctld (read-only)",
        "rotator_port": "rotctld TCP port",
        "activity": "Record active-RX exposure",
    },
}


@dataclass(frozen=True, slots=True)
class CommunicationSettings:
    wsjtx_host: str
    wsjtx_port: int
    wsjtx_forward: str
    hamlib_enabled: bool
    hamlib_port: int
    rotator_enabled: bool
    rotator_port: int
    rx_activity_enabled: bool


class CommunicationSettingsDialog(QDialog):
    def __init__(
        self,
        values: CommunicationSettings,
        language: str = "CZE",
        parent=None,
    ):
        super().__init__(parent)
        text = TEXT[language if language in TEXT else "CZE"]
        self.setWindowTitle(text["title"])
        self.setMinimumWidth(560)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)
        intro = QLabel(text["intro"])
        intro.setWordWrap(True)
        layout.addWidget(intro)
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)

        self.wsjtx_host = QLineEdit(values.wsjtx_host)
        self.wsjtx_port = QSpinBox()
        self.wsjtx_port.setRange(1024, 65535)
        self.wsjtx_port.setValue(values.wsjtx_port)
        self.wsjtx_forward = QLineEdit(values.wsjtx_forward)
        self.wsjtx_forward.setPlaceholderText(text["forward_hint"])
        self.hamlib_enabled = QCheckBox(text["hamlib"])
        self.hamlib_enabled.setChecked(values.hamlib_enabled)
        self.hamlib_port = QSpinBox()
        self.hamlib_port.setRange(1024, 65535)
        self.hamlib_port.setValue(values.hamlib_port)
        self.rotator_enabled = QCheckBox(text["rotator"])
        self.rotator_enabled.setChecked(values.rotator_enabled)
        self.rotator_port = QSpinBox()
        self.rotator_port.setRange(1024, 65535)
        self.rotator_port.setValue(values.rotator_port)
        self.rx_activity_enabled = QCheckBox(text["activity"])
        self.rx_activity_enabled.setChecked(values.rx_activity_enabled)

        form.addRow(text["wsjtx_host"], self.wsjtx_host)
        form.addRow(text["wsjtx_port"], self.wsjtx_port)
        form.addRow(text["forward"], self.wsjtx_forward)
        form.addRow("", self.hamlib_enabled)
        form.addRow(text["hamlib_port"], self.hamlib_port)
        form.addRow("", self.rotator_enabled)
        form.addRow(text["rotator_port"], self.rotator_port)
        form.addRow("", self.rx_activity_enabled)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        save_button = buttons.button(QDialogButtonBox.StandardButton.Save)
        save_button.setObjectName("primaryAction")
        save_button.setDefault(True)
        layout.addWidget(buttons)
        for widget, name in (
            (self.wsjtx_host, text["wsjtx_host"]),
            (self.wsjtx_port, text["wsjtx_port"]),
            (self.wsjtx_forward, text["forward"]),
            (self.hamlib_enabled, text["hamlib"]),
            (self.hamlib_port, text["hamlib_port"]),
            (self.rotator_enabled, text["rotator"]),
            (self.rotator_port, text["rotator_port"]),
            (self.rx_activity_enabled, text["activity"]),
        ):
            widget.setAccessibleName(name)

    def values(self) -> CommunicationSettings:
        return CommunicationSettings(
            wsjtx_host=self.wsjtx_host.text().strip() or "127.0.0.1",
            wsjtx_port=self.wsjtx_port.value(),
            wsjtx_forward=self.wsjtx_forward.text().strip(),
            hamlib_enabled=self.hamlib_enabled.isChecked(),
            hamlib_port=self.hamlib_port.value(),
            rotator_enabled=self.rotator_enabled.isChecked(),
            rotator_port=self.rotator_port.value(),
            rx_activity_enabled=self.rx_activity_enabled.isChecked(),
        )
