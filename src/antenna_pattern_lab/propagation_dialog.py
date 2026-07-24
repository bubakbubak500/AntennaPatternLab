from __future__ import annotations

from datetime import datetime, timezone

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.dates import AutoDateLocator, ConciseDateFormatter
from matplotlib.figure import Figure
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtCore import QUrl
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
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTableWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .design_system import DataPanel, MetricItem, PanelHeader, StatusIndicator
from .ionosphere import (
    GIRO_LICENSE,
    GIRO_LICENSE_URL,
    GiroDidbaseClient,
    IonosphereBundle,
    band_usability,
)
from .geo import distance_and_bearing, maidenhead_to_latlon
from .propagation import (
    IMAGE_SOURCES,
    NoaaSwpcClient,
    PropagationBundle,
    PropagationDataError,
    SeriesPoint,
    attach_ionosphere,
    condition_summary,
    freshness_text,
    ionosphere_from_snapshot,
    operational_context,
)
from .storage import SpotRepository
from .theme import TOKENS, apply_figure_theme, semantic_style
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
        "trends": "Trendy 24 h",
        "planning": "Upozornění a prognóza",
        "ionosphere": "Ionosféra",
        "analysis": "Srovnatelnost kampaně",
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
            "glotec": "GloTEC · globální TEC (model)",
        },
        "image_empty": "Obrázek není v cache.",
        "image_source": "NOAA SWPC · {url}",
        "drap_frequency": "Modelová frekvence D‑RAP:",
        "drap_history": "Otevřít historii/animaci D‑RAP",
        "image_metadata": "Model / předpověď · NOAA SWPC · snímek stažen {time} UTC",
        "timeline_empty": "Pro vybranou kampaň nejsou uložené snapshoty.",
        "load_snapshot": "Načíst vybraný historický snapshot",
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
        "flare": "Erupce: nyní {current}, maximum {peak} · {begin} / {maximum} / {end}",
        "proton": "Protony ≥10 MeV · NOAA S{scale}; S1 začíná na 10 pfu. Zvýšení může způsobit polární absorpci.",
        "trend_empty": "Časové řady nejsou v cache.",
        "alerts_headers": ["Vydáno UTC", "Typ", "Bulletin"],
        "forecast_headers": ["Den UTC", "Kp max", "Ap", "F10.7", "M %", "X %", "Proton %"],
        "cme": "Předpověď / model · {source} · očekávaný průchod u Země {arrival} · rychlost {speed} · zásah {impact}",
        "observation": "Pozorování",
        "forecast": "Předpověď",
        "model": "Model",
        "giro_note": (
            "GIRO/DIDBase · {license}. Automatická měření mohou obsahovat chyby; "
            "CS 999 označuje ruční validaci. TEC ani MUF nejsou mírou zisku antény "
            "a nesmějí samy korigovat SNR."
        ),
        "ionosphere_headers": [
            "Stanice", "Pozorováno UTC", "CS", "foF2 MHz", "MUF(3000) MHz",
            "hmF2 km", "Škálování", "Vzdálenost",
        ],
        "open_ionogram": "Otevřít ionogram",
        "target_grid": "Cílový lokátor:",
        "target_grid_tip": "Volitelný Maidenhead lokátor cílové oblasti pro výběr další blízké ionosondy.",
        "band_headers": ["Pásmo", "Orientační stav"],
        "band_states": {
            "supported": "pod MUF s rezervou",
            "marginal": "blízko MUF",
            "above_muf": "nad pozorovanou MUF",
            "unknown": "bez podkladu",
        },
        "analysis_headers": ["UTC blok", "Reporty", "RX", "TX", "Medián SNR", "Δ SNR", "Podmínky", "Přímé A/B"],
        "sensitivity_headers": ["Vynecháno", "Hodnota", "Zbývá", "Max změna sektoru"],
        "yes": "ano",
        "no": "ne",
        "analysis_terms": {
            "receiver_network_changed": "změna sítě RX",
            "conditions_not_comparable": "podmínky nejsou srovnatelné",
            "mixed_band_mode_or_power": "smíšené pásmo, mód nebo výkon",
            "missing_conditions": "chybí podmínky",
            "stale_conditions": "zastaralé podmínky",
            "geomagnetic_disturbance": "geomagnetická porucha",
            "radio_blackout": "rádiový výpadek",
            "polar_cap_absorption_risk": "riziko polární absorpce",
            "receiver": "přijímač",
            "time": "čas",
            "direction": "směr",
        },
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
        "trends": "24 h trends",
        "planning": "Alerts and forecast",
        "ionosphere": "Ionosphere",
        "analysis": "Campaign comparability",
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
            "glotec": "GloTEC · global TEC (model)",
        },
        "image_empty": "The image is not cached.",
        "image_source": "NOAA SWPC · {url}",
        "drap_frequency": "D‑RAP model frequency:",
        "drap_history": "Open D‑RAP history/animation",
        "image_metadata": "Model / forecast · NOAA SWPC · image fetched {time} UTC",
        "timeline_empty": "No snapshots are stored for the selected campaign.",
        "load_snapshot": "Load selected historical snapshot",
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
        "flare": "Flare: current {current}, peak {peak} · {begin} / {maximum} / {end}",
        "proton": "Protons ≥10 MeV · NOAA S{scale}; S1 starts at 10 pfu. Elevated flux can cause polar-cap absorption.",
        "trend_empty": "No time series are cached.",
        "alerts_headers": ["Issued UTC", "Type", "Bulletin"],
        "forecast_headers": ["Day UTC", "Kp max", "Ap", "F10.7", "M %", "X %", "Proton %"],
        "cme": "Forecast / model · {source} · expected passage at Earth {arrival} · speed {speed} · impact {impact}",
        "observation": "Observation",
        "forecast": "Forecast",
        "model": "Model",
        "giro_note": (
            "GIRO/DIDBase · {license}. Autoscaled measurements can contain errors; "
            "CS 999 marks manual validation. TEC and MUF are not antenna-gain "
            "measures and must not by themselves correct SNR."
        ),
        "ionosphere_headers": [
            "Station", "Observed UTC", "CS", "foF2 MHz", "MUF(3000) MHz",
            "hmF2 km", "Scaling", "Distance",
        ],
        "open_ionogram": "Open ionogram",
        "target_grid": "Target locator:",
        "target_grid_tip": "Optional target-area Maidenhead locator used to select another nearby ionosonde.",
        "band_headers": ["Band", "Indicative state"],
        "band_states": {
            "supported": "below MUF with margin",
            "marginal": "near MUF",
            "above_muf": "above observed MUF",
            "unknown": "no evidence",
        },
        "analysis_headers": ["UTC block", "Reports", "RX", "TX", "Median SNR", "Δ SNR", "Conditions", "Direct A/B"],
        "sensitivity_headers": ["Omitted", "Value", "Remaining", "Max sector change"],
        "yes": "yes",
        "no": "no",
        "analysis_terms": {
            "receiver_network_changed": "receiver network changed",
            "conditions_not_comparable": "conditions not comparable",
            "mixed_band_mode_or_power": "mixed band, mode or power",
            "missing_conditions": "conditions missing",
            "stale_conditions": "conditions stale",
            "geomagnetic_disturbance": "geomagnetic disturbance",
            "radio_blackout": "radio blackout",
            "polar_cap_absorption_risk": "polar-cap absorption risk",
            "receiver": "receiver",
            "time": "time",
            "direction": "direction",
        },
    },
}


