from __future__ import annotations

from datetime import datetime, timezone

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .analysis import locate_spot
from .campaign_attachments_dialog import CampaignAttachmentsDialog
from .campaign_comparison_dialog import CampaignComparisonDialog
from .campaign_log_dialog import CampaignLogDialog
from .campaigns import (
    MeasurementCampaign,
    assess_campaign_metadata,
    assess_campaign_progress,
)
from .storage import SpotRepository
from .theme import TOKENS, semantic_style


TEXT = {
    "CZE": {
        "title": "Měřicí kampaně",
        "name": "Název",
        "objective": "Cíl měření",
        "callsign": "Značka",
        "grid": "TX lokátor",
        "band": "Pásmo",
        "mode": "Mód",
        "profile": "Profil antény",
        "notes": "Poznámky a podmínky",
        "target_title": "Minimální cíl",
        "target_spots": "spotů",
        "target_receivers": "RX",
        "target_sectors": "sektorů",
        "target_blocks": "30min bloků",
        "progress_complete": "✓ cíl splněn",
        "progress_incomplete": "{met}/4 podmínky",
        "progress_tip": (
            "Spoty {spots}/{target_spots} · RX {receivers}/{target_receivers} · "
            "sektory {sectors}/{target_sectors} · bloky {blocks}/{target_blocks}"
        ),
        "no_profile": "— bez profilu —",
        "start": "Zahájit kampaň",
        "stop": "Ukončit aktivní kampaň",
        "coverage": "Pokrytí",
        "diary": "Deník",
        "attachments": "Přílohy",
        "compare": "Porovnat 2 kampaně",
        "readiness_complete": "Metadata měření: {percent}% · připraveno",
        "readiness_missing": "Metadata měření: {percent}% · chybí: {missing}",
        "metadata": {
            "name": "název",
            "objective": "cíl",
            "callsign": "značka",
            "grid": "platný lokátor",
            "band": "pásmo",
            "mode": "mód",
            "profile": "profil antény",
            "power": "výkon v profilu",
            "conditions": "výchozí podmínky",
        },
        "close": "Zavřít",
        "active": "Aktivní kampaň: {name} · {band} {mode} · od {started}",
        "inactive": "Žádná měřicí kampaň není aktivní.",
        "invalid": "Kampaň nelze zahájit: {error}",
        "headers": [
            "Začátek UTC",
            "Konec UTC",
            "Název",
            "Pásmo",
            "Mód",
            "Profil",
            "Spoty",
            "RX",
            "TX",
            "Cíl",
        ],
        "running": "aktivní",
    },
    "ENG": {
        "title": "Measurement campaigns",
        "name": "Name",
        "objective": "Measurement objective",
        "callsign": "Callsign",
        "grid": "TX grid",
        "band": "Band",
        "mode": "Mode",
        "profile": "Antenna profile",
        "notes": "Notes and conditions",
        "target_title": "Minimum target",
        "target_spots": "spots",
        "target_receivers": "RX",
        "target_sectors": "sectors",
        "target_blocks": "30-min blocks",
        "progress_complete": "✓ target reached",
        "progress_incomplete": "{met}/4 conditions",
        "progress_tip": (
            "Spots {spots}/{target_spots} · RX {receivers}/{target_receivers} · "
            "sectors {sectors}/{target_sectors} · blocks {blocks}/{target_blocks}"
        ),
        "no_profile": "— no profile —",
        "start": "Start campaign",
        "stop": "Finish active campaign",
        "coverage": "Coverage",
        "diary": "Log",
        "attachments": "Attachments",
        "compare": "Compare 2 campaigns",
        "readiness_complete": "Measurement metadata: {percent}% · ready",
        "readiness_missing": "Measurement metadata: {percent}% · missing: {missing}",
        "metadata": {
            "name": "name",
            "objective": "objective",
            "callsign": "callsign",
            "grid": "valid TX grid",
            "band": "band",
            "mode": "mode",
            "profile": "antenna profile",
            "power": "profile power",
            "conditions": "initial conditions",
        },
        "close": "Close",
        "active": "Active campaign: {name} · {band} {mode} · since {started}",
        "inactive": "No measurement campaign is active.",
        "invalid": "Cannot start campaign: {error}",
        "headers": [
            "Start UTC",
            "End UTC",
            "Name",
            "Band",
            "Mode",
            "Profile",
            "Spots",
            "RX",
            "TX",
            "Target",
        ],
        "running": "active",
    },
}


