from __future__ import annotations

from datetime import timezone

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTableWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .design_system import DataPanel, MetricItem, PanelHeader, StatusIndicator
from .propagation import (
    IMAGE_SOURCES,
    NoaaSwpcClient,
    PropagationBundle,
    PropagationDataError,
    condition_summary,
    freshness_text,
)
from .storage import SpotRepository
from .theme import semantic_style
from .ui_formatting import TechnicalTableItem


TEXT = {
    "CZE": {
        "title": "Podmínky šíření",
        "intro": (
            "Aktuální kosmické počasí poskytuje kontext k naměřenému pokrytí. "
            "Nejde o předpověď konkrétního spojení ani o korekci zisku antény."
        ),
        "campaign": "Kampaň:",
        "no_campaign": "— Bez kampaně —",
        "refresh": "Obnovit z NOAA",
        "save": "Uložit snapshot ke kampani",
        "refresh_tip": (
            "Výslovně stáhne aktuální data a obrázky z oficiální služby NOAA "
            "Space Weather Prediction Center."
        ),
        "overview": "Přehled",
        "images": "Obrazové produkty",
        "timeline": "Časová osa kampaně",
        "measurements": "Pozorované ukazatele",
        "interpretation": "Orientační význam pro KV",
        "workflow_title": "Doporučený postup",
        "workflow": (
            "1. Obnovte podmínky před začátkem měření.  "
            "2. Uložte snapshot ke kampani.  "
            "3. Obnovu opakujte při výrazné změně Kp, R/S/G nebo počasí "
            "slunečního větru. Kampaně z výrazně odlišných podmínek "
            "neporovnávejte bez upozornění."
        ),
        "source_note": (
            "Zdroj: NOAA Space Weather Prediction Center · všechny časy UTC · "
            "„—“ znamená, že zdroj hodnotu neposkytl."
        ),
        "waiting": "Načítám data NOAA…",
        "no_cache": (
            "Zatím není uložena místní cache. Data se stáhnou pouze po stisku "
            "„Obnovit z NOAA“."
        ),
        "loaded_cache": "Zobrazena místní cache NOAA.",
        "loaded_live": "Aktuální data NOAA byla načtena.",
        "partial": "Část zdrojů není dostupná; použita byla dostupná cache.",
        "failed": "Data NOAA nelze načíst a použitelná cache není k dispozici.",
        "saved": "Snapshot podmínek byl uložen ke kampani „{name}“.",
        "select_campaign": "Před uložením vyberte kampaň.",
        "no_snapshot": "Nejprve načtěte nebo obnovte data NOAA.",
        "metrics": {
            "kp": "Planetární Kp",
            "f107": "Tok F10.7",
            "sunspots": "Číslo skvrn",
            "speed": "Sluneční vítr",
            "bt": "IMF Bt",
            "bz": "IMF Bz",
            "scales": "NOAA stupnice",
            "observed": "Pozorováno",
            "fetched": "Staženo",
        },
        "metric_tips": {
            "kp": "Tříhodinový planetární index geomagnetické aktivity (0–9).",
            "f107": "Tok na 10,7 cm v jednotkách solar flux unit (sfu).",
            "sunspots": "Poslední dostupný pozorovaný měsíční index NOAA.",
            "speed": "Rychlost slunečního větru u L1 v km/s.",
            "bt": "Celková velikost meziplanetárního magnetického pole v nT.",
            "bz": "Severojižní složka IMF; déle trvající záporná hodnota může zvyšovat geomagnetickou aktivitu.",
            "scales": "R = rádiové výpadky, S = radiační bouře, G = geomagnetické bouře.",
            "observed": "Nejnovější čas obsažený v použitých datových produktech.",
            "fetched": "Čas stažení a uložení lokální cache.",
        },
        "image_titles": {
            "drap": "D‑RAP · absorpce v D-vrstvě",
            "aurora": "Aurorální ovál · 30min předpověď",
            "sun": "Slunce · GOES SUVI 195 Å",
        },
        "image_empty": "Obrázek není v cache.",
        "image_source": "NOAA SWPC · {url}",
        "timeline_empty": "Pro vybranou kampaň nejsou uložené snapshoty.",
        "timeline_headers": [
            "Pozorováno UTC",
            "Kp",
            "F10.7",
            "SSN",
            "Vítr km/s",
            "Bz nT",
            "R / S / G",
            "Stav",
        ],
        "current": "aktuální",
        "stale": "zastaralé",
        "close": "Zavřít",
    },
    "ENG": {
        "title": "Propagation conditions",
        "intro": (
            "Current space weather provides context for measured coverage. "
            "It is not a point-to-point forecast or an antenna-gain correction."
        ),
        "campaign": "Campaign:",
        "no_campaign": "— No campaign —",
        "refresh": "Refresh from NOAA",
        "save": "Save snapshot to campaign",
        "refresh_tip": (
            "Explicitly downloads current data and images from the official NOAA "
            "Space Weather Prediction Center service."
        ),
        "overview": "Overview",
        "images": "Image products",
        "timeline": "Campaign timeline",
        "measurements": "Observed indicators",
        "interpretation": "Indicative HF meaning",
        "workflow_title": "Recommended workflow",
        "workflow": (
            "1. Refresh conditions before measuring.  "
            "2. Save the snapshot to the campaign.  "
            "3. Refresh again after a substantial Kp, R/S/G, or solar-wind "
            "change. Do not compare campaigns from substantially different "
            "conditions without a warning."
        ),
        "source_note": (
            "Source: NOAA Space Weather Prediction Center · all times UTC · "
            "“—” means the source did not provide a value."
        ),
        "waiting": "Loading NOAA data…",
        "no_cache": (
            "No local cache exists yet. Data are downloaded only after pressing "
            "“Refresh from NOAA”."
        ),
        "loaded_cache": "Showing the local NOAA cache.",
        "loaded_live": "Current NOAA data were loaded.",
        "partial": "Some sources are unavailable; available cached data are shown.",
        "failed": "NOAA data cannot be loaded and no usable cache exists.",
        "saved": "The conditions snapshot was saved to campaign “{name}”.",
        "select_campaign": "Select a campaign before saving.",
        "no_snapshot": "Load or refresh NOAA data first.",
        "metrics": {
            "kp": "Planetary Kp",
            "f107": "F10.7 flux",
            "sunspots": "Sunspot number",
            "speed": "Solar wind",
            "bt": "IMF Bt",
            "bz": "IMF Bz",
            "scales": "NOAA scales",
            "observed": "Observed",
            "fetched": "Fetched",
        },
        "metric_tips": {
            "kp": "Three-hour planetary geomagnetic activity index (0–9).",
            "f107": "10.7 cm radio flux in solar flux units (sfu).",
            "sunspots": "Latest available observed monthly NOAA index.",
            "speed": "Solar-wind speed at L1 in km/s.",
            "bt": "Total interplanetary magnetic-field magnitude in nT.",
            "bz": "North-south IMF component; sustained negative values can increase geomagnetic activity.",
            "scales": "R = radio blackouts, S = radiation storms, G = geomagnetic storms.",
            "observed": "Newest timestamp contained in the data products used.",
            "fetched": "Time the local cache was downloaded and stored.",
        },
        "image_titles": {
            "drap": "D‑RAP · D-region absorption",
            "aurora": "Auroral oval · 30-minute forecast",
            "sun": "Sun · GOES SUVI 195 Å",
        },
        "image_empty": "The image is not cached.",
        "image_source": "NOAA SWPC · {url}",
        "timeline_empty": "No snapshots are stored for the selected campaign.",
        "timeline_headers": [
            "Observed UTC",
            "Kp",
            "F10.7",
            "SSN",
            "Wind km/s",
            "Bz nT",
            "R / S / G",
            "State",
        ],
        "current": "current",
        "stale": "stale",
        "close": "Close",
    },
}