_ACTIVE_THREADS: set[QThread] = set()


class PropagationFetchThread(QThread):
    result_ready = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        client: NoaaSwpcClient,
        giro_client: GiroDidbaseClient | None = None,
        tx_grid: str = "",
        target_grid: str = "",
    ):
        super().__init__()
        self.client = client
        self.giro_client = giro_client
        self.tx_grid = tx_grid
        self.target_grid = target_grid

    def run(self) -> None:
        try:
            bundle = self.client.fetch_current()
            if self.giro_client is not None and self.tx_grid:
                try:
                    ionosphere = self.giro_client.fetch_for_grids(
                        self.tx_grid,
                        self.target_grid,
                        station_limit=2,
                    )
                    bundle = attach_ionosphere(bundle, ionosphere)
                    if ionosphere.errors:
                        bundle = PropagationBundle(
                            bundle.snapshot,
                            bundle.images,
                            bundle.stale_keys,
                            bundle.errors + ionosphere.errors,
                            ionosphere,
                        )
                except Exception as exc:
                    bundle = PropagationBundle(
                        bundle.snapshot,
                        bundle.images,
                        bundle.stale_keys,
                        bundle.errors + (f"GIRO: {exc}",),
                    )
            self.result_ready.emit(bundle)
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
        giro_client: GiroDidbaseClient | None = None,
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
        self.giro_client = giro_client or GiroDidbaseClient(
            cache_path=cache_path / "giro"
        )
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
        self.tabs.addTab(self._build_trends_tab(), self.text["trends"])
        self.tabs.addTab(self._build_planning_tab(), self.text["planning"])
        self.tabs.addTab(self._build_ionosphere_tab(), self.text["ionosphere"])
        self.tabs.addTab(self._build_images_tab(), self.text["images"])
        self.tabs.addTab(self._build_timeline_tab(), self.text["timeline"])
        self.tabs.addTab(self._build_analysis_tab(), self.text["analysis"])
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
        controls = QHBoxLayout()
        controls.setContentsMargins(12, 12, 12, 0)
        drap_label = QLabel(self.text["drap_frequency"])
        self.drap_frequency = QComboBox()
        drap_label.setBuddy(self.drap_frequency)
        for frequency in (5, 10, 15, 20, 25, 30):
            self.drap_frequency.addItem(
                f"{frequency} MHz",
                f"drap_{frequency:02d}",
            )
        self.drap_frequency.setCurrentIndex(1)
        self.drap_frequency.currentIndexChanged.connect(self._drap_changed)
        history = QPushButton(self.text["drap_history"])
        history.clicked.connect(
            lambda: QDesktopServices.openUrl(
                QUrl("https://www.swpc.noaa.gov/products/d-region-absorption-predictions-d-rap")
            )
        )
        controls.addWidget(drap_label)
        controls.addWidget(self.drap_frequency)
        controls.addWidget(history)
        controls.addStretch(1)
        layout.addLayout(controls)
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
        self.image_metadata = QLabel()
        self.image_metadata.setContentsMargins(12, 0, 12, 8)
        self.image_metadata.setStyleSheet(semantic_style("text_secondary"))
        layout.addWidget(self.image_metadata)
        return page

    def _build_trends_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        self.trend_summary = QLabel(self.text["trend_empty"])
        self.trend_summary.setWordWrap(True)
        self.trend_summary.setStyleSheet(semantic_style("text_secondary"))
        layout.addWidget(self.trend_summary)
        self.trend_figure = Figure(
            figsize=(10, 6),
            facecolor=TOKENS.panel_background,
        )
        self.trend_canvas = FigureCanvasQTAgg(self.trend_figure)
        self.trend_canvas.setAccessibleName(self.text["trends"])
        layout.addWidget(self.trend_canvas, 1)
        return page

    def _build_planning_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        self.cme_summary = QLabel()
        self.cme_summary.setWordWrap(True)
        self.cme_summary.setStyleSheet(semantic_style("text_secondary"))
        layout.addWidget(self.cme_summary)
        splitter = QSplitter(Qt.Orientation.Vertical)
        self.alerts_table = self._technical_table(
            3, self.text["alerts_headers"], self.text["planning"]
        )
        self.alerts_table.cellDoubleClicked.connect(self._open_alert)
        self.forecast_table = self._technical_table(
            7, self.text["forecast_headers"], self.text["forecast"]
        )
        splitter.addWidget(self.alerts_table)
        splitter.addWidget(self.forecast_table)
        splitter.setSizes([260, 300])
        splitter.setChildrenCollapsible(False)
        layout.addWidget(splitter, 1)
        return page

    def _build_ionosphere_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        note = QLabel(
            self.text["giro_note"].format(license=GIRO_LICENSE)
            + f"  {GIRO_LICENSE_URL}"
        )
        note.setWordWrap(True)
        note.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        note.setStyleSheet(semantic_style("text_secondary"))
        layout.addWidget(note)
        target_row = QHBoxLayout()
        target_label = QLabel(self.text["target_grid"])
        self.target_grid = QLineEdit()
        self.target_grid.setMaximumWidth(140)
        self.target_grid.setPlaceholderText("JN79")
        self.target_grid.setToolTip(self.text["target_grid_tip"])
        self.target_grid.setAccessibleDescription(self.text["target_grid_tip"])
        target_label.setBuddy(self.target_grid)
        target_row.addWidget(target_label)
        target_row.addWidget(self.target_grid)
        target_row.addStretch(1)
        layout.addLayout(target_row)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.ionosphere_table = self._technical_table(
            8,
            self.text["ionosphere_headers"],
            self.text["ionosphere"],
        )
        self.band_table = self._technical_table(
            2,
            self.text["band_headers"],
            self.text["band_headers"][0],
        )
        splitter.addWidget(self.ionosphere_table)
        splitter.addWidget(self.band_table)
        splitter.setSizes([900, 220])
        splitter.setChildrenCollapsible(False)
        layout.addWidget(splitter, 1)
        actions = QHBoxLayout()
        self.ionogram_button = QPushButton(self.text["open_ionogram"])
        self.ionogram_button.setEnabled(False)
        self.ionogram_button.clicked.connect(self._open_ionogram)
        actions.addWidget(self.ionogram_button)
        actions.addStretch(1)
        layout.addLayout(actions)
        self.glotec_panel = ImageProductPanel(
            self.text["image_titles"]["glotec"],
            self.text["image_source"].format(url=IMAGE_SOURCES["glotec"]),
            self.text["image_empty"],
        )
        self.glotec_panel.setMaximumHeight(280)
        layout.addWidget(self.glotec_panel, 1)
        self.ionosphere_table.itemSelectionChanged.connect(
            self._ionosphere_selection_changed
        )
        return page

    def _build_analysis_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        self.analysis_warning = QLabel()
        self.analysis_warning.setWordWrap(True)
        self.analysis_warning.setStyleSheet(semantic_style("text_secondary"))
        layout.addWidget(self.analysis_warning)
        splitter = QSplitter(Qt.Orientation.Vertical)
        self.analysis_table = self._technical_table(
            8,
            self.text["analysis_headers"],
            self.text["analysis"],
        )
        self.sensitivity_table = self._technical_table(
            4,
            self.text["sensitivity_headers"],
            self.text["sensitivity_headers"][0],
        )
        splitter.addWidget(self.analysis_table)
        splitter.addWidget(self.sensitivity_table)
        splitter.setSizes([330, 180])
        splitter.setChildrenCollapsible(False)
        layout.addWidget(splitter, 1)
        return page

    @staticmethod
    def _technical_table(
        columns: int,
        headers: list[str],
        accessible_name: str,
    ) -> QTableWidget:
        table = QTableWidget(0, columns)
        table.setHorizontalHeaderLabels(headers)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setAlternatingRowColors(True)
        table.setSortingEnabled(True)
        table.setAccessibleName(accessible_name)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        table.horizontalHeader().setStretchLastSection(True)
        return table

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
        self.load_snapshot_button = QPushButton(self.text["load_snapshot"])
        self.load_snapshot_button.setEnabled(False)
        self.load_snapshot_button.clicked.connect(self._load_selected_snapshot)
        self.timeline_table.itemSelectionChanged.connect(
            lambda: self.load_snapshot_button.setEnabled(
                bool(self.timeline_table.selectedItems())
            )
        )
        layout.addWidget(self.load_snapshot_button)
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
        self.refresh_analysis()
        if self.bundle is not None:
            self._fill_ionosphere(self.bundle.ionosphere)

    def refresh_from_noaa(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            return
        self.refresh_button.setEnabled(False)
        self.save_button.setEnabled(False)
        self._set_status("connecting", self.text["waiting"])
        campaign_id = self.campaign.currentData()
        tx_grid = (
            self.repository.get_campaign(int(campaign_id)).tx_grid
            if campaign_id is not None
            else ""
        )
        worker = PropagationFetchThread(
            self.client,
            self.giro_client,
            tx_grid,
            self.target_grid.text().strip().upper(),
        )
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
        self.glotec_panel.set_content(
            bundle.images.get("glotec"),
            self.text["image_empty"],
        )
        self._drap_changed()
        self.image_metadata.setText(
            self.text["image_metadata"].format(time=_utc(snapshot.fetched_at))
        )
        self._render_operational_context()
        self._fill_ionosphere(bundle.ionosphere)
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
        self.glotec_panel.set_content(None, self.text["image_empty"])
        self.image_metadata.setText("")
        self._render_operational_context()
        self._fill_ionosphere(None)

    def _render_operational_context(self) -> None:
        self.trend_figure.clear()
        if self.bundle is None:
            self.trend_summary.setText(self.text["trend_empty"])
            self.trend_canvas.draw_idle()
            self._fill_alerts_and_forecast(None)
            return
        context = operational_context(self.bundle.snapshot)
        flare = context.flare
        flare_text = (
            self.text["flare"].format(
                current=flare.current_class,
                peak=flare.peak_class,
                begin=_utc_optional(flare.begin_at),
                maximum=_utc_optional(flare.peak_at),
                end=_utc_optional(flare.end_at),
            )
            if flare
            else self.text["trend_empty"]
        )
        self.trend_summary.setText(
            f"{self.text['observation']} · NOAA SWPC · "
            f"{_utc(self.bundle.snapshot.fetched_at)}\n{flare_text}\n"
            + self.text["proton"].format(scale=context.proton_scale)
        )
        axes = self.trend_figure.subplots(3, 2)
        plots = (
            (
                axes[0][0],
                context.xray_flux,
                "GOES X-ray 0.1–0.8 nm",
                "W/m²",
                True,
            ),
            (
                axes[0][1],
                context.proton_flux_10mev,
                "GOES protons ≥10 MeV",
                "pfu",
                True,
            ),
            (
                axes[1][0],
                tuple(
                    SeriesPoint(item.observed_at, item.speed_kms)
                    for item in context.solar_wind
                    if item.speed_kms is not None
                ),
                "Solar wind speed",
                "km/s",
                False,
            ),
            (
                axes[1][1],
                tuple(
                    SeriesPoint(item.observed_at, item.density_cm3)
                    for item in context.solar_wind
                    if item.density_cm3 is not None
                ),
                "Solar-wind density / pressure",
                "cm⁻³ / nPa",
                False,
            ),
            (
                axes[2][0],
                tuple(
                    SeriesPoint(item.observed_at, item.bt_nt)
                    for item in context.solar_wind
                    if item.bt_nt is not None
                ),
                "IMF Bt / Bz",
                "nT",
                False,
            ),
            (
                axes[2][1],
                context.dst,
                "Kyoto Dst",
                "nT",
                False,
            ),
        )
        for axis, points, title, unit, logarithmic in plots:
            axis.set_title(title)
            if points:
                axis.plot(
                    [point.observed_at for point in points],
                    [point.value for point in points],
                    color=TOKENS.chart_empirical_line,
                    linewidth=1.2,
                )
            else:
                axis.text(
                    0.5,
                    0.5,
                    "—",
                    transform=axis.transAxes,
                    ha="center",
                    va="center",
                )
            if logarithmic:
                axis.set_yscale("log")
            axis.set_ylabel(unit)
            locator = AutoDateLocator(minticks=3, maxticks=6)
            axis.xaxis.set_major_locator(locator)
            axis.xaxis.set_major_formatter(ConciseDateFormatter(locator))
            axis.grid(True, alpha=0.35)
        wind_times = [item.observed_at for item in context.solar_wind]
        pressure = [
            item.dynamic_pressure_npa
            for item in context.solar_wind
        ]
        if wind_times and any(value is not None for value in pressure):
            axes[1][1].plot(
                wind_times,
                [float("nan") if value is None else value for value in pressure],
                color=TOKENS.chart_series[2],
                linewidth=1.0,
                linestyle="--",
                label="pressure nPa",
            )
            axes[1][1].legend(loc="best", fontsize="small")
        bz_times = [
            item.observed_at for item in context.solar_wind if item.bz_nt is not None
        ]
        bz_values = [
            item.bz_nt for item in context.solar_wind if item.bz_nt is not None
        ]
        if bz_times:
            axes[2][0].plot(
                bz_times,
                bz_values,
                color=TOKENS.chart_series[3],
                linewidth=1.0,
                label="Bz",
            )
            axes[2][0].axhline(0, color=TOKENS.chart_grid, linewidth=0.8)
            axes[2][0].legend(loc="best", fontsize="small")
        apply_figure_theme(self.trend_figure)
        self.trend_figure.tight_layout(pad=1.2)
        self.trend_canvas.draw_idle()
        self._fill_alerts_and_forecast(context)

    def _fill_alerts_and_forecast(self, context) -> None:
        cme = context.cme if context else None
        self.cme_summary.setText(
            self.text["cme"].format(
                source=cme.source,
                arrival=_utc_optional(cme.arrival_at),
                speed=(
                    "—"
                    if cme.speed_kms is None
                    else f"{cme.speed_kms:.0f} km/s"
                ),
                impact=(
                    "—"
                    if cme.earth_directed is None
                    else self.text["yes"]
                    if cme.earth_directed
                    else self.text["no"]
                ),
            )
            if cme
            else ""
        )
        alerts = context.alerts if context else ()
        self.alerts_table.setSortingEnabled(False)
        self.alerts_table.setRowCount(len(alerts))
        for row, alert in enumerate(alerts):
            values = (_utc(alert.issued_at), alert.category, alert.headline)
            for column, value in enumerate(values):
                item = TechnicalTableItem(value)
                item.setToolTip(
                    f"{alert.message}\n\n{alert.bulletin_url}"
                    if column == 2
                    else value
                )
                item.setData(Qt.ItemDataRole.UserRole, alert.bulletin_url)
                self.alerts_table.setItem(row, column, item)
        self.alerts_table.setSortingEnabled(True)

        forecast = context.forecast if context else ()
        self.forecast_table.setSortingEnabled(False)
        self.forecast_table.setRowCount(len(forecast))
        for row, item in enumerate(forecast):
            values = (
                item.day.strftime("%Y-%m-%d"),
                _value(item.kp_max, 1),
                _value(item.ap, 0),
                _value(item.f107_sfu, 0),
                _optional_percent(item.m_flare_percent),
                _optional_percent(item.x_flare_percent),
                _optional_percent(item.proton_percent),
            )
            for column, value in enumerate(values):
                self.forecast_table.setItem(
                    row,
                    column,
                    TechnicalTableItem(
                        value,
                        numeric=column > 0,
                        sort_value=(
                            (
                                item.day.timestamp(),
                                item.kp_max,
                                item.ap,
                                item.f107_sfu,
                                item.m_flare_percent,
                                item.x_flare_percent,
                                item.proton_percent,
                            )[column]
                            or float("-inf")
                        ),
                    ),
                )
        self.forecast_table.setSortingEnabled(True)
        self.forecast_table.sortItems(
            0,
            Qt.SortOrder.AscendingOrder,
        )

    def _fill_ionosphere(
        self,
        bundle: IonosphereBundle | None,
    ) -> None:
        series = bundle.series if bundle else ()
        campaign_id = self.campaign.currentData()
        origin = None
        if campaign_id is not None:
            try:
                origin = maidenhead_to_latlon(
                    self.repository.get_campaign(int(campaign_id)).tx_grid
                )
            except ValueError:
                pass
        self.ionosphere_table.setSortingEnabled(False)
        self.ionosphere_table.setRowCount(len(series))
        self._ionogram_urls: list[str] = []
        latest_measurement = None
        for row, item in enumerate(series):
            latest = item.latest
            if latest is None:
                continue
            latest_measurement = latest_measurement or latest
            distance = (
                distance_and_bearing(
                    origin,
                    (item.station.latitude, item.station.longitude),
                )[0]
                if origin is not None
                else None
            )
            scaling = (
                "manual"
                if latest.manually_validated
                else "auto"
            )
            values = (
                f"{item.station.code} · {item.station.name}",
                _utc(latest.observed_at),
                "—" if latest.confidence_score is None else str(latest.confidence_score),
                _value(latest.fof2_mhz, 2),
                _value(latest.muf3000_mhz, 2),
                _value(latest.hmf2_km, 0),
                scaling,
                "—" if distance is None else f"{distance:.0f} km",
            )
            self._ionogram_urls.append(item.station.ionogram_url)
            for column, value in enumerate(values):
                table_item = TechnicalTableItem(
                    value,
                    numeric=column in (2, 3, 4, 5, 7),
                )
                table_item.setData(
                    Qt.ItemDataRole.UserRole,
                    item.station.ionogram_url,
                )
                self.ionosphere_table.setItem(row, column, table_item)
        self.ionosphere_table.setSortingEnabled(True)
        states = band_usability(latest_measurement)
        self.band_table.setSortingEnabled(False)
        self.band_table.setRowCount(len(states))
        for row, (band, state) in enumerate(states):
            self.band_table.setItem(row, 0, TechnicalTableItem(band))
            self.band_table.setItem(
                row,
                1,
                TechnicalTableItem(self.text["band_states"][state]),
            )
        self.band_table.setSortingEnabled(True)
        self._ionosphere_selection_changed()

    def _ionosphere_selection_changed(self) -> None:
        self.ionogram_button.setEnabled(
            bool(self.ionosphere_table.selectedItems())
        )

    def _open_ionogram(self) -> None:
        items = self.ionosphere_table.selectedItems()
        if not items:
            return
        url = items[0].data(Qt.ItemDataRole.UserRole)
        if url:
            QDesktopServices.openUrl(QUrl(str(url)))

    def _open_alert(self, row: int, _column: int) -> None:
        item = self.alerts_table.item(row, 0)
        if item is None:
            return
        url = item.data(Qt.ItemDataRole.UserRole)
        if url:
            QDesktopServices.openUrl(QUrl(str(url)))

    def _drap_changed(self) -> None:
        if not hasattr(self, "image_panels"):
            return
        key = self.drap_frequency.currentData()
        content = (
            self.bundle.images.get(str(key))
            if self.bundle is not None
            else None
        )
        panel = self.image_panels["drap"]
        panel.setTitle(
            f"{self.text['image_titles']['drap']} · "
            f"{self.drap_frequency.currentText()}"
        )
        panel.source.setText(
            self.text["image_source"].format(url=IMAGE_SOURCES[str(key)])
        )
        panel.source.setToolTip(IMAGE_SOURCES[str(key)])
        panel.set_content(content, self.text["image_empty"])

    def refresh_analysis(self) -> None:
        campaign_id = self.campaign.currentData()
        analysis = (
            self.repository.analyze_campaign_propagation(int(campaign_id))
            if campaign_id is not None
            else None
        )
        intervals = analysis.intervals if analysis else ()
        self.analysis_table.setSortingEnabled(False)
        self.analysis_table.setRowCount(len(intervals))
        for row, interval in enumerate(intervals):
            values = (
                _utc(interval.started_at),
                str(interval.record_count),
                str(interval.receiver_count),
                str(interval.tx_session_count),
                _signed_value(interval.median_snr_db, 1),
                _signed_value(interval.median_change_db, 1),
                ", ".join(
                    self.text["analysis_terms"].get(flag, flag)
                    for flag in interval.flags
                ) or "OK",
                self.text["yes"] if interval.direct_comparison_suitable else self.text["no"],
            )
            for column, value in enumerate(values):
                self.analysis_table.setItem(
                    row,
                    column,
                    TechnicalTableItem(value, numeric=column in (1, 2, 3, 4, 5)),
                )
        self.analysis_table.setSortingEnabled(True)
        sensitivity = analysis.sensitivity if analysis else ()
        self.sensitivity_table.setSortingEnabled(False)
        self.sensitivity_table.setRowCount(len(sensitivity))
        for row, case in enumerate(sensitivity):
            values = (
                self.text["analysis_terms"].get(case.omitted, case.omitted),
                case.omitted_value,
                str(case.remaining_count),
                (
                    "—"
                    if case.max_sector_median_change_db is None
                    else f"{case.max_sector_median_change_db:.1f} dB"
                ),
            )
            for column, value in enumerate(values):
                self.sensitivity_table.setItem(
                    row,
                    column,
                    TechnicalTableItem(value, numeric=column in (2, 3)),
                )
        self.sensitivity_table.setSortingEnabled(True)
        self.analysis_warning.setText(
            ", ".join(
                self.text["analysis_terms"].get(warning, warning)
                for warning in analysis.warnings
            )
            if analysis and analysis.warnings
            else self.text["timeline_empty"] if campaign_id is not None else ""
        )

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
        self._timeline_snapshots = {
            snapshot.id: snapshot for snapshot in snapshots
        }
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
                item.setData(Qt.ItemDataRole.UserRole, snapshot.id)
                self.timeline_table.setItem(row, column, item)
        self.timeline_table.setSortingEnabled(True)
        self.timeline_message.setText(
            self.text["timeline_empty"] if not snapshots else ""
        )

    def _load_selected_snapshot(self) -> None:
        items = self.timeline_table.selectedItems()
        if not items:
            return
        snapshot = self._timeline_snapshots.get(
            items[0].data(Qt.ItemDataRole.UserRole)
        )
        if snapshot is None:
            return
        self._show_bundle(
            PropagationBundle(
                snapshot,
                {},
                (),
                (),
                ionosphere_from_snapshot(snapshot),
            ),
            from_network=False,
        )


def _utc(value) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M")


def _utc_optional(value) -> str:
    return "—" if value is None else _utc(value)


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


def _optional_percent(value: int | None) -> str:
    return "—" if value is None else f"{value} %"