class CampaignDialog(QDialog):
    def __init__(
        self,
        repository: SpotRepository,
        language: str,
        callsign: str,
        tx_grid: str,
        band: str,
        mode: str,
        profile_id: int | None,
        parent=None,
    ):
        super().__init__(parent)
        self.repository = repository
        self.language = language if language in TEXT else "CZE"
        self.text = TEXT[self.language]
        self.coverage_campaign_id: int | None = None
        self.setWindowTitle(self.text["title"])
        self.resize(1050, 620)
        layout = QVBoxLayout(self)

        self.active_status = QLabel()
        self.active_status.setWordWrap(True)
        self.active_status.setStyleSheet("font-size: 15px; font-weight: 700;")
        layout.addWidget(self.active_status)

        form = QGridLayout()
        form.setColumnStretch(1, 1)
        form.setColumnStretch(3, 1)
        profile_name = ""
        if profile_id is not None:
            try:
                profile_name = repository.get_antenna_profile(profile_id).name
            except ValueError:
                profile_id = None
        default_name = " · ".join(
            part
            for part in (
                datetime.now().strftime("%Y-%m-%d"),
                band,
                profile_name,
            )
            if part
        )
        self.name = QLineEdit(default_name)
        self.objective = QLineEdit()
        self.callsign = QLineEdit(callsign.strip().upper())
        self.tx_grid = QLineEdit(tx_grid.strip().upper())
        self.band = QComboBox()
        self.band.addItems(("80m", "40m", "30m", "20m", "17m", "15m", "12m", "10m"))
        self.band.setCurrentText(band)
        self.mode = QComboBox()
        self.mode.addItems(("FT8", "WSPR"))
        self.mode.setCurrentText(mode)
        self.profile = QComboBox()
        self.profile.addItem(self.text["no_profile"], None)
        for antenna_profile in repository.list_antenna_profiles():
            self.profile.addItem(antenna_profile.name, antenna_profile.id)
        self.profile.setCurrentIndex(max(0, self.profile.findData(profile_id)))
        self.notes = QTextEdit()
        self.notes.setMaximumHeight(58)
        pairs = (
            (0, 0, self.text["name"], self.name),
            (0, 2, self.text["band"], self.band),
            (1, 0, self.text["objective"], self.objective),
            (1, 2, self.text["mode"], self.mode),
            (2, 0, self.text["callsign"], self.callsign),
            (2, 2, self.text["profile"], self.profile),
            (3, 0, self.text["grid"], self.tx_grid),
            (3, 2, self.text["notes"], self.notes),
        )
        for row, column, label, widget in pairs:
            form.addWidget(QLabel(label), row, column)
            form.addWidget(widget, row, column + 1)
        self.target_spots = QSpinBox()
        self.target_spots.setRange(1, 100_000)
        self.target_spots.setValue(100)
        self.target_receivers = QSpinBox()
        self.target_receivers.setRange(1, 10_000)
        self.target_receivers.setValue(10)
        self.target_sectors = QSpinBox()
        self.target_sectors.setRange(1, 12)
        self.target_sectors.setValue(8)
        self.target_blocks = QSpinBox()
        self.target_blocks.setRange(1, 10_000)
        self.target_blocks.setValue(6)
        target_widget = QWidget()
        target_layout = QHBoxLayout(target_widget)
        target_layout.setContentsMargins(0, 0, 0, 0)
        for spin, label in (
            (self.target_spots, self.text["target_spots"]),
            (self.target_receivers, self.text["target_receivers"]),
            (self.target_sectors, self.text["target_sectors"]),
            (self.target_blocks, self.text["target_blocks"]),
        ):
            target_layout.addWidget(spin)
            target_layout.addWidget(QLabel(label))
        target_layout.addStretch()
        form.addWidget(QLabel(self.text["target_title"]), 4, 0)
        form.addWidget(target_widget, 4, 1, 1, 3)
        layout.addLayout(form)
        self.readiness = QLabel()
        self.readiness.setWordWrap(True)
        layout.addWidget(self.readiness)

        actions = QHBoxLayout()
        self.start_button = QPushButton(self.text["start"])
        self.stop_button = QPushButton(self.text["stop"])
        self.coverage_button = QPushButton(self.text["coverage"])
        self.coverage_button.setEnabled(False)
        self.diary_button = QPushButton(self.text["diary"])
        self.diary_button.setEnabled(False)
        self.attachments_button = QPushButton(self.text["attachments"])
        self.attachments_button.setEnabled(False)
        self.compare_button = QPushButton(self.text["compare"])
        self.compare_button.setEnabled(False)
        close_button = QPushButton(self.text["close"])
        actions.addWidget(self.start_button)
        actions.addWidget(self.stop_button)
        actions.addWidget(self.coverage_button)
        actions.addWidget(self.diary_button)
        actions.addWidget(self.attachments_button)
        actions.addWidget(self.compare_button)
        actions.addStretch()
        actions.addWidget(close_button)
        layout.addLayout(actions)

        self.table = QTableWidget(0, len(self.text["headers"]))
        self.table.setHorizontalHeaderLabels(self.text["headers"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)

        self.start_button.clicked.connect(self.start_campaign)
        self.stop_button.clicked.connect(self.stop_campaign)
        self.coverage_button.clicked.connect(self.open_selected_coverage)
        self.diary_button.clicked.connect(self.open_selected_diary)
        self.attachments_button.clicked.connect(self.open_selected_attachments)
        self.compare_button.clicked.connect(self.open_selected_comparison)
        self.table.itemSelectionChanged.connect(self._selection_changed)
        for line_edit in (self.name, self.objective, self.callsign, self.tx_grid):
            line_edit.textChanged.connect(self._update_readiness)
        self.notes.textChanged.connect(self._update_readiness)
        self.band.currentIndexChanged.connect(self._update_readiness)
        self.mode.currentIndexChanged.connect(self._update_readiness)
        self.profile.currentIndexChanged.connect(self._update_readiness)
        close_button.clicked.connect(self.accept)
        self.refresh()

    def start_campaign(self) -> None:
        campaign = self._draft_campaign()
        try:
            self.repository.start_campaign(campaign)
        except ValueError as exc:
            self.active_status.setText(self.text["invalid"].format(error=exc))
            self.active_status.setStyleSheet(
                semantic_style("danger", bold=True, size_px=15)
            )
            return
        self.refresh()

    def _draft_campaign(self) -> MeasurementCampaign:
        return MeasurementCampaign(
            id=None,
            name=self.name.text(),
            objective=self.objective.text(),
            tx_call=self.callsign.text(),
            tx_grid=self.tx_grid.text(),
            band=self.band.currentText(),
            mode=self.mode.currentText(),
            antenna_profile_id=self.profile.currentData(),
            antenna_profile_name=self.profile.currentText(),
            notes=self.notes.toPlainText(),
            started_at=datetime.now(timezone.utc),
            target_spots=self.target_spots.value(),
            target_receivers=self.target_receivers.value(),
            target_sectors=self.target_sectors.value(),
            target_time_blocks=self.target_blocks.value(),
        )

    def stop_campaign(self) -> None:
        active = self.repository.active_campaign()
        if active is not None and active.id is not None:
            self.repository.finish_campaign(active.id)
        self.refresh()

    def _selection_changed(self) -> None:
        count = len(self.table.selectionModel().selectedRows())
        self.coverage_button.setEnabled(count == 1)
        self.diary_button.setEnabled(count == 1)
        self.attachments_button.setEnabled(count == 1)
        self.compare_button.setEnabled(count == 2)

    def _selected_campaign_ids(self) -> list[int]:
        campaign_ids = []
        for index in sorted(
            self.table.selectionModel().selectedRows(),
            key=lambda item: item.row(),
        ):
            item = self.table.item(index.row(), 0)
            campaign_id = item.data(Qt.ItemDataRole.UserRole) if item else None
            if campaign_id is not None:
                campaign_ids.append(int(campaign_id))
        return campaign_ids

    def _selected_campaign_id(self) -> int | None:
        campaign_ids = self._selected_campaign_ids()
        return campaign_ids[0] if len(campaign_ids) == 1 else None

    def open_selected_coverage(self) -> None:
        campaign_id = self._selected_campaign_id()
        if campaign_id is None:
            return
        self.coverage_campaign_id = campaign_id
        self.accept()

    def open_selected_diary(self) -> None:
        campaign_id = self._selected_campaign_id()
        if campaign_id is None:
            return
        CampaignLogDialog(
            self.repository,
            campaign_id,
            self.language,
            self,
        ).exec()

    def open_selected_attachments(self) -> None:
        campaign_id = self._selected_campaign_id()
        if campaign_id is None:
            return
        CampaignAttachmentsDialog(
            self.repository,
            campaign_id,
            self.language,
            self,
        ).exec()

    def open_selected_comparison(self) -> None:
        campaign_ids = self._selected_campaign_ids()
        if len(campaign_ids) != 2:
            return
        campaign_a, campaign_b = (
            self.repository.get_campaign(campaign_id)
            for campaign_id in campaign_ids
        )
        CampaignComparisonDialog(
            campaign_a,
            self._campaign_located(campaign_a),
            campaign_b,
            self._campaign_located(campaign_b),
            self.language,
            self,
        ).exec()

    def _update_readiness(self, *_args) -> None:
        if not hasattr(self, "readiness"):
            return
        profile_power_w = None
        profile_id = self.profile.currentData()
        if profile_id is not None:
            try:
                profile_power_w = self.repository.get_antenna_profile(
                    profile_id
                ).power_w
            except ValueError:
                pass
        check = assess_campaign_metadata(self._draft_campaign(), profile_power_w)
        if check.complete:
            self.readiness.setText(
                self.text["readiness_complete"].format(percent=check.percent)
            )
            color = TOKENS.success
        else:
            missing = ", ".join(self.text["metadata"][key] for key in check.missing)
            self.readiness.setText(
                self.text["readiness_missing"].format(
                    percent=check.percent,
                    missing=missing,
                )
            )
            color = TOKENS.warning if check.percent >= 70 else TOKENS.danger
        self.readiness.setStyleSheet(f"color: {color}; font-weight: 700;")

    def refresh(self) -> None:
        active = self.repository.active_campaign()
        controls = (
            self.name,
            self.objective,
            self.callsign,
            self.tx_grid,
            self.band,
            self.mode,
            self.profile,
            self.notes,
            self.target_spots,
            self.target_receivers,
            self.target_sectors,
            self.target_blocks,
        )
        for control in controls:
            control.setEnabled(active is None)
        self.start_button.setEnabled(active is None)
        self.stop_button.setEnabled(active is not None)
        if active is None:
            self.active_status.setText(self.text["inactive"])
            self.active_status.setStyleSheet(
                semantic_style("text_secondary", bold=True, size_px=15)
            )
        else:
            self.active_status.setText(
                self.text["active"].format(
                    name=active.name,
                    band=active.band,
                    mode=active.mode,
                    started=active.started_at.astimezone(timezone.utc).strftime(
                        "%Y-%m-%d %H:%M UTC"
                    ),
                )
            )
            self.active_status.setStyleSheet(
                semantic_style("success", bold=True, size_px=15)
            )
        self._update_readiness()

        campaigns = self.repository.list_campaigns()
        self.table.setRowCount(len(campaigns))
        for row, campaign in enumerate(campaigns):
            progress = self._campaign_progress(campaign)
            values = (
                campaign.started_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M"),
                (
                    self.text["running"]
                    if campaign.active
                    else campaign.ended_at.astimezone(timezone.utc).strftime(
                        "%Y-%m-%d %H:%M"
                    )
                ),
                campaign.name,
                campaign.band,
                campaign.mode,
                campaign.antenna_profile_name or self.text["no_profile"],
                str(campaign.spot_count),
                str(campaign.unique_receivers),
                str(campaign.tx_session_count),
                (
                    self.text["progress_complete"]
                    if progress.complete
                    else self.text["progress_incomplete"].format(
                        met=progress.met_count
                    )
                ),
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, campaign.id)
                if column in (6, 7, 8):
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                if column == 9:
                    item.setForeground(
                        QColor(TOKENS.success if progress.complete else TOKENS.warning)
                    )
                    item.setToolTip(
                        self.text["progress_tip"].format(
                            spots=progress.spot_count,
                            target_spots=campaign.target_spots,
                            receivers=progress.unique_receivers,
                            target_receivers=campaign.target_receivers,
                            sectors=progress.supported_sector_count,
                            target_sectors=campaign.target_sectors,
                            blocks=progress.time_block_count,
                            target_blocks=campaign.target_time_blocks,
                        )
                    )
                self.table.setItem(row, column, item)
        self.table.resizeColumnsToContents()

    def _campaign_progress(self, campaign):
        return assess_campaign_progress(campaign, self._campaign_located(campaign))

    def _campaign_located(self, campaign):
        located = [
            item
            for spot in self.repository.list_spots(campaign_id=campaign.id)
            if (item := locate_spot(spot, campaign.tx_grid))
        ]
        return located
