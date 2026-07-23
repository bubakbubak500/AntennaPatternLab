from __future__ import annotations

import sqlite3

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from .profiles import ANTENNA_TYPES, WIRE_TYPES, AntennaProfile, normalize_antenna_type
from .storage import SpotRepository


TEXT = {
    "CZE": {
        "title": "Profily antén",
        "profile": "Profil",
        "name": "Název",
        "type": "Typ antény",
        "types": {
            "vertical": "Vertikál",
            "efhw": "EFHW",
            "efrw": "EFRW",
            "dipole": "Dipól",
            "inverted_v": "Inverted-V",
            "yagi": "Yagi",
            "other": "Ostatní",
        },
        "apex": "Výška vrcholu (m)",
        "height_vertical": "Výška vertikálu (m)",
        "height_wire": "Výška středu/napájení (m)",
        "height_yagi": "Výška stožáru (m)",
        "end": "Výška konců (m)",
        "orientation": "Orientace (°)",
        "power": "Výkon (W)",
        "tuner": "Tuner zapnutý",
        "wire_length": "Délka vodiče (m)",
        "radial_count": "Počet radiálů",
        "radial_length": "Délka radiálů (m)",
        "element_count": "Počet prvků",
        "boom_length": "Délka ráhna (m)",
        "transformer": "Transformátor / poměr",
        "notes": "Poznámky",
        "new": "Nový",
        "save": "Uložit",
        "archive": "Archivovat",
        "close": "Zavřít",
        "unsaved": "Nový profil",
        "saved": "Profil byl uložen.",
        "revised": (
            "Uložena revize v{revision}. Předchozí verze zůstala beze změny "
            "u starších měření."
        ),
        "error": "Profil nelze uložit",
        "archive_title": "Archivovat profil?",
        "archive_text": "Profil zmizí z výběru, ale zůstane u starších TX relací.",
    },
    "ENG": {
        "title": "Antenna profiles",
        "profile": "Profile",
        "name": "Name",
        "type": "Antenna type",
        "types": {
            "vertical": "Vertical",
            "efhw": "EFHW",
            "efrw": "EFRW",
            "dipole": "Dipole",
            "inverted_v": "Inverted-V",
            "yagi": "Yagi",
            "other": "Other",
        },
        "apex": "Apex height (m)",
        "height_vertical": "Vertical height (m)",
        "height_wire": "Center/feed height (m)",
        "height_yagi": "Mast height (m)",
        "end": "End height (m)",
        "orientation": "Orientation (°)",
        "power": "Power (W)",
        "tuner": "Tuner enabled",
        "wire_length": "Wire length (m)",
        "radial_count": "Radial count",
        "radial_length": "Radial length (m)",
        "element_count": "Element count",
        "boom_length": "Boom length (m)",
        "transformer": "Transformer / ratio",
        "notes": "Notes",
        "new": "New",
        "save": "Save",
        "archive": "Archive",
        "close": "Close",
        "unsaved": "New profile",
        "saved": "Profile saved.",
        "revised": (
            "Revision v{revision} saved. The previous version remains unchanged "
            "for historical measurements."
        ),
        "error": "Profile cannot be saved",
        "archive_title": "Archive profile?",
        "archive_text": "The profile disappears from selection but remains attached to older TX sessions.",
    },
}