_ACTIVE_THREADS: set[QThread] = set()


class PropagationFetchThread(QThread):
    result_ready = Signal(object)
    failed = Signal(str)

    def __init__(self, client: NoaaSwpcClient):
        super().__init__()
        self.client = client

    def run(self) -> None:
        try:
            self.result_ready.emit(self.client.fetch_current())
        except PropagationDataError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # Defensive boundary around a network worker.
            self.failed.emit(str(exc))


class ImageProductPanel(QGroupBox):
    def __init__(self, title: str, source_url: str, empty_text: str, parent=None):
        super().__init__(title, parent)
        self._pixmap = QPixmap()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 12)
        layout.setSpacing(8)
        self.image = QLabel(empty_text)
        self.image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image.setMinimumSize(260, 190)
        self.image.setWordWrap(True)
        self.image.setAccessibleName(title)
        layout.addWidget(self.image, 1)
        self.source = QLabel(source_url)
        self.source.setWordWrap(True)
        self.source.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByKeyboard
            | Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.source.setStyleSheet(semantic_style("text_muted"))
        self.source.setToolTip(source_url)
        layout.addWidget(self.source)

    def set_content(self, content: bytes | None, empty_text: str) -> None:
        pixmap = QPixmap()
        if content:
            pixmap.loadFromData(content)
        self._pixmap = pixmap
        if pixmap.isNull():
            self.image.setPixmap(QPixmap())
            self.image.setText(empty_text)
        else:
            self.image.clear()
            self._rescale()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._rescale()

    def _rescale(self) -> None:
        if self._pixmap.isNull():
            return
        size = self.image.contentsRect().size()
        if size.width() < 1 or size.height() < 1:
            return
        self.image.setPixmap(
            self._pixmap.scaled(
                size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )


class PropagationConditionsDialog(QDialog):
    def __init__(
        self,
        repository: SpotRepository,
        language: str,
        parent=None,
        *,
        client: NoaaSwpcClient | None = None,
    ):
        super().__init__(parent)
        self.repository = repository
        self.language = language if language in TEXT else "CZE"
        self.text = TEXT[self.language]
        cache_path = (
            repository.path.parent
            / f"{repository.path.stem}-propagation-cache"
        )
        self.client = client or NoaaSwpcClient(cache_path)
        self.bundle: PropagationBundle | None = None
        self._worker: PropagationFetchThread | None = None

        self.setWindowTitle(self.text["title"])
        self.resize(1180, 760)
        self.setMinimumSize(900, 620)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(12)

        intro = QLabel(self.text["intro"])
        intro.setWordWrap(True)
        intro.setStyleSheet(semantic_style("text_secondary"))
        outer.addWidget(intro)

        controls = QHBoxLayout()
        controls.setSpacing(8)
        campaign_label = QLabel(self.text["campaign"])
        self.campaign = QComboBox()
        campaign_label.setBuddy(self.campaign)
        self.campaign.setMinimumContentsLength(24)
        self.campaign.setAccessibleName(self.text["campaign"])
        self.refresh_button = QPushButton(self.text["refresh"])
        self.refresh_button.setObjectName("primaryAction")
        self.refresh_button.setToolTip(self.text["refresh_tip"])
        self.refresh_button.setAccessibleDescription(self.text["refresh_tip"])
        self.save_button = QPushButton(self.text["save"])
        self.save_button.setEnabled(False)
        controls.addWidget(campaign_label)
        controls.addWidget(self.campaign, 1)
        controls.addWidget(self.save_button)
        controls.addWidget(self.refresh_button)
        outer.addLayout(controls)

        self.status = StatusIndicator("NOAA SWPC", "inactive", self.text["no_cache"])
        self.status.set_indicator(
            "NOAA SWPC",
            "inactive",
            self.text["no_cache"],
            self.text["no_cache"],
        )
        self.status.setWordWrap(True)
        outer.addWidget(self.status)

        self.tabs = QTabWidget()
        self.tabs.setAccessibleName(self.text["title"])
        self.tabs.addTab(self._build_overview_tab(), self.text["overview"])
        self.tabs.addTab(self._build_images_tab(), self.text["images"])
        self.tabs.addTab(self._build_timeline_tab(), self.text["timeline"])
        outer.addWidget(self.tabs, 1)

        source_note = QLabel(self.text["source_note"])
        source_note.setWordWrap(True)
        source_note.setStyleSheet(semantic_style("text_secondary"))
        outer.addWidget(source_note)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Close).setText(
            self.text["close"]
        )
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

        self.refresh_button.clicked.connect(self.refresh_from_noaa)
        self.save_button.clicked.connect(self.save_snapshot)
        self.campaign.currentIndexChanged.connect(self._campaign_changed)
        self._load_campaigns()

        cached = self.client.load_cached()
        if cached is not None:
            self._show_bundle(cached, from_network=False)
        else:
            self._show_empty_values()
            self.refresh_timeline()

    def _build_overview_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        metrics_panel = DataPanel()
        metrics_layout = QVBoxLayout(metrics_panel)
        metrics_layout.setContentsMargins(16, 12, 16, 12)
        metrics_layout.setSpacing(8)
        metrics_layout.addWidget(PanelHeader(self.text["measurements"]))
        metric_grid = QGridLayout()
        metric_grid.setContentsMargins(0, 0, 0, 0)
        metric_grid.setHorizontalSpacing(20)
        metric_grid.setVerticalSpacing(10)
        self.metrics: dict[str, MetricItem] = {}
        for index, key in enumerate(
            ("kp", "f107", "sunspots", "speed", "bt", "bz", "scales", "observed", "fetched")
        ):
            item = MetricItem()
            self.metrics[key] = item
            metric_grid.addWidget(item, index // 2, index % 2)
        metrics_layout.addLayout(metric_grid)
        metrics_layout.addStretch(1)

        meaning_panel = DataPanel()
        meaning_layout = QVBoxLayout(meaning_panel)
        meaning_layout.setContentsMargins(16, 12, 16, 12)
        meaning_layout.setSpacing(8)
        meaning_layout.addWidget(PanelHeader(self.text["interpretation"]))
        self.meaning = QLabel()
        self.meaning.setWordWrap(True)
        self.meaning.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        self.meaning.setAccessibleName(self.text["interpretation"])
        meaning_layout.addWidget(self.meaning, 1)

        splitter.addWidget(metrics_panel)
        splitter.addWidget(meaning_panel)
        splitter.setSizes([620, 420])
        splitter.setChildrenCollapsible(False)
        layout.addWidget(splitter, 3)
        layout.addWidget(PanelHeader(self.text["workflow_title"]))
        workflow = QLabel(self.text["workflow"])
        workflow.setWordWrap(True)
        workflow.setStyleSheet(semantic_style("text_secondary"))
        workflow.setAccessibleName(self.text["workflow_title"])
        layout.addWidget(workflow)
        return page

    def _build_images_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        grid = QGridLayout(content)
        grid.setContentsMargins(12, 12, 12, 12)
        grid.setSpacing(12)
        self.image_panels: dict[str, ImageProductPanel] = {}
        for column, key in enumerate(("drap", "aurora", "sun")):
            url = IMAGE_SOURCES[key]
            panel = ImageProductPanel(
                self.text["image_titles"][key],
                self.text["image_source"].format(url=url),
                self.text["image_empty"],
            )
            self.image_panels[key] = panel
            grid.addWidget(panel, 0, column)
            grid.setColumnStretch(column, 1)
        scroll.setWidget(content)
        layout.addWidget(scroll)
        return page

    def _build_timeline_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        self.timeline_table = QTableWidget(0, 8)
        self.timeline_table.setHorizontalHeaderLabels(
            self.text["timeline_headers"]
        )
        self.timeline_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.timeline_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.timeline_table.setAlternatingRowColors(True)
        self.timeline_table.setSortingEnabled(True)
        self.timeline_table.setAccessibleName(self.text["timeline"])
        self.timeline_table.verticalHeader().setVisible(False)
        header = self.timeline_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(True)
        layout.addWidget(self.timeline_table, 1)
        self.timeline_message = QLabel()
        self.timeline_message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timeline_message.setStyleSheet(semantic_style("text_muted"))
        layout.addWidget(self.timeline_message)
        return page

    def _load_campaigns(self) -> None:
        selected_id = self.campaign.currentData()
        self.campaign.blockSignals(True)
        self.campaign.clear()
        self.campaign.addItem(self.text["no_campaign"], None)
        campaigns = self.repository.list_campaigns()
        active_id = None
        for campaign in campaigns:
            suffix = " · active" if campaign.active and self.language == "ENG" else ""
            suffix = " · aktivní" if campaign.active and self.language == "CZE" else suffix
            self.campaign.addItem(
                f"{campaign.name} · {campaign.band} {campaign.mode}{suffix}",
                campaign.id,
            )
            if campaign.active:
                active_id = campaign.id
        target_id = selected_id if selected_id is not None else active_id
        if target_id is not None:
            index = self.campaign.findData(target_id)
            if index >= 0:
                self.campaign.setCurrentIndex(index)
        self.campaign.blockSignals(False)
        self._campaign_changed()

    def _campaign_changed(self) -> None:
        self.save_button.setEnabled(
            self.bundle is not None and self.campaign.currentData() is not None
        )
        self.refresh_timeline()

    def refresh_from_noaa(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            return
        self.refresh_button.setEnabled(False)
        self.save_button.setEnabled(False)
        self._set_status("connecting", self.text["waiting"])
        worker = PropagationFetchThread(self.client)
        self._worker = worker
        _ACTIVE_THREADS.add(worker)
        worker.result_ready.connect(self._network_result)
        worker.failed.connect(self._network_failed)
        worker.finished.connect(
            lambda current=worker: _ACTIVE_THREADS.discard(current)
        )
        worker.finished.connect(worker.deleteLater)
        worker.start()

    def _network_result(self, bundle: PropagationBundle) -> None:
        self._show_bundle(bundle, from_network=True)
        self.refresh_button.setEnabled(True)
        self._worker = None

    def _network_failed(self, detail: str) -> None:
        self._set_status("error", self.text["failed"], detail)
        self.refresh_button.setEnabled(True)
        self.save_button.setEnabled(
            self.bundle is not None and self.campaign.currentData() is not None
        )
        self._worker = None

    def _show_bundle(
        self,
        bundle: PropagationBundle,
        *,
        from_network: bool,
    ) -> None:
        self.bundle = bundle
        snapshot = bundle.snapshot
        freshness_role, freshness = freshness_text(snapshot, self.language)
        if bundle.errors:
            message = f"{self.text['partial']} {freshness}"
            self._set_status("warning", message, "\n".join(bundle.errors))
        else:
            lead = self.text["loaded_live"] if from_network else self.text["loaded_cache"]
            self._set_status(freshness_role, f"{lead} {freshness}")
        metric_values = {
            "kp": _value(snapshot.kp_index, 1),
            "f107": _unit(snapshot.f107_sfu, "sfu", 0),
            "sunspots": _value(snapshot.sunspot_number, 0),
            "speed": _unit(snapshot.solar_wind_speed_kms, "km/s", 0),
            "bt": _signed_unit(snapshot.imf_bt_nt, "nT", 1),
            "bz": _signed_unit(snapshot.imf_bz_nt, "nT", 1),
            "scales": (
                f"R{_scale(snapshot.radio_blackout_scale)} / "
                f"S{_scale(snapshot.solar_radiation_scale)} / "
                f"G{_scale(snapshot.geomagnetic_scale)}"
            ),
            "observed": _utc(snapshot.observed_at),
            "fetched": _utc(snapshot.fetched_at),
        }
        for key, item in self.metrics.items():
            item.set_metric(
                self.text["metrics"][key],
                metric_values[key],
                self.text["metric_tips"][key],
            )
        meaning_role, meaning = condition_summary(snapshot, self.language)
        self.meaning.setText(meaning)
        self.meaning.setProperty("statusRole", meaning_role)
        self.meaning.style().unpolish(self.meaning)
        self.meaning.style().polish(self.meaning)
        for key, panel in self.image_panels.items():
            panel.set_content(bundle.images.get(key), self.text["image_empty"])
        self._campaign_changed()

    def _show_empty_values(self) -> None:
        for key, item in self.metrics.items():
            item.set_metric(
                self.text["metrics"][key],
                "—",
                self.text["metric_tips"][key],
            )
        self.meaning.setText(self.text["no_cache"])
        for panel in self.image_panels.values():
            panel.set_content(None, self.text["image_empty"])

    def save_snapshot(self) -> None:
        if self.bundle is None:
            self._set_status("warning", self.text["no_snapshot"])
            return
        campaign_id = self.campaign.currentData()
        if campaign_id is None:
            self._set_status("warning", self.text["select_campaign"])
            return
        saved = self.repository.save_propagation_snapshot(
            int(campaign_id),
            self.bundle.snapshot,
        )
        campaign = self.repository.get_campaign(int(campaign_id))
        self._set_status(
            "success",
            self.text["saved"].format(name=campaign.name),
            saved.payload_sha256,
        )
        self.refresh_timeline()

    def _set_status(self, state: str, message: str, detail: str = "") -> None:
        self.status.set_indicator(
            "NOAA SWPC",
            state,
            detail or message,
            message,
        )

    def refresh_timeline(self) -> None:
        campaign_id = self.campaign.currentData()
        snapshots = (
            self.repository.list_propagation_snapshots(int(campaign_id))
            if campaign_id is not None
            else []
        )
        self.timeline_table.setSortingEnabled(False)
        self.timeline_table.setRowCount(len(snapshots))
        for row, snapshot in enumerate(snapshots):
            values = (
                _utc(snapshot.observed_at),
                _value(snapshot.kp_index, 1),
                _value(snapshot.f107_sfu, 0),
                _value(snapshot.sunspot_number, 0),
                _value(snapshot.solar_wind_speed_kms, 0),
                _signed_value(snapshot.imf_bz_nt, 1),
                (
                    f"R{_scale(snapshot.radio_blackout_scale)} / "
                    f"S{_scale(snapshot.solar_radiation_scale)} / "
                    f"G{_scale(snapshot.geomagnetic_scale)}"
                ),
                self.text["stale"] if snapshot.stale else self.text["current"],
            )
            for column, value in enumerate(values):
                sort_values = (
                    snapshot.observed_at.timestamp(),
                    snapshot.kp_index,
                    snapshot.f107_sfu,
                    snapshot.sunspot_number,
                    snapshot.solar_wind_speed_kms,
                    snapshot.imf_bz_nt,
                    value,
                    int(snapshot.stale),
                )
                item = TechnicalTableItem(
                    value,
                    sort_value=(
                        sort_values[column]
                        if sort_values[column] is not None
                        else float("-inf")
                    ),
                    numeric=column in (1, 2, 3, 4, 5),
                )
                self.timeline_table.setItem(row, column, item)
        self.timeline_table.setSortingEnabled(True)
        self.timeline_message.setText(
            self.text["timeline_empty"] if not snapshots else ""
        )


def _utc(value) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M")


def _value(value: float | None, decimals: int) -> str:
    return "—" if value is None else f"{value:.{decimals}f}"


def _signed_value(value: float | None, decimals: int) -> str:
    return "—" if value is None else f"{value:+.{decimals}f}"


def _unit(value: float | None, unit: str, decimals: int) -> str:
    raw = _value(value, decimals)
    return raw if raw == "—" else f"{raw} {unit}"


def _signed_unit(value: float | None, unit: str, decimals: int) -> str:
    raw = _signed_value(value, decimals)
    return raw if raw == "—" else f"{raw} {unit}"


def _scale(value: int | None) -> str:
    return "—" if value is None else str(value)