class AntennaProfileDialog(QDialog):
    def __init__(self, repository: SpotRepository, language: str, parent=None):
        super().__init__(parent)
        self.repository = repository
        self.text = TEXT[language if language in TEXT else "CZE"]
        self.profile_id: int | None = None
        self.setWindowTitle(self.text["title"])
        self.resize(480, 520)
        self._build_ui()
        self._reload_profiles()
        self.new_profile()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.form = form
        self.field_labels: dict[str, QLabel] = {}
        self.profiles = QComboBox()
        self.name = QLineEdit()
        self.antenna_type = QComboBox()
        for type_code in ANTENNA_TYPES:
            self.antenna_type.addItem(self.text["types"][type_code], type_code)
        self.apex_height = self._nullable_spin(0, 100, " m")
        self.end_height = self._nullable_spin(0, 100, " m")
        self.orientation = self._nullable_spin(0, 359.9, "°")
        self.power = self._nullable_spin(0, 10_000, " W")
        self.wire_length = self._nullable_spin(0, 1000, " m")
        self.radial_count = self._nullable_int_spin(0, 1000)
        self.radial_length = self._nullable_spin(0, 1000, " m")
        self.element_count = self._nullable_int_spin(1, 100)
        self.boom_length = self._nullable_spin(0, 100, " m")
        self.transformer_ratio = QLineEdit()
        self.tuner = QCheckBox()
        self.notes = QPlainTextEdit()
        self.notes.setMaximumHeight(100)
        self._add_row("profile", self.text["profile"], self.profiles)
        self._add_row("name", self.text["name"], self.name)
        self._add_row("type", self.text["type"], self.antenna_type)
        self._add_row("apex", self.text["apex"], self.apex_height)
        self._add_row("end", self.text["end"], self.end_height)
        self._add_row("orientation", self.text["orientation"], self.orientation)
        self._add_row("wire_length", self.text["wire_length"], self.wire_length)
        self._add_row("radial_count", self.text["radial_count"], self.radial_count)
        self._add_row("radial_length", self.text["radial_length"], self.radial_length)
        self._add_row("element_count", self.text["element_count"], self.element_count)
        self._add_row("boom_length", self.text["boom_length"], self.boom_length)
        self._add_row("transformer", self.text["transformer"], self.transformer_ratio)
        self._add_row("power", self.text["power"], self.power)
        self._add_row("tuner", self.text["tuner"], self.tuner)
        self._add_row("notes", self.text["notes"], self.notes)
        layout.addLayout(form)
        self.message = QLabel()
        layout.addWidget(self.message)
        buttons = QHBoxLayout()
        self.new_button = QPushButton(self.text["new"])
        self.save_button = QPushButton(self.text["save"])
        self.archive_button = QPushButton(self.text["archive"])
        self.close_button = QPushButton(self.text["close"])
        buttons.addWidget(self.new_button)
        buttons.addWidget(self.save_button)
        buttons.addWidget(self.archive_button)
        buttons.addStretch()
        buttons.addWidget(self.close_button)
        layout.addLayout(buttons)
        self.profiles.currentIndexChanged.connect(self._profile_selected)
        self.antenna_type.currentIndexChanged.connect(self._type_changed)
        self.new_button.clicked.connect(self.new_profile)
        self.save_button.clicked.connect(self.save_profile)
        self.archive_button.clicked.connect(self.archive_profile)
        self.close_button.clicked.connect(self.accept)

    def _add_row(self, key: str, text: str, widget) -> None:
        label = QLabel(text)
        self.field_labels[key] = label
        self.form.addRow(label, widget)

    @staticmethod
    def _nullable_spin(minimum: float, maximum: float, suffix: str) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(-1, maximum)
        spin.setDecimals(1)
        spin.setSpecialValueText("—")
        spin.setSuffix(suffix)
        spin.setValue(-1)
        return spin

    @staticmethod
    def _nullable_int_spin(minimum: int, maximum: int) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(-1, maximum)
        spin.setSpecialValueText("—")
        spin.setValue(-1)
        return spin

    def _reload_profiles(self, selected_id: int | None = None) -> None:
        self.profiles.blockSignals(True)
        self.profiles.clear()
        self.profiles.addItem(self.text["unsaved"], None)
        for profile in self.repository.list_antenna_profiles():
            self.profiles.addItem(profile.name, profile.id)
        index = self.profiles.findData(selected_id)
        self.profiles.setCurrentIndex(max(0, index))
        self.profiles.blockSignals(False)

    def new_profile(self) -> None:
        self.profile_id = None
        self.profiles.setCurrentIndex(0)
        self.name.clear()
        self.antenna_type.setCurrentIndex(self.antenna_type.findData("dipole"))
        for spin in (
            self.apex_height,
            self.end_height,
            self.orientation,
            self.power,
            self.wire_length,
            self.radial_count,
            self.radial_length,
            self.element_count,
            self.boom_length,
        ):
            spin.setValue(-1)
        self.transformer_ratio.clear()
        self.tuner.setChecked(False)
        self.notes.clear()
        self.message.clear()
        self.archive_button.setEnabled(False)
        self._type_changed()

    def _profile_selected(self, _index: int) -> None:
        profile_id = self.profiles.currentData()
        if profile_id is None:
            self.new_profile()
            return
        profile = self.repository.get_antenna_profile(profile_id)
        self.profile_id = profile.id
        self.name.setText(profile.name)
        type_index = self.antenna_type.findData(normalize_antenna_type(profile.antenna_type))
        self.antenna_type.setCurrentIndex(max(0, type_index))
        self._set_nullable(self.apex_height, profile.apex_height_m)
        self._set_nullable(self.end_height, profile.end_height_m)
        self._set_nullable(self.orientation, profile.orientation_deg)
        self._set_nullable(self.power, profile.power_w)
        self._set_nullable(self.wire_length, profile.wire_length_m)
        self.radial_count.setValue(-1 if profile.radial_count is None else profile.radial_count)
        self._set_nullable(self.radial_length, profile.radial_length_m)
        self.element_count.setValue(-1 if profile.element_count is None else profile.element_count)
        self._set_nullable(self.boom_length, profile.boom_length_m)
        self.transformer_ratio.setText(profile.transformer_ratio)
        self.tuner.setChecked(profile.tuner_enabled)
        self.notes.setPlainText(profile.notes)
        self.archive_button.setEnabled(True)
        self.message.clear()
        self._type_changed()

    @staticmethod
    def _set_nullable(spin: QDoubleSpinBox, value: float | None) -> None:
        spin.setValue(-1 if value is None else value)

    @staticmethod
    def _get_nullable(spin: QDoubleSpinBox) -> float | None:
        return None if spin.value() < 0 else spin.value()

    @staticmethod
    def _get_nullable_int(spin: QSpinBox) -> int | None:
        return None if spin.value() < 0 else spin.value()

    def _type_changed(self, *_args) -> None:
        antenna_type = self.antenna_type.currentData() or "other"
        is_wire = antenna_type in WIRE_TYPES
        is_vertical = antenna_type == "vertical"
        is_yagi = antenna_type == "yagi"
        visibility = {
            "end": is_wire,
            "orientation": is_wire or is_yagi or antenna_type == "other",
            "wire_length": is_wire,
            "radial_count": is_vertical,
            "radial_length": is_vertical,
            "element_count": is_yagi,
            "boom_length": is_yagi,
            "transformer": antenna_type in ("efhw", "efrw"),
        }
        widgets = {
            "end": self.end_height,
            "orientation": self.orientation,
            "wire_length": self.wire_length,
            "radial_count": self.radial_count,
            "radial_length": self.radial_length,
            "element_count": self.element_count,
            "boom_length": self.boom_length,
            "transformer": self.transformer_ratio,
        }
        for key, visible in visibility.items():
            self.field_labels[key].setVisible(visible)
            widgets[key].setVisible(visible)
        height_key = "height_vertical" if is_vertical else "height_yagi" if is_yagi else "height_wire" if is_wire else "apex"
        self.field_labels["apex"].setText(self.text[height_key])

    def save_profile(self) -> None:
        previous_id = self.profile_id
        profile = AntennaProfile(
            id=self.profile_id,
            name=self.name.text(),
            antenna_type=self.antenna_type.currentData(),
            apex_height_m=self._get_nullable(self.apex_height),
            end_height_m=self._get_nullable(self.end_height),
            orientation_deg=self._get_nullable(self.orientation),
            power_w=self._get_nullable(self.power),
            tuner_enabled=self.tuner.isChecked(),
            wire_length_m=self._get_nullable(self.wire_length),
            radial_count=self._get_nullable_int(self.radial_count),
            radial_length_m=self._get_nullable(self.radial_length),
            element_count=self._get_nullable_int(self.element_count),
            boom_length_m=self._get_nullable(self.boom_length),
            transformer_ratio=self.transformer_ratio.text(),
            notes=self.notes.toPlainText(),
        )
        try:
            saved = self.repository.save_antenna_profile(profile)
        except (ValueError, sqlite3.IntegrityError) as exc:
            QMessageBox.warning(self, self.text["error"], str(exc))
            return
        self.profile_id = saved.id
        self._reload_profiles(saved.id)
        self.archive_button.setEnabled(True)
        self.message.setText(
            self.text["revised"].format(revision=saved.revision)
            if previous_id is not None and saved.id != previous_id
            else self.text["saved"]
        )

    def archive_profile(self) -> None:
        if self.profile_id is None:
            return
        answer = QMessageBox.question(
            self,
            self.text["archive_title"],
            self.text["archive_text"],
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.repository.archive_antenna_profile(self.profile_id)
        self._reload_profiles()
        self.new_profile()
