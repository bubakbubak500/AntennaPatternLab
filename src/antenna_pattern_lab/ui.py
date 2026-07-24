from __future__ import annotations

from datetime import datetime, timezone
from html import escape
from math import pi
from pathlib import Path
from statistics import median
import threading
import time

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import QObject, QSettings, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QActionGroup, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .analysis import (
    control_group_adjusted_sector_profile,
    filter_located_spots,
    locate_spot,
    receiver_balanced_sector_profile,
    sector_profile,
    smooth_sector_pattern,
    time_normalized_sector_profile,
    trend_adjusted_sector_profile,
)
from .appearance_dialog import AppearanceDialog
from .ab_dialog import AbComparisonDialog
from .adif_io import import_adif
from .campaign_dialog import CampaignDialog
from .campaigns import assess_campaign_progress
from .collector import PskReporterCollector
from .coverage_dialog import CoverageDialog
from .csv_io import export_spots, import_spots
from .demo import generate_demo_spots
from .dependencies import detect_external_tools
from .diagnostics import build_diagnostic_report, diagnostic_json
from .domain import Spot
from .experiment_dialog import ExperimentDialog
from .exposure import exposure_sector_profile
from .geo import maidenhead_to_latlon
from .history import HistoryClient, HistoryResult
from .help_dialog import HelpDialog
from .hamlib import (
    HamlibMonitor,
    RigState,
    RigctldClient,
    RotatorMonitor,
    RotatorState,
    RotctldClient,
)
from .models import calibrate_azimuth_model, representative_frequency_hz, theoretical_azimuth_model
from .nec import NecPattern, parse_nec_output
from .profile_dialog import AntennaProfileDialog
from .profiles import expected_main_bearings
from .propagation_dialog import PropagationConditionsDialog
from .rotator_safety import (
    RotatorSafety,
    evaluate_rotator_safety,
    mechanical_target,
)
from .setup_dialog import SetupDialog
from .spot_map_dialog import SpotMapDialog
from .settings_dialog import CommunicationSettings, CommunicationSettingsDialog
from .theme import (
    TOKENS,
    DesignStyle,
    ThemeController,
    apply_figure_theme,
    current_tokens,
    monospace_font,
    semantic_style,
)
from .design_system import EmptyState, StatusIndicator, repolish
from .ui_components import (
    AnalysisToolbar,
    IntegrationStatusBar,
    MetricStrip,
    OperationalHeader,
    ReportExplorerPanel,
    SectorQualityPanel,
)
from .ui_formatting import (
    TechnicalTableItem,
    compact_source,
    format_bearing,
    format_distance_km,
    format_frequency_mhz,
    format_signed_snr,
    format_utc_timestamp,
)
from .update_dialog import UpdateDialog
from .updates import DEFAULT_RELEASE_MANIFEST_URL, check_for_update
from . import __version__
from .storage import SpotRepository
from .wsjtx import Close, Heartbeat, Status, WsjtxListener, parse_forward_targets


class CollectorBridge(QObject):
    spot_received = Signal(object)
    status_changed = Signal(str)
    connection_changed = Signal(str, str)
    history_completed = Signal(object)
    history_failed = Signal(str)
    wsjtx_message = Signal(object)
    wsjtx_state = Signal(str, str)
    hamlib_rig_state = Signal(object)
    hamlib_connection = Signal(str, str)
    rotator_position = Signal(object)
    rotator_connection = Signal(str, str)
    receiver_activity = Signal(object)
    update_checked = Signal(object)
    update_failed = Signal(str)


TRANSLATIONS = {
    "CZE": {
        "subtitle": "",
        "menu_file": "Soubor",
        "menu_data": "Data",
        "menu_tools": "Nástroje",
        "menu_settings": "Nastavení",
        "menu_help": "Nápověda",
        "communications": "Komunikace…",
        "external_tools": "Externí nástroje…",
        "about": "O programu",
        "spot_map": "Mapa spotů…",
        "campaigns": "Měřicí kampaně…",
        "campaign_none": "Kampaň: —",
        "campaign_active": "Kampaň: {name}",
        "campaign_goal_reached": "Kampaň: {name} ✓",
        "campaign_goal_progress": "Kampaň: {name} · {met}/4",
        "campaign_goal_tip": (
            "Spoty {spots}/{target_spots} · RX {receivers}/{target_receivers} · "
            "sektory {sectors}/{target_sectors} · bloky {blocks}/{target_blocks}"
        ),
        "coverage": "Pokrytí měření…",
        "propagation_conditions": "Podmínky šíření…",
        "exit": "Ukončit",
        "about_text": "Antenna Pattern Lab {version}\n\nNástroj pro modelování a porovnávání směrových vyzařovacích diagramů antén z reálných záznamů radioamatérského provozu.\n\nFT8/WSPR a PSK Reporter slouží jako zdroje měřicích dat; cílem je odhadnout, vizualizovat a porovnávat chování anténních sestav.",
        "callsign": "Moje značka",
        "tx_grid": "TX lokátor",
        "band": "Pásmo",
        "mode": "Mód",
        "language": "Jazyk",
        "wsjtx_port": "WSJT-X UDP",
        "wsjtx_address": "WSJT-X adresa",
        "wsjtx_forward": "UDP forward",
        "wsjtx_network_tooltip": "Pro běžný provoz použij 127.0.0.1. Lze zadat multicastovou IPv4 skupinu. Forward cíle odděl čárkou ve tvaru 127.0.0.1:2238.",
        "wsjtx_network_error": "Neplatné síťové nastavení WSJT-X",
        "rx_activity": "Doložená RX expozice",
        "rx_activity_tooltip": "Při živém sběru sleduje nejvýše 12 Maidenhead polí známých RX. Aktivitu agreguje po 5 minutách a používá ji pouze proti skutečným WSJT-X TX relacím.",
        "antenna_profile": "Profil antény",
        "manage_profiles": "Spravovat…",
        "ab_compare": "A/B…",
        "experiment": "Experiment…",
        "setup": "Nastavení…",
        "updates": "Aktualizace…",
        "diagnostics": "Diagnostika…",
        "help_contents": "Obsah nápovědy…",
        "diagnostics_title": "Export diagnostiky živého řetězce",
        "diagnostics_confirm": "Export obsahuje značku, lokátor, cesty k programům a stavy spojení, ale žádné spoty, zprávy, hesla ani sériová data rádia. Pokračovat?",
        "diagnostics_saved": "Diagnostika uložena: {path}",
        "database_backup_created": "Před aktualizací databáze byla vytvořena a ověřena bezpečnostní záloha.",
        "update_available": "Dostupná aktualizace {version}; otevřete Aktualizace…",
        "nec_import": "Import NEC…",
        "nec_import_title": "Import výstupu NEC",
        "nec_import_failed": "Výstup NEC nelze načíst",
        "no_profile": "— bez profilu —",
        "profile_tooltip": "Vybraný profil se uloží ke každé nové TX relaci. Změna nepřepisuje starší měření.",
        "profile_reference": "Teoretická referenční osa",
        "measured_outline": "Empirický obrys",
        "hamlib": "Hamlib rigctld",
        "hamlib_tooltip": "Volitelně čte rádio přes Hamlib rigctld na 127.0.0.1. Výchozí TCP port je 4532.",
        "hamlib_states": {
            "disabled": "Vypnuto",
            "connecting": "Připojuji",
            "connected": "Připojeno",
            "error": "Nedostupné",
        },
        "rotator_tooltip": "Čte pouze aktuální azimut a elevaci z Hamlib rotctld na 127.0.0.1; aplikace rotátor neovládá.",
        "rotator_name": "Rotátor",
        "rotator_states": {
            "disabled": "Vypnuto",
            "connecting": "Připojuji",
            "connected": "Připojeno",
            "error": "Nedostupné",
        },
        "rotator_alerts": {
            "moving_during_tx": "POHYB PŘI TX",
            "profile_mismatch": "MIMO PROFIL",
        },
        "rotator_alert_detail": {
            "moving_during_tx": "Rotátor se během aktivní TX relace odchýlil o {movement:.1f}° (limit 3°).",
            "profile_mismatch": "Skutečná mechanická osa se od profilu liší o {error:.1f}° (tolerance 5°).",
        },
        "start": "Spustit živý sběr",
        "stop": "Zastavit sběr",
        "demo": "Přidat demo data",
        "import": "Import dat…",
        "export": "Export CSV",
        "clear": "Vymazat spoty",
        "history": "Načíst historii",
        "headers": ["Čas UTC", "RX", "Lokátor", "SNR", "km", "Azimut", "MHz", "Zdroj"],
        "ready": "Připraveno.",
        "plot": "Medián SNR podle azimutu",
        "graph_view": "Graf",
        "sector_width": "Sektor",
        "time_filter": "Čas",
        "distance_filter": "Vzdálenost",
        "period_filter": "Sluneční čas TX",
        "period_filters": {"all": "Celý den", "day": "Den 06–18", "night": "Noc 18–06"},
        "source_filter": "Zdroj",
        "source_filters": {
            "all": "Všechny zdroje",
            "pskreporter": "PSK Reporter",
            "adif": "ADIF QSO",
        },
        "time_filters": {"all": "Vše", "1": "1 h", "6": "6 h", "24": "24 h", "168": "7 dní"},
        "distance_filters": {
            "all": "Vše",
            "near": "0–1 000 km",
            "mid": "1 000–3 000 km",
            "dx": "3 000–8 000 km",
            "ultra": "8 000+ km",
        },
        "graph_modes": {
            "model": "Zjednodušený model antény",
            "nec": "Externí NEC výstup",
            "snr": "Směrový profil SNR",
            "normalized": "Časově vyvážené SNR",
            "detrended": "SNR po odečtení trendu",
            "receiver": "SNR vyvážené podle RX",
            "control": "SNR vůči stabilní kontrolní skupině",
            "count": "Počet zachycení",
            "distance": "Maximální dosah",
            "time": "SNR v čase",
            "map": "Mapa přijímačů",
            "exposure": "Míra detekce aktivních RX",
        },
        "graph_titles": {
            "model": "Parametrický azimutový model",
            "nec": "Importovaný azimutový řez NEC",
            "snr": "Medián SNR podle azimutu",
            "normalized": "Medián 30minutových oken podle azimutu",
            "detrended": "SNR po robustním odečtení společného časového trendu",
            "receiver": "Směrový profil s jedním váženým hlasem každého RX",
            "control": "Směrový profil po odečtení společného trendu stabilních RX",
            "count": "Počet reportů podle azimutu",
            "distance": "Maximální dosažená vzdálenost podle azimutu",
            "time": "Časový průběh SNR",
            "map": "Geografické rozložení přijímačů",
            "exposure": "Detekce mezi prokazatelně aktivními RX",
        },
        "graph_help": {
            "model": "Samostatný geometrický model ve volném prostoru podle typu, orientace, délky vodiče a počtu prvků. Není to NEC; nezahrnuje zem, terén, výšku, ztráty, napáječ, elevaci ani ionosféru.",
            "nec": "Relativní azimutový řez importovaný z normální tabulky RADIATION PATTERNS externího NEC solveru. Aplikace neověřuje správnost vstupního NEC modelu.",
            "snr": "Kruhově vyhlazený medián SNR ve výkonové doméně. Velké mezery bez dat zůstávají nezakreslené.",
            "normalized": "Nejprve vypočítá medián v každém 30minutovém okně a potom medián oken. Rušné období tak nepřeváží klidné.",
            "detrended": "Odečte pomalý společný trend mediánu SNR v sousedních 30minutových blocích. Nekoriguje změny jednotlivých RX ani nerovnoměrné směrové pokrytí.",
            "receiver": "Každý přijímač má v sektoru nejvýše jeden hlas bez ohledu na počet reportů. Proměnlivost vůči souběžnému společnému trendu upraví váhu RX v rozsahu 0,25–1, ale přijímač nevyřadí. Pevná úroveň RX se neodečítá, protože ji z těchto dat nelze oddělit od směrového zisku antény.",
            "control": "Společný časový posun odhaduje pouze ze stabilních RX v nejméně třech různých 60° směrech a třech srovnatelných blocích. Odečte pouze změnu vůči vlastní dlouhodobé úrovni každého kontrolního RX. Při nedostatečné skupině korekci nepoužije.",
            "count": "Kolik reportů přišlo z každého sektoru. Vysoký počet může znamenat i vyšší aktivitu přijímačů.",
            "distance": "Nejvzdálenější zachycení v sektoru. Extrém je citlivý na propagaci a jediný report.",
            "time": "Jednotlivá SNR v UTC čase. Pomáhá rozpoznat změny podmínek a nestabilní období.",
            "map": "Poloha reportujících přijímačů podle Maidenhead lokátorů. Barva vyjadřuje medián SNR a velikost počet reportů.",
            "exposure": "Podíl skutečných detekcí mezi RX, které ve stejném TX okně prokazatelně reportovaly provoz. Absence bez doložené aktivity se nepočítá.",
        },
        "model_no_profile": "Vyberte profil antény, pro který se má model vykreslit.",
        "nec_no_data": "Načtěte textový výstup externího NEC solveru tlačítkem Import NEC…",
        "model_unavailable": "Pro typ Ostatní není zjednodušený model definován.",
        "model_frequency": "Referenční frekvence: {frequency:.6f} MHz",
        "model_relative_gain": "Relativní úroveň (dB)",
        "model_calibration": "Empirický relativní tvar",
        "model_calibration_detail": "měřeno {measured:+.1f} dB · model {model:+.1f} dB · reziduum {residual:+.1f} dB",
        "graph_details": "Přístupný přehled dat grafu",
        "graph_detail_headers": ["Položka", "Hodnota", "Vzorky", "RX", "Podrobnosti"],
        "pin_help": "Najetí zobrazí detail; kliknutí jej připne. Stejná data jsou v tabulce pod grafem.",
        "model_names": {
            "vertical": "Ideální všesměrový vertikál",
            "wire": "Aproximace tenkého přímého vodiče",
            "yagi": "Empirická aproximace dopředného laloku Yagi",
        },
        "model_assumptions": {
            "ideal_symmetry": "ideální azimutová symetrie",
            "no_elevation_radials": "elevace a ztráty radiálů nejsou zahrnuty",
            "sinusoidal_current": "sinusový proud na přímém vodiči",
            "free_space_horizontal": "volný prostor a vodorovný vodič",
            "no_feed_common_mode": "napájecí bod a soufázové proudy nejsou zahrnuty",
            "ideal_phasing": "ideální fázování prvků",
            "elements_control_shape": "počet prvků určuje šířku laloku a odhad F/B",
            "no_boom_solution": "geometrie ráhna a délky prvků se neřeší",
        },
        "sector_tip": "Šířka směrových sektorů. Užší sektory mají větší detail, ale méně vzorků.",
        "quality_labels": {"none": "bez dat", "low": "nízká", "medium": "střední", "high": "dobrá"},
        "confidence_range": "{low:+.1f} až {high:+.1f} dB",
        "receiver_summary": "{stable} stabilních · {variable} proměnlivých · {unstable} nestabilních · {insufficient} bez dostatku souběžných dat",
        "receiver_stability_labels": {
            "stable": "stabilní",
            "variable": "proměnlivý",
            "unstable": "nestabilní",
            "insufficient": "málo dat",
        },
        "receiver_stability_detail": "srovnatelné bloky {blocks} · MAD {mad} · váha {weight:.2f} · relativní úroveň {baseline}",
        "receiver_more": "Dalších {count} RX je skryto kvůli velikosti tabulky.",
        "control_group": "Kontrolní skupina",
        "control_trend": "Společný trend {time}",
        "control_ready": "{receivers} stabilní RX · {sectors} směrů · {blocks} bloků",
        "control_unavailable": "Korekce nepoužita: {reason}",
        "control_reasons": {
            "receivers": "méně než 3 stabilní RX",
            "directions": "stabilní RX nepokrývají alespoň 3 různé 60° směry",
            "blocks": "méně než 3 společné časové bloky",
        },
        "sector_hover": "Sektor {start:.0f}–{end:.0f}°\nMedián SNR: {snr}\n95% CI: {confidence}\nReportů: {count}\n30min oken: {blocks}\nUnikátních RX: {receivers}\nMax. vzdálenost: {distance}\nKvalita pokrytí: {quality}\n{context}",
        "filter_context": "{call} · {band} · čas {time} · {period} · vzdálenost {distance} · zdroj {source} · profil {profile}",
        "map_hover": "{call} · {grid}\nMedián SNR: {snr:+.1f} dB\nReportů: {count}",
        "exposure_hover": "Detekce: {detections}/{opportunities} ({rate})\nAktivních RX: {receivers}\n95% Wilsonův interval: {confidence}",
        "summary": "{spots} použitelných reportů · {receivers} RX",
        "quality_summary": "{good}/{covered} sektorů s dobrou kvalitou",
        "collection_section": "SBĚR",
        "collection_states": {
            "stopped": "○ Zastaveno",
            "connecting": "◐ Připojuji",
            "running": "● Probíhá",
            "stopping": "◐ Zastavuji",
            "failed": "◆ Chyba sběru",
        },
        "collection_details": {
            "stopped": "Připraveno k bezpečnému spuštění.",
            "connecting": "Navazuji spojení s PSK Reporterem.",
            "running": "Přijímám a ukládám reporty.",
            "stopping": "Dokončuji sběr a ukládám stav.",
            "failed": "Sběr se nepodařilo spustit. Opravte nastavení a zkuste to znovu.",
        },
        "metrics": {
            "reports": "Reporty",
            "receivers": "Přijímače",
            "quality": "Kvalitní sektory",
            "tx": "TX relace",
            "range": "Max. dosah",
            "period": "Období",
        },
        "reports_title": "Příchozí reporty",
        "no_reports_title": "Zatím žádné reporty",
        "no_reports_detail": "Spusťte živý sběr, načtěte historii, importujte data nebo použijte demo.",
        "no_filtered_title": "Filtry nevracejí žádná data",
        "no_filtered_detail": "Změňte čas, vzdálenost, sluneční období nebo zdroj dat.",
        "no_chart_title": "Diagram čeká na data",
        "no_chart_detail": "Spusťte sběr, načtěte historii, importujte data nebo přidejte demo.",
        "sector_quality_title": "Kvalita pokrytí sektorů",
        "sector_detail": "{start:.0f}–{end:.0f}° · {quality} · {count} reportů · {receivers} RX · max {distance}",
        "report_detail": "{time} UTC · {call} {grid} · SNR {snr} dB · {distance} km · {bearing} · {frequency} MHz · {source}",
        "reset_layout": "Obnovit rozložení",
        "language_menu": "Jazyk",
        "new_spot": "Nový report: {call} · {snr:+d} dB",
        "demo_added": "Přidáno {count} demo reportů.",
        "import_title": "Import spotů",
        "import_failed": "Import selhal",
        "imported": "Importováno {count} nových reportů.",
        "adif_imported": "ADIF: {records} QSO, {usable} použitelných, {new} nových, {skipped} přeskočeno. Jde o výběrová QSO data; pro oddělení použijte filtr Zdroj.",
        "export_title": "Export spotů",
        "exported": "Export uložen: {name}",
        "cannot_start": "Nelze spustit sběr",
        "clear_title": "Vymazat databázi spotů?",
        "clear_confirm": "Opravdu odstranit všech {count} uložených spotů? Tuto operaci nelze vrátit zpět. Živý sběr může pokračovat od čistého záznamu.",
        "cleared": "Odstraněno {count} spotů. Záznam začíná znovu od nuly.",
        "nothing_to_clear": "Databáze spotů je již prázdná.",
        "invalid_demo_title": "Demo data nelze vytvořit",
        "invalid_demo_call": "Nejdříve zadejte vlastní volací značku.",
        "invalid_demo_grid": "TX lokátor není platný Maidenhead lokátor.",
        "history_loading": "Načítám historii {hours} h pro {call}…",
        "history_loaded": "Historie: API vrátilo {reports} reportů, {usable} použitelných, {new} nových, {skipped} přeskočeno.",
        "history_failed": "Načtení historie selhalo: {error}",
        "history_rate_limit": "Další historický dotaz bude možný za {seconds} s (limit PSK Reporteru je 5 minut).",
        "history_tooltip": "Načte poslední reporty přes HTTP API. PSK Reporter povoluje rozsah nejvýše 24 hodin a doporučuje nejvýše jeden dotaz za 5 minut.",
        "wsjtx_tooltip": "V nastavení WSJT-X nastav UDP Server na 127.0.0.1 a tento port. Zelený RX/TX stav se objeví až po přijetí platné zprávy.",
        "wsjtx": {
            "disconnected": "Vypnuto",
            "waiting": "Čekám",
            "connected": "Připojeno",
            "stale": "Bez dat",
            "error": "Chyba",
            "rx": "RX",
            "tx": "TX",
        },
        "connection": {
            "disconnected": "Odpojeno",
            "connecting": "Připojování…",
            "connected": "Připojeno",
            "error": "Chyba spojení",
        },
        "connection_status": {
            "disconnected": "Živý sběr není připojen.",
            "connecting": "Navazuji spojení s PSK Reporterem…",
            "connected": "PSK Reporter potvrdil MQTT spojení a odběr tématu.",
            "error": "Spojení s PSK Reporterem selhalo nebo bylo přerušeno.",
        },
    },
    "ENG": {
        "subtitle": "",
        "menu_file": "File",
        "menu_data": "Data",
        "menu_tools": "Tools",
        "menu_settings": "Settings",
        "menu_help": "Help",
        "communications": "Communications…",
        "external_tools": "External tools…",
        "about": "About",
        "spot_map": "Spot map…",
        "campaigns": "Measurement campaigns…",
        "campaign_none": "Campaign: —",
        "campaign_active": "Campaign: {name}",
        "campaign_goal_reached": "Campaign: {name} ✓",
        "campaign_goal_progress": "Campaign: {name} · {met}/4",
        "campaign_goal_tip": (
            "Spots {spots}/{target_spots} · RX {receivers}/{target_receivers} · "
            "sectors {sectors}/{target_sectors} · blocks {blocks}/{target_blocks}"
        ),
        "coverage": "Measurement coverage…",
        "propagation_conditions": "Propagation conditions…",
        "exit": "Exit",
        "about_text": "Antenna Pattern Lab {version}\n\nA tool for modelling and comparing directional antenna radiation patterns from real amateur-radio operating records.\n\nFT8/WSPR and PSK Reporter provide measurement data; the goal is to estimate, visualize and compare antenna-system behaviour.",
        "callsign": "My callsign",
        "tx_grid": "TX grid",
        "band": "Band",
        "mode": "Mode",
        "language": "Language",
        "wsjtx_port": "WSJT-X UDP",
        "wsjtx_address": "WSJT-X address",
        "wsjtx_forward": "UDP forwarding",
        "wsjtx_network_tooltip": "Use 127.0.0.1 normally. An IPv4 multicast group is also supported. Separate forwarding targets with commas, e.g. 127.0.0.1:2238.",
        "wsjtx_network_error": "Invalid WSJT-X network settings",
        "rx_activity": "Verified RX exposure",
        "rx_activity_tooltip": "During live collection, monitors up to 12 Maidenhead fields containing known receivers. Activity is aggregated into 5-minute windows and matched only against real WSJT-X TX sessions.",
        "antenna_profile": "Antenna profile",
        "manage_profiles": "Manage…",
        "ab_compare": "A/B…",
        "experiment": "Experiment…",
        "setup": "Setup…",
        "updates": "Updates…",
        "diagnostics": "Diagnostics…",
        "help_contents": "Help contents…",
        "diagnostics_title": "Export live-chain diagnostics",
        "diagnostics_confirm": "The export contains callsign, grid, executable paths and connection states, but no spot rows, messages, passwords or radio serial data. Continue?",
        "diagnostics_saved": "Diagnostics saved: {path}",
        "database_backup_created": "A verified safety backup was created before updating the database.",
        "update_available": "Update {version} is available; open Updates…",
        "nec_import": "Import NEC…",
        "nec_import_title": "Import NEC output",
        "nec_import_failed": "Cannot load NEC output",
        "no_profile": "— no profile —",
        "profile_tooltip": "The selected profile is stored with every new TX session. Changing it does not rewrite older measurements.",
        "profile_reference": "Theoretical reference axis",
        "measured_outline": "Empirical outline",
        "hamlib": "Hamlib rigctld",
        "hamlib_tooltip": "Optionally reads the radio through Hamlib rigctld on 127.0.0.1. Default TCP port is 4532.",
        "hamlib_states": {
            "disabled": "Off",
            "connecting": "Connecting",
            "connected": "Connected",
            "error": "Unavailable",
        },
        "rotator_tooltip": "Only reads current azimuth and elevation from Hamlib rotctld at 127.0.0.1; the application does not control the rotator.",
        "rotator_name": "Rotator",
        "rotator_states": {
            "disabled": "Off",
            "connecting": "Connecting",
            "connected": "Connected",
            "error": "Unavailable",
        },
        "rotator_alerts": {
            "moving_during_tx": "MOVING DURING TX",
            "profile_mismatch": "PROFILE MISMATCH",
        },
        "rotator_alert_detail": {
            "moving_during_tx": "The rotator moved {movement:.1f}° during an active TX session (3° limit).",
            "profile_mismatch": "The actual mechanical axis differs from the profile by {error:.1f}° (5° tolerance).",
        },
        "start": "Start live collection",
        "stop": "Stop collection",
        "demo": "Add demo data",
        "import": "Import data…",
        "export": "Export CSV",
        "clear": "Clear spots",
        "history": "Load history",
        "headers": ["UTC time", "RX", "Grid", "SNR", "km", "Bearing", "MHz", "Source"],
        "ready": "Ready.",
        "plot": "Median SNR by bearing",
        "graph_view": "Chart",
        "sector_width": "Sector",
        "time_filter": "Time",
        "distance_filter": "Distance",
        "period_filter": "TX solar time",
        "period_filters": {"all": "Full day", "day": "Day 06–18", "night": "Night 18–06"},
        "source_filter": "Source",
        "source_filters": {
            "all": "All sources",
            "pskreporter": "PSK Reporter",
            "adif": "ADIF QSO",
        },
        "time_filters": {"all": "All", "1": "1 h", "6": "6 h", "24": "24 h", "168": "7 days"},
        "distance_filters": {
            "all": "All",
            "near": "0–1,000 km",
            "mid": "1,000–3,000 km",
            "dx": "3,000–8,000 km",
            "ultra": "8,000+ km",
        },
        "graph_modes": {
            "model": "Simplified antenna model",
            "nec": "External NEC output",
            "snr": "Directional SNR profile",
            "normalized": "Time-balanced SNR",
            "detrended": "Trend-adjusted SNR",
            "receiver": "Receiver-balanced SNR",
            "control": "Stable-control adjusted SNR",
            "count": "Detection count",
            "distance": "Maximum reach",
            "time": "SNR over time",
            "map": "Receiver map",
            "exposure": "Active-RX detection rate",
        },
        "graph_titles": {
            "model": "Parametric azimuth model",
            "nec": "Imported NEC azimuth cut",
            "snr": "Median SNR by bearing",
            "normalized": "Median of 30-minute windows by bearing",
            "detrended": "SNR after robust removal of the common time trend",
            "receiver": "Directional profile with one weighted vote per RX",
            "control": "Directional profile after stable-RX common-trend removal",
            "count": "Report count by bearing",
            "distance": "Maximum reached distance by bearing",
            "time": "SNR over time",
            "map": "Geographic receiver distribution",
            "exposure": "Detection among demonstrably active receivers",
        },
        "graph_help": {
            "model": "A separate free-space geometric model based on type, orientation, wire length and element count. It is not NEC and omits ground, terrain, height, loss, feed line, elevation and ionosphere.",
            "nec": "Relative azimuth cut imported from an external NEC solver's normal RADIATION PATTERNS table. The app cannot validate the correctness of the input NEC model.",
            "snr": "Circularly smoothed median SNR in the power domain. Large unsupported gaps remain unplotted.",
            "normalized": "First takes a median inside every 30-minute window, then a median across windows, preventing busy periods from dominating.",
            "detrended": "Removes a slow common median-SNR trend across neighboring 30-minute blocks. It cannot correct receiver-specific changes or uneven directional coverage.",
            "receiver": "Each receiver has at most one vote per sector regardless of report count. Variability against a concurrent common trend adjusts its weight between 0.25 and 1 without excluding it. Fixed RX level is not subtracted because these data cannot separate it from directional antenna gain.",
            "control": "A common time shift is estimated only from stable receivers spanning at least three different 60° directions and three comparable blocks. Only change from each control RX's own long-term level is removed. No correction is applied when the group is insufficient.",
            "count": "Number of reports from each sector. A high count may also reflect greater receiver activity.",
            "distance": "Most distant reception in a sector. This extreme is sensitive to propagation and single reports.",
            "time": "Individual SNR values over UTC time. Useful for spotting changing conditions and unstable periods.",
            "map": "Locations of reporting receivers from Maidenhead grids. Color represents median SNR and marker size the report count.",
            "exposure": "Share of detections among receivers demonstrably reporting traffic in the same TX window. Unknown absence is excluded.",
        },
        "model_no_profile": "Select an antenna profile to draw its model.",
        "nec_no_data": "Load a text output from an external NEC solver with Import NEC…",
        "model_unavailable": "No simplified model is defined for the Other type.",
        "model_frequency": "Reference frequency: {frequency:.6f} MHz",
        "model_relative_gain": "Relative level (dB)",
        "model_calibration": "Empirical relative shape",
        "model_calibration_detail": "measured {measured:+.1f} dB · model {model:+.1f} dB · residual {residual:+.1f} dB",
        "graph_details": "Accessible chart data",
        "graph_detail_headers": ["Item", "Value", "Samples", "RX", "Details"],
        "pin_help": "Hover shows details; click pins them. The same data is available in the table below the chart.",
        "model_names": {
            "vertical": "Ideal omnidirectional vertical",
            "wire": "Thin straight-wire approximation",
            "yagi": "Empirical Yagi forward-lobe approximation",
        },
        "model_assumptions": {
            "ideal_symmetry": "ideal azimuthal symmetry",
            "no_elevation_radials": "elevation and radial losses omitted",
            "sinusoidal_current": "sinusoidal current on a straight wire",
            "free_space_horizontal": "free space and horizontal wire",
            "no_feed_common_mode": "feed point and common-mode effects omitted",
            "ideal_phasing": "ideal element phasing",
            "elements_control_shape": "element count controls beam width and F/B estimate",
            "no_boom_solution": "boom geometry and element lengths are not solved",
        },
        "sector_tip": "Bearing sector width. Narrow sectors provide more detail but fewer samples.",
        "quality_labels": {"none": "no data", "low": "low", "medium": "medium", "high": "good"},
        "confidence_range": "{low:+.1f} to {high:+.1f} dB",
        "receiver_summary": "{stable} stable · {variable} variable · {unstable} unstable · {insufficient} without enough concurrent data",
        "receiver_stability_labels": {
            "stable": "stable",
            "variable": "variable",
            "unstable": "unstable",
            "insufficient": "insufficient data",
        },
        "receiver_stability_detail": "comparable blocks {blocks} · MAD {mad} · weight {weight:.2f} · relative level {baseline}",
        "receiver_more": "{count} additional receivers are hidden to keep the table responsive.",
        "control_group": "Control group",
        "control_trend": "Common trend {time}",
        "control_ready": "{receivers} stable RX · {sectors} directions · {blocks} blocks",
        "control_unavailable": "Correction not applied: {reason}",
        "control_reasons": {
            "receivers": "fewer than 3 stable receivers",
            "directions": "stable receivers do not span at least 3 different 60° directions",
            "blocks": "fewer than 3 common time blocks",
        },
        "sector_hover": "Sector {start:.0f}–{end:.0f}°\nMedian SNR: {snr}\n95% CI: {confidence}\nReports: {count}\n30-minute windows: {blocks}\nUnique RX: {receivers}\nMax distance: {distance}\nCoverage quality: {quality}\n{context}",
        "filter_context": "{call} · {band} · time {time} · {period} · distance {distance} · source {source} · profile {profile}",
        "map_hover": "{call} · {grid}\nMedian SNR: {snr:+.1f} dB\nReports: {count}",
        "exposure_hover": "Detections: {detections}/{opportunities} ({rate})\nActive RX: {receivers}\n95% Wilson interval: {confidence}",
        "summary": "{spots} usable reports · {receivers} RX",
        "quality_summary": "{good}/{covered} sectors with good quality",
        "collection_section": "COLLECTION",
        "collection_states": {
            "stopped": "○ Stopped",
            "connecting": "◐ Connecting",
            "running": "● Running",
            "stopping": "◐ Stopping",
            "failed": "◆ Collection failed",
        },
        "collection_details": {
            "stopped": "Ready to start safely.",
            "connecting": "Opening the PSK Reporter connection.",
            "running": "Receiving and storing reports.",
            "stopping": "Finishing collection and saving state.",
            "failed": "Collection could not start. Correct the settings and try again.",
        },
        "metrics": {
            "reports": "Reports",
            "receivers": "Receivers",
            "quality": "Good sectors",
            "tx": "TX sessions",
            "range": "Max range",
            "period": "Period",
        },
        "reports_title": "Incoming reports",
        "no_reports_title": "No reports yet",
        "no_reports_detail": "Start live collection, load history, import data, or add demo data.",
        "no_filtered_title": "No data matches the filters",
        "no_filtered_detail": "Change the time, distance, solar-period, or source filter.",
        "no_chart_title": "The pattern is waiting for data",
        "no_chart_detail": "Start collection, load history, import data, or add demo data.",
        "sector_quality_title": "Sector coverage quality",
        "sector_detail": "{start:.0f}–{end:.0f}° · {quality} · {count} reports · {receivers} RX · max {distance}",
        "report_detail": "{time} UTC · {call} {grid} · SNR {snr} dB · {distance} km · {bearing} · {frequency} MHz · {source}",
        "reset_layout": "Reset layout",
        "language_menu": "Language",
        "new_spot": "New report: {call} · {snr:+d} dB",
        "demo_added": "Added {count} demo reports.",
        "import_title": "Import spots",
        "import_failed": "Import failed",
        "imported": "Imported {count} new reports.",
        "adif_imported": "ADIF: {records} QSOs, {usable} usable, {new} new, {skipped} skipped. These are selected QSO data; use the Source filter to keep them separate.",
        "export_title": "Export spots",
        "exported": "Export saved: {name}",
        "cannot_start": "Collection cannot start",
        "clear_title": "Clear the spot database?",
        "clear_confirm": "Delete all {count} stored spots? This cannot be undone. Live collection can continue with a clean record.",
        "cleared": "Deleted {count} spots. Recording now starts again from zero.",
        "nothing_to_clear": "The spot database is already empty.",
        "invalid_demo_title": "Demo data cannot be created",
        "invalid_demo_call": "Enter your callsign first.",
        "invalid_demo_grid": "The TX grid is not a valid Maidenhead locator.",
        "history_loading": "Loading {hours} h of history for {call}…",
        "history_loaded": "History: API returned {reports} reports, {usable} usable, {new} new, {skipped} skipped.",
        "history_failed": "History loading failed: {error}",
        "history_rate_limit": "The next history request is available in {seconds} s (PSK Reporter's limit is 5 minutes).",
        "history_tooltip": "Loads recent reports through the HTTP API. PSK Reporter allows at most 24 hours and recommends no more than one request every 5 minutes.",
        "wsjtx_tooltip": "Set UDP Server in WSJT-X to 127.0.0.1 and this port. Green RX/TX appears only after a valid message is received.",
        "wsjtx": {
            "disconnected": "Off",
            "waiting": "Waiting",
            "connected": "Connected",
            "stale": "No data",
            "error": "Error",
            "rx": "RX",
            "tx": "TX",
        },
        "connection": {
            "disconnected": "Disconnected",
            "connecting": "Connecting…",
            "connected": "Connected",
            "error": "Connection error",
        },
        "connection_status": {
            "disconnected": "Live collection is not connected.",
            "connecting": "Connecting to PSK Reporter…",
            "connected": "PSK Reporter confirmed the MQTT connection and subscription.",
            "error": "The PSK Reporter connection failed or was interrupted.",
        },
    },
}


class MainWindow(QMainWindow):
    def __init__(self, repository: SpotRepository, settings: QSettings | None = None):
        super().__init__()
        self.repository = repository
        self.settings = settings or QSettings("OK7PS", "AntennaPatternLab")
        self.theme_controller = ThemeController(self.settings, self)
        self.bridge = CollectorBridge()
        self.collector = PskReporterCollector(
            self.bridge.spot_received.emit,
            self.bridge.status_changed.emit,
            self.bridge.connection_changed.emit,
            self.bridge.receiver_activity.emit,
        )
        self.history_client = HistoryClient()
        wsjtx_host = str(self.settings.value("wsjtx_host", "127.0.0.1"))
        wsjtx_port = int(self.settings.value("wsjtx_port", 2237))
        wsjtx_forward = str(self.settings.value("wsjtx_forward", ""))
        try:
            forward_targets = parse_forward_targets(
                wsjtx_forward, listener_host=wsjtx_host, listener_port=wsjtx_port
            )
        except ValueError:
            forward_targets = ()
        self.wsjtx_listener = WsjtxListener(
            self.bridge.wsjtx_message.emit,
            self.bridge.wsjtx_state.emit,
            host=wsjtx_host,
            port=wsjtx_port,
            forward_targets=forward_targets,
        )
        self._active_tx_sessions: dict[str, int] = {}
        self._tx_rotator_tracking: dict[int, tuple[float | None, float]] = {}
        self._tx_rotator_targets: dict[int, float | None] = {}
        self._wsjtx_connection_state = "disconnected"
        self._wsjtx_operating_state = ""
        self._wsjtx_detail = ""
        self._latest_rig_state: RigState | None = None
        self._nec_pattern: NecPattern | None = None
        self._hamlib_connection_state = "disabled"
        self._hamlib_detail = ""
        self.hamlib_monitor = HamlibMonitor(
            RigctldClient(port=int(self.settings.value("hamlib_port", 4532))),
            self.bridge.hamlib_rig_state.emit,
            self.bridge.hamlib_connection.emit,
        )
        self._latest_rotator_state: RotatorState | None = None
        self._rotator_connection_state = "disabled"
        self._rotator_detail = ""
        self._rotator_safety = RotatorSafety("none", (), None, 0.0)
        self.rotator_monitor = RotatorMonitor(
            RotctldClient(port=int(self.settings.value("rotator_port", 4533))),
            self.bridge.rotator_position.emit,
            self.bridge.rotator_connection.emit,
        )
        self._collecting = False
        self._collection_ui_state = "stopped"
        self._connection_state = "disconnected"
        self._spot_map_dialog: SpotMapDialog | None = None
        saved_language = str(self.settings.value("language", "CZE"))
        self.language_code = saved_language if saved_language in TRANSLATIONS else "CZE"
        self.setWindowTitle("Antenna Pattern Lab · FT8 / WSPR")
        self.setWindowIcon(QApplication.instance().windowIcon())
        self.resize(1180, 760)
        self.setMinimumSize(1100, 680)
        self._build_ui()
        self.theme_controller.theme_changed.connect(self._theme_changed)
        self._connect_signals()
        self._configure_tab_order()
        self.wsjtx_listener.start()
        if bool(int(self.settings.value("hamlib_enabled", 0))):
            self.hamlib_monitor.start()
        if bool(int(self.settings.value("rotator_enabled", 0))):
            self.rotator_monitor.start()
        self.refresh()
        if self.repository.migration_performed and self.repository.last_backup_path:
            self.status.setText(self._text("database_backup_created"))
            self.status.setToolTip(str(self.repository.last_backup_path))

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("AppShell")
        layout = QVBoxLayout(root)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(6)
        self._root_layout = layout

        # Kept as compatibility attributes for existing translation/theme code;
        # the native title bar already carries the product name.
        self._title = QLabel()
        self.subtitle = QLabel()

        self.callsign = QLineEdit(str(self.settings.value("callsign", "OK7PS")))
        self.callsign.setMaximumWidth(145)
        self.tx_grid = QLineEdit(str(self.settings.value("tx_grid", "JN79")))
        self.tx_grid.setMaximumWidth(105)
        self.band = QComboBox()
        self.band.addItems(["20m", "40m", "15m", "10m", "80m", "30m", "17m", "12m", "+"])
        self.band.setCurrentText(str(self.settings.value("band", "20m")))
        self.band.setMaximumWidth(90)
        self.mode = QComboBox()
        self.mode.addItems(["FT8", "WSPR"])
        self.mode.setCurrentText(str(self.settings.value("mode", "FT8")))
        self.mode.setMaximumWidth(90)
        self.language = QComboBox()
        self.language.addItems(["CZE", "ENG"])
        self.language.setCurrentText(self.language_code if self.language_code in TRANSLATIONS else "CZE")
        self.language.hide()
        self.callsign_label = QLabel()
        self.tx_grid_label = QLabel()
        self.band_label = QLabel()
        self.mode_label = QLabel()
        self.language_label = QLabel()
        self.language_label.hide()

        # Runtime communication controls remain the source of truth, but are
        # edited in the Communication dialog rather than shown on the main UI.
        self.wsjtx_port = QSpinBox()
        self.wsjtx_port.setRange(1024, 65535)
        self.wsjtx_port.setValue(self.wsjtx_listener.port)
        self.wsjtx_port_label = QLabel()
        self.wsjtx_host = QLineEdit(self.wsjtx_listener.host)
        self.wsjtx_host_label = QLabel()
        self.wsjtx_forward = QLineEdit(str(self.settings.value("wsjtx_forward", "")))
        self.wsjtx_forward_label = QLabel()
        self.antenna_profile = QComboBox()
        self.manage_profiles_button = QPushButton()
        self.ab_compare_button = QPushButton()
        self.experiment_button = QPushButton()
        self.setup_button = QPushButton()
        self.updates_button = QPushButton()
        self.diagnostics_button = QPushButton()
        self.nec_import_button = QPushButton()
        self.antenna_profile_label = QLabel()
        self.hamlib_enabled = QCheckBox()
        self.hamlib_enabled.setChecked(bool(int(self.settings.value("hamlib_enabled", 0))))
        self.hamlib_port = QSpinBox()
        self.hamlib_port.setRange(1024, 65535)
        self.hamlib_port.setValue(self.hamlib_monitor.client.port)
        self.hamlib_label = QLabel()
        self.rotator_enabled = QCheckBox()
        self.rotator_enabled.setChecked(
            bool(int(self.settings.value("rotator_enabled", 0)))
        )
        self.rotator_port = QSpinBox()
        self.rotator_port.setRange(1024, 65535)
        self.rotator_port.setValue(self.rotator_monitor.client.port)
        self.rx_activity_enabled = QCheckBox()
        self.rx_activity_enabled.setChecked(bool(int(self.settings.value("rx_activity_enabled", 0))))
        self.rx_activity_label = QLabel()
        self._reload_antenna_profiles()

        self.demo_button = QPushButton()
        self.import_button = QPushButton()
        self.export_button = QPushButton()
        self.history_hours = QComboBox()
        for hours in (1, 6, 12, 24):
            self.history_hours.addItem(f"{hours} h", hours)
        saved_history_hours = int(self.settings.value("history_hours", 6))
        history_index = self.history_hours.findData(saved_history_hours)
        self.history_hours.setCurrentIndex(max(0, history_index))
        self.history_hours.setMaximumWidth(72)
        self.history_button = QPushButton()
        self.clear_button = QPushButton()
        self.clear_button.setProperty("buttonRole", "danger")

        self.operational_header = OperationalHeader()
        self.operational_header.setAccessibleName("Measurement context and collection")
        self.operational_header.add_context(self.callsign_label, self.callsign, 0, 0)
        self.operational_header.add_context(self.tx_grid_label, self.tx_grid, 0, 2)
        self.operational_header.add_context(self.band_label, self.band, 0, 4)
        self.operational_header.add_context(self.mode_label, self.mode, 0, 6)
        self.operational_header.add_context(
            self.antenna_profile_label, self.antenna_profile, 1, 0, 3
        )
        self.campaign_indicator = QLabel()
        self.campaign_indicator.setObjectName("ContextValue")
        self.campaign_indicator.setWordWrap(False)
        self.operational_header.context_layout.addWidget(
            self.campaign_indicator, 1, 4, 1, 2
        )
        self.operational_header.context_layout.addWidget(self.history_hours, 1, 6)
        self.operational_header.context_layout.addWidget(self.history_button, 1, 7)
        self.live_button = self.operational_header.collection.button
        layout.addWidget(self.operational_header)

        self.metric_strip = MetricStrip()
        self.metric_strip.setAccessibleName("Analysis metrics")
        layout.addWidget(self.metric_strip)

        self.analysis_toolbar = AnalysisToolbar()
        self.analysis_toolbar.setAccessibleName("Analysis filters")
        self.graph_view_label = QLabel()
        self.graph_view = QComboBox()
        for code in ("snr", "normalized", "detrended", "receiver", "control", "count", "distance", "time", "map", "exposure", "model", "nec"):
            self.graph_view.addItem("", code)
        saved_graph = str(self.settings.value("graph_view", "snr"))
        self.graph_view.setCurrentIndex(max(0, self.graph_view.findData(saved_graph)))
        self.graph_view.setMinimumContentsLength(18)
        self.sector_width_label = QLabel()
        self.sector_width = QComboBox()
        for width in (10, 15, 30, 45, 60, 90):
            self.sector_width.addItem(f"{width}°", width)
        saved_width = int(self.settings.value("sector_width", 10))
        self.sector_width.setCurrentIndex(max(0, self.sector_width.findData(saved_width)))
        self.graph_info = QPushButton("i")
        self.graph_info.setObjectName("graphInfo")
        self.graph_info.setFlat(True)
        self.graph_info.setMaximumWidth(32)

        self.time_filter_label = QLabel()
        self.time_filter = QComboBox()
        for code, hours in (("all", None), ("1", 1), ("6", 6), ("24", 24), ("168", 168)):
            self.time_filter.addItem("", (code, hours))
        saved_time_filter = str(self.settings.value("time_filter", "all"))
        for index in range(self.time_filter.count()):
            if self.time_filter.itemData(index)[0] == saved_time_filter:
                self.time_filter.setCurrentIndex(index)
                break
        self.distance_filter_label = QLabel()
        self.distance_filter = QComboBox()
        for code in ("all", "near", "mid", "dx", "ultra"):
            self.distance_filter.addItem("", code)
        self.distance_filter.setCurrentIndex(
            max(0, self.distance_filter.findData(str(self.settings.value("distance_filter", "all"))))
        )
        self.period_filter_label = QLabel()
        self.period_filter = QComboBox()
        for code in ("all", "day", "night"):
            self.period_filter.addItem("", code)
        self.period_filter.setCurrentIndex(
            max(0, self.period_filter.findData(str(self.settings.value("period_filter", "all"))))
        )
        self.source_filter_label = QLabel()
        self.source_filter = QComboBox()
        for code in ("all", "pskreporter", "adif"):
            self.source_filter.addItem("", code)
        self.source_filter.setCurrentIndex(
            max(0, self.source_filter.findData(str(self.settings.value("source_filter", "all"))))
        )

        self.analysis_toolbar.add_control(self.graph_view_label, self.graph_view, 1)
        self.analysis_toolbar.add_control(self.sector_width_label, self.sector_width)
        self.analysis_toolbar.layout.addWidget(self.graph_info)
        self.analysis_toolbar.add_gap()
        self.analysis_toolbar.add_control(self.time_filter_label, self.time_filter)
        self.analysis_toolbar.add_control(self.distance_filter_label, self.distance_filter)
        self.analysis_toolbar.add_control(self.period_filter_label, self.period_filter)
        self.analysis_toolbar.add_control(self.source_filter_label, self.source_filter)
        self.analysis_toolbar.finish()
        layout.addWidget(self.analysis_toolbar)

        chart_panel = QFrame()
        chart_panel.setObjectName("DataPanel")
        chart_layout = QVBoxLayout(chart_panel)
        chart_layout.setContentsMargins(4, 4, 4, 4)
        self.figure = Figure(
            figsize=(6, 5), facecolor=current_tokens().panel_background
        )
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setAccessibleName("Primary analysis chart")
        self._graph_hover_data = []
        self._plot_annotation = None
        self._plot_pinned = False
        self.canvas.mpl_connect("motion_notify_event", self._on_graph_hover)
        self.canvas.mpl_connect("button_press_event", self._on_graph_click)
        self.chart_empty = EmptyState()
        self.chart_stack = QStackedWidget()
        self.chart_stack.addWidget(self.canvas)
        self.chart_stack.addWidget(self.chart_empty)
        chart_layout.addWidget(self.chart_stack, 1)
        self.graph_details = QTableWidget(0, 5)
        self.graph_details.setObjectName("DataTable")
        self.graph_details.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.graph_details.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.graph_details.horizontalHeader().setStretchLastSection(True)
        self.graph_details.hide()

        self.table = QTableWidget(0, 8)
        self.table.setObjectName("DataTable")
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().setDefaultSectionSize(current_tokens().table_row_height)
        header = self.table.horizontalHeader()
        for column in range(7):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
        self.report_panel = ReportExplorerPanel(self.table)
        self.table.itemSelectionChanged.connect(self._report_selection_changed)

        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setObjectName("MainAnalysisSplitter")
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.addWidget(chart_panel)
        self.main_splitter.addWidget(self.report_panel)
        self.main_splitter.setStretchFactor(0, 65)
        self.main_splitter.setStretchFactor(1, 35)
        saved_splitter = self.settings.value("ui/main_splitter_state")
        restored = bool(saved_splitter and self.main_splitter.restoreState(saved_splitter))
        if not restored:
            self.main_splitter.setSizes([760, 420])
        layout.addWidget(self.main_splitter, 1)

        self.sector_quality_panel = SectorQualityPanel()
        layout.addWidget(self.sector_quality_panel)

        self.integration_bar = IntegrationStatusBar()
        self.connection_indicator = StatusIndicator()
        self.wsjtx_indicator = StatusIndicator()
        self.hamlib_indicator = StatusIndicator()
        self.rotator_indicator = StatusIndicator()
        for indicator in (
            self.connection_indicator,
            self.wsjtx_indicator,
            self.hamlib_indicator,
            self.rotator_indicator,
        ):
            self.integration_bar.add_indicator(indicator)
        self.integration_bar.finish()
        self.status = self.integration_bar.warning
        layout.addWidget(self.integration_bar)

        # Compatibility label retained for tests and integrations; metrics now
        # render through MetricStrip rather than the bottom status row.
        self.summary = QLabel()
        self.summary.hide()

        self.setCentralWidget(root)
        self._build_menus()
        self._apply_theme()
        self._apply_language()
        self._set_connection_state("disconnected", "")
        self._render_wsjtx_indicator()
        self._render_hamlib_indicator()
        self._render_rotator_indicator()
        self._render_campaign_indicator()

    def _build_menus(self) -> None:
        menu_bar = self.menuBar()
        self.file_menu = menu_bar.addMenu("")
        self.data_menu = menu_bar.addMenu("")
        self.tools_menu = menu_bar.addMenu("")
        self.settings_menu = menu_bar.addMenu("")
        self.help_menu = menu_bar.addMenu("")

        self.import_action = QAction(self)
        self.import_action.triggered.connect(self.import_button.click)
        self.export_action = QAction(self)
        self.export_action.triggered.connect(self.export_button.click)
        self.nec_action = QAction(self)
        self.nec_action.triggered.connect(self.nec_import_button.click)
        self.exit_action = QAction(self)
        self.exit_action.triggered.connect(self.close)
        self.file_menu.addActions(
            [self.import_action, self.export_action, self.nec_action]
        )
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.exit_action)

        self.history_action = QAction(self)
        self.history_action.triggered.connect(self.history_button.click)
        self.demo_action = QAction(self)
        self.demo_action.triggered.connect(self.demo_button.click)
        self.clear_action = QAction(self)
        self.clear_action.triggered.connect(self.clear_button.click)
        self.spot_map_action = QAction(self)
        self.spot_map_action.triggered.connect(self._open_spot_map)
        self.data_menu.addActions(
            [self.history_action, self.clear_action, self.spot_map_action]
        )

        self.profiles_action = QAction(self)
        self.profiles_action.triggered.connect(self.manage_profiles_button.click)
        self.ab_action = QAction(self)
        self.ab_action.triggered.connect(self.ab_compare_button.click)
        self.experiment_action = QAction(self)
        self.experiment_action.triggered.connect(self.experiment_button.click)
        self.campaigns_action = QAction(self)
        self.campaigns_action.triggered.connect(self._open_campaigns)
        self.coverage_action = QAction(self)
        self.coverage_action.triggered.connect(self._open_coverage)
        self.propagation_action = QAction(self)
        self.propagation_action.triggered.connect(
            self._open_propagation_conditions
        )
        self.tools_menu.addActions(
            [
                self.profiles_action,
                self.ab_action,
                self.experiment_action,
                self.campaigns_action,
                self.coverage_action,
                self.propagation_action,
            ]
        )

        self.communications_action = QAction(self)
        self.communications_action.triggered.connect(
            self._open_communication_settings
        )
        self.external_tools_action = QAction(self)
        self.external_tools_action.triggered.connect(self.setup_button.click)
        self.updates_action = QAction(self)
        self.updates_action.triggered.connect(self.updates_button.click)
        self.settings_menu.addActions(
            [
                self.communications_action,
                self.external_tools_action,
                self.updates_action,
            ]
        )
        self.settings_menu.addSeparator()
        self.appearance_action = QAction(self)
        self.appearance_action.triggered.connect(self._open_appearance_settings)
        self.settings_menu.addAction(self.appearance_action)
        self.language_menu = self.settings_menu.addMenu("")
        self.language_group = QActionGroup(self)
        self.language_group.setExclusive(True)
        self.language_actions = {}
        for code in ("CZE", "ENG"):
            action = QAction(code, self)
            action.setCheckable(True)
            action.setData(code)
            action.triggered.connect(
                lambda checked=False, selected=code: self.language.setCurrentText(selected)
            )
            self.language_group.addAction(action)
            self.language_menu.addAction(action)
            self.language_actions[code] = action
        self.reset_layout_action = QAction(self)
        self.reset_layout_action.triggered.connect(self._reset_layout)
        self.settings_menu.addAction(self.reset_layout_action)

        self.diagnostics_action = QAction(self)
        self.diagnostics_action.triggered.connect(self.diagnostics_button.click)
        self.help_contents_action = QAction(self)
        self.help_contents_action.triggered.connect(self._show_help)
        self.about_action = QAction(self)
        self.about_action.triggered.connect(self._show_about)
        self.help_menu.addActions([self.help_contents_action, self.demo_action])
        self.help_menu.addSeparator()
        self.help_menu.addActions([self.diagnostics_action, self.about_action])

    def _connect_signals(self) -> None:
        self.live_button.clicked.connect(self.toggle_collection)
        self.demo_button.clicked.connect(self.add_demo_data)
        self.import_button.clicked.connect(self.import_csv)
        self.export_button.clicked.connect(self.export_csv)
        self.history_button.clicked.connect(self.load_history)
        self.clear_button.clicked.connect(self.clear_spots)
        self.band.currentTextChanged.connect(self._collection_configuration_changed)
        self.mode.currentTextChanged.connect(self._collection_configuration_changed)
        self.language.currentTextChanged.connect(self._change_language)
        self.callsign.editingFinished.connect(self._collection_configuration_changed)
        self.tx_grid.editingFinished.connect(self.refresh)
        self.wsjtx_port.editingFinished.connect(self._restart_wsjtx_listener)
        self.wsjtx_host.editingFinished.connect(self._restart_wsjtx_listener)
        self.wsjtx_forward.editingFinished.connect(self._restart_wsjtx_listener)
        self.manage_profiles_button.clicked.connect(self._manage_antenna_profiles)
        self.ab_compare_button.clicked.connect(self._open_ab_comparison)
        self.experiment_button.clicked.connect(self._open_experiment)
        self.setup_button.clicked.connect(self._open_setup)
        self.updates_button.clicked.connect(self._open_updates)
        self.diagnostics_button.clicked.connect(self._export_diagnostics)
        self.nec_import_button.clicked.connect(self._import_nec_output)
        self.antenna_profile.currentIndexChanged.connect(
            self._antenna_profile_selected
        )
        self.hamlib_enabled.toggled.connect(self._toggle_hamlib)
        self.rotator_enabled.toggled.connect(self._toggle_rotator)
        self.rx_activity_enabled.toggled.connect(self._rx_activity_toggled)
        self.hamlib_port.editingFinished.connect(self._restart_hamlib)
        self.rotator_port.editingFinished.connect(self._restart_rotator)
        self.graph_view.currentIndexChanged.connect(self._graph_options_changed)
        self.sector_width.currentIndexChanged.connect(self._graph_options_changed)
        self.time_filter.currentIndexChanged.connect(self._graph_options_changed)
        self.distance_filter.currentIndexChanged.connect(self._graph_options_changed)
        self.period_filter.currentIndexChanged.connect(self._graph_options_changed)
        self.source_filter.currentIndexChanged.connect(self._graph_options_changed)
        self.main_splitter.splitterMoved.connect(self._save_splitter_state)
        self.bridge.spot_received.connect(self._store_live_spot)
        self.bridge.connection_changed.connect(self._set_connection_state)
        self.bridge.history_completed.connect(self._history_completed)
        self.bridge.history_failed.connect(self._history_failed)
        self.bridge.wsjtx_message.connect(self._handle_wsjtx_message)
        self.bridge.wsjtx_state.connect(self._set_wsjtx_state)
        self.bridge.hamlib_rig_state.connect(self._handle_rig_state)
        self.bridge.hamlib_connection.connect(self._set_hamlib_state)
        self.bridge.rotator_position.connect(self._handle_rotator_state)
        self.bridge.rotator_connection.connect(self._set_rotator_state)
        self.bridge.receiver_activity.connect(self._store_receiver_activity)
        self.bridge.update_checked.connect(self._handle_update_check)
        self.bridge.update_failed.connect(lambda _error: None)
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(3000)
        self._refresh_timer.timeout.connect(self.refresh)

    def _configure_tab_order(self) -> None:
        controls = (
            self.callsign,
            self.tx_grid,
            self.band,
            self.mode,
            self.antenna_profile,
            self.history_hours,
            self.history_button,
            self.live_button,
            self.graph_view,
            self.sector_width,
            self.graph_info,
            self.time_filter,
            self.distance_filter,
            self.period_filter,
            self.source_filter,
            self.table,
        )
        for current, following in zip(controls, controls[1:]):
            QWidget.setTabOrder(current, following)

    def _apply_theme(self) -> None:
        tokens = self.theme_controller.tokens
        monitor = self.theme_controller.design_style == DesignStyle.MONITOR
        if not hasattr(self, "_classic_widget_fonts"):
            self._classic_widget_fonts = [
                (widget, QFont(widget.font()))
                for widget in (
                    self.callsign,
                    self.tx_grid,
                    self.history_hours,
                    self.table,
                    self.graph_details,
                )
            ]
        self.setPalette(QApplication.palette())
        self.setStyleSheet("")
        if monitor:
            self._root_layout.setContentsMargins(12, 8, 12, 8)
            self._root_layout.setSpacing(6)
            for widget, _font in self._classic_widget_fonts:
                widget.setFont(monospace_font())
        else:
            self._root_layout.setContentsMargins(12, 8, 12, 8)
            self._root_layout.setSpacing(6)
            for widget, font in self._classic_widget_fonts:
                widget.setFont(font)
        self.graph_info.setStyleSheet(
            semantic_style(
                "info",
                bold=True,
                size_px=tokens.heading_font_px if monitor else 17,
            )
        )
        self.table.verticalHeader().setDefaultSectionSize(tokens.table_row_height)
        apply_figure_theme(self.figure)

    def _theme_changed(self, _tokens) -> None:
        self._apply_theme()
        self.refresh()

    def _open_appearance_settings(self) -> None:
        dialog = AppearanceDialog(
            self.theme_controller.design_style,
            self.theme_controller.preference,
            self.language_code,
            self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        design_style, preference = dialog.values()
        self.theme_controller.set_selection(design_style, preference)

    def toggle_collection(self) -> None:
        if self._collecting:
            self._set_collection_ui_state("stopping")
            self.collector.stop()
            self._collecting = False
            self._refresh_timer.stop()
            self._set_collection_ui_state("stopped")
            return
        self._set_collection_ui_state("connecting")
        try:
            self.collector.start(
                self.callsign.text(), self.band.currentText(), self.mode.currentText(), self._activity_fields()
            )
        except ValueError as exc:
            self._set_collection_ui_state("failed", str(exc))
            QMessageBox.warning(self, self._text("cannot_start"), str(exc))
            return
        self._save_settings()
        self._collecting = True
        self._set_collection_ui_state("running")
        self._refresh_timer.start()

    def _set_collection_ui_state(self, state: str, detail: str = "") -> None:
        if state not in {"stopped", "connecting", "running", "stopping", "failed"}:
            state = "failed"
        self._collection_ui_state = state
        if not hasattr(self, "operational_header"):
            return
        action = self._text("stop") if state == "running" else self._text("start")
        if state == "connecting":
            action = self._text("collection_states")["connecting"]
        elif state == "stopping":
            action = self._text("collection_states")["stopping"]
        self.operational_header.collection.set_collection_state(
            state,
            self._text("collection_states")[state],
            detail or self._text("collection_details")[state],
            action,
        )

    def _store_live_spot(self, spot: Spot) -> None:
        if self.repository.add(spot):
            self.status.setText(self._text("new_spot").format(call=spot.rx_call, snr=spot.snr_db))

    def add_demo_data(self) -> None:
        callsign = self.callsign.text().strip()
        if not callsign:
            QMessageBox.warning(
                self, self._text("invalid_demo_title"), self._text("invalid_demo_call")
            )
            return
        try:
            maidenhead_to_latlon(self.tx_grid.text())
        except ValueError:
            QMessageBox.warning(
                self, self._text("invalid_demo_title"), self._text("invalid_demo_grid")
            )
            return
        selected_band = self.band.currentText()
        demo_band = "20m" if selected_band == "+" else selected_band
        spots = generate_demo_spots(
            callsign, self.tx_grid.text(), demo_band, mode=self.mode.currentText()
        )
        inserted = self.repository.add_many(spots)
        self.status.setText(self._text("demo_added").format(count=inserted))
        self.refresh()

    def import_csv(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            self._text("import_title"),
            "",
            "Supported data (*.csv *.adi *.adif);;ADIF (*.adi *.adif);;CSV (*.csv)",
        )
        if not filename:
            return
        try:
            if Path(filename).suffix.lower() in {".adi", ".adif"}:
                result = import_adif(
                    filename,
                    fallback_tx_call=self.callsign.text().strip(),
                    fallback_tx_grid=self.tx_grid.text().strip(),
                )
                inserted = self.repository.add_many(result.spots)
            else:
                result = None
                inserted = self.repository.add_many(import_spots(filename))
        except (KeyError, OSError, ValueError) as exc:
            QMessageBox.critical(self, self._text("import_failed"), str(exc))
            return
        if result is None:
            self.status.setText(self._text("imported").format(count=inserted))
        else:
            self.status.setText(
                self._text("adif_imported").format(
                    records=result.record_count,
                    usable=len(result.spots),
                    new=inserted,
                    skipped=result.skipped_count,
                )
            )
        self.refresh()

    def export_csv(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(
            self, self._text("export_title"), "antenna-spots.csv", "CSV (*.csv)"
        )
        if filename:
            export_spots(filename, [item.spot for item in self._located_spots()])
            self.status.setText(self._text("exported").format(name=Path(filename).name))

    def clear_spots(self) -> None:
        count = self.repository.count()
        if count == 0:
            self.status.setText(self._text("nothing_to_clear"))
            return
        answer = QMessageBox.question(
            self,
            self._text("clear_title"),
            self._text("clear_confirm").format(count=count),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        removed = self.repository.clear()
        self.refresh()
        self.status.setText(self._text("cleared").format(count=removed))

    def load_history(self) -> None:
        callsign = self.callsign.text().strip().upper()
        if not callsign:
            QMessageBox.warning(
                self, self._text("invalid_demo_title"), self._text("invalid_demo_call")
            )
            return
        try:
            maidenhead_to_latlon(self.tx_grid.text())
        except ValueError:
            QMessageBox.warning(
                self, self._text("invalid_demo_title"), self._text("invalid_demo_grid")
            )
            return
        now = int(time.time())
        last_request = int(self.settings.value("history_last_request_epoch", 0))
        remaining = 300 - (now - last_request)
        if remaining > 0:
            self.status.setText(
                self._text("history_rate_limit").format(seconds=remaining)
            )
            return
        hours = int(self.history_hours.currentData())
        band = self.band.currentText()
        tx_grid = self.tx_grid.text().strip().upper()
        mode = self.mode.currentText()
        self.settings.setValue("history_last_request_epoch", now)
        self.settings.setValue("history_hours", hours)
        self.history_button.setEnabled(False)
        self.status.setText(
            self._text("history_loading").format(hours=hours, call=callsign)
        )
        worker = threading.Thread(
            target=self._fetch_history,
            args=(callsign, band, hours, tx_grid, mode),
            daemon=True,
            name="pskr-history",
        )
        worker.start()

    def _fetch_history(
        self, callsign: str, band: str, hours: int, tx_grid: str, mode: str
    ) -> None:
        try:
            result = self.history_client.fetch(callsign, band, hours, tx_grid, mode)
        except Exception as exc:  # Network/XML errors are presented in the UI.
            self.bridge.history_failed.emit(str(exc))
            return
        self.bridge.history_completed.emit(result)

    def _history_completed(self, result: HistoryResult) -> None:
        inserted = self.repository.add_many(result.spots)
        self.history_button.setEnabled(True)
        self.refresh()
        self.status.setText(
            self._text("history_loaded").format(
                reports=result.report_count,
                usable=len(result.spots),
                new=inserted,
                skipped=result.skipped_count,
            )
        )

    def _history_failed(self, error: str) -> None:
        self.history_button.setEnabled(True)
        self.status.setText(self._text("history_failed").format(error=error))

    def _collection_configuration_changed(self, *_args) -> None:
        self.refresh()
        if not self._collecting:
            return
        try:
            self.collector.start(
                self.callsign.text(), self.band.currentText(), self.mode.currentText(), self._activity_fields()
            )
        except ValueError as exc:
            self._collecting = False
            self._set_collection_ui_state("failed", str(exc))
            self._refresh_timer.stop()
            QMessageBox.warning(self, self._text("cannot_start"), str(exc))

    def _filtered_spots(self, campaign_id: int | None = None) -> list[Spot]:
        if campaign_id is not None:
            return self.repository.list_spots(campaign_id=campaign_id)
        return self.repository.list_spots(
            tx_call=self.callsign.text().strip(),
            band=self.band.currentText(),
            mode=self.mode.currentText(),
            source=self.source_filter.currentData() or "all",
        )

    def _located_spots(self, campaign_id: int | None = None):
        campaign = (
            self.repository.get_campaign(campaign_id)
            if campaign_id is not None
            else None
        )
        tx_grid = campaign.tx_grid if campaign is not None else self.tx_grid.text()
        located = [
            item
            for spot in self._filtered_spots(campaign_id)
            if (item := locate_spot(spot, tx_grid))
        ]
        time_data = self.time_filter.currentData() or ("all", None)
        distance_code = self.distance_filter.currentData() or "all"
        distance_bounds = {
            "all": (None, None),
            "near": (0.0, 1000.0),
            "mid": (1000.0, 3000.0),
            "dx": (3000.0, 8000.0),
            "ultra": (8000.0, None),
        }
        minimum, maximum = (
            (None, None)
            if campaign is not None
            else distance_bounds[distance_code]
        )
        try:
            _latitude, tx_longitude = maidenhead_to_latlon(tx_grid)
        except ValueError:
            tx_longitude = 0.0
        return filter_located_spots(
            located,
            # A named campaign is already bounded by its own explicit interval.
            # A rolling "last N hours" UI filter must not erase historical results.
            hours=None if campaign is not None else time_data[1],
            min_distance_km=minimum,
            max_distance_km=maximum,
            solar_period=(
                "all"
                if campaign is not None
                else self.period_filter.currentData() or "all"
            ),
            tx_longitude_deg=tx_longitude,
        )

    def refresh(self) -> None:
        located = self._located_spots()
        self._draw_profile(located)
        mode = self.graph_view.currentData() or "snr"
        chart_requires_reports = mode not in {"model", "nec"}
        if chart_requires_reports and not located:
            filtered_empty = self.repository.count() > 0
            self.chart_empty.heading.setText(
                self._text("no_filtered_title")
                if filtered_empty
                else self._text("no_chart_title")
            )
            self.chart_empty.description.setText(
                self._text("no_filtered_detail")
                if filtered_empty
                else self._text("no_chart_detail")
            )
            self.chart_stack.setCurrentWidget(self.chart_empty)
            self.report_panel.set_texts(
                self._text("reports_title"),
                (
                    self._text("no_filtered_title")
                    if filtered_empty
                    else self._text("no_reports_title")
                ),
                (
                    self._text("no_filtered_detail")
                    if filtered_empty
                    else self._text("no_reports_detail")
                ),
            )
        else:
            self.chart_stack.setCurrentWidget(self.canvas)
        apply_figure_theme(self.figure)
        self.canvas.draw_idle()
        self._fill_table(located[:500])
        unique_rx = len({item.spot.rx_call for item in located})
        width_deg = int(self.sector_width.currentData() or 10)
        sectors = sector_profile(located, width_deg)
        covered = sum(sector.count > 0 for sector in sectors)
        good = sum(sector.quality_label == "high" for sector in sectors)
        tx_count = self.repository.tx_session_count()
        maximum_distance = max(
            (item.distance_km for item in located),
            default=None,
        )
        self.summary.setText(
            self._text("summary").format(spots=len(located), receivers=unique_rx)
            + f" · {self._text('quality_summary').format(good=good, covered=covered)}"
            + f" · {tx_count} TX"
        )
        metric_labels = self._text("metrics")
        self.metric_strip.set_metrics(
            {
                "reports": (metric_labels["reports"], str(len(located)), self._filter_context()),
                "receivers": (metric_labels["receivers"], str(unique_rx), ""),
                "quality": (
                    metric_labels["quality"],
                    f"{good}/{covered}",
                    self._text("quality_summary").format(good=good, covered=covered),
                ),
                "tx": (metric_labels["tx"], str(tx_count), ""),
                "range": (
                    metric_labels["range"],
                    (
                        f"{format_distance_km(maximum_distance)} km"
                        if maximum_distance is not None
                        else "—"
                    ),
                    "",
                ),
                "period": (
                    metric_labels["period"],
                    self.time_filter.currentText(),
                    self._filter_context(),
                ),
            }
        )
        quality_labels = self._text("quality_labels")
        sector_details = []
        for sector in sectors:
            start = sector.center_deg - width_deg / 2
            end = sector.center_deg + width_deg / 2
            sector_details.append(
                self._text("sector_detail").format(
                    start=start % 360,
                    end=end % 360,
                    quality=quality_labels[sector.quality_label],
                    count=sector.count,
                    receivers=sector.unique_receivers,
                    distance=(
                        f"{format_distance_km(sector.max_distance_km)} km"
                        if sector.max_distance_km is not None
                        else "—"
                    ),
                )
            )
        self.sector_quality_panel.set_sectors(
            sectors,
            width_deg,
            quality_labels,
            self._text("quality_summary").format(good=good, covered=covered),
            sector_details,
        )
        if hasattr(self, "campaign_indicator"):
            self._render_campaign_indicator()
        self._save_settings()

    def _draw_profile(self, located) -> None:
        self.figure.clear()
        self._graph_hover_data = []
        self._plot_pinned = False
        self._set_graph_details([])
        mode = self.graph_view.currentData() or "snr"
        width_deg = int(self.sector_width.currentData() or 10)
        if mode == "time":
            self._draw_time_chart(located)
            return
        if mode == "map":
            self._draw_receiver_map(located)
            return
        if mode == "exposure":
            self._draw_exposure_chart()
            return
        if mode == "model":
            self._draw_model_chart()
            return
        if mode == "nec":
            self._draw_nec_chart()
            return
        axis = self.figure.add_subplot(111, projection="polar")
        axis.set_facecolor(TOKENS.panel_background)
        axis.set_theta_zero_location("N")
        axis.set_theta_direction(-1)
        receiver_metrics = []
        control_group = None
        if mode == "normalized":
            profile = time_normalized_sector_profile(located, width_deg)
        elif mode == "detrended":
            profile = trend_adjusted_sector_profile(located, width_deg)
        elif mode == "receiver":
            profile, receiver_metrics = receiver_balanced_sector_profile(
                located, width_deg
            )
        elif mode == "control":
            profile, receiver_metrics, control_group = (
                control_group_adjusted_sector_profile(located, width_deg)
            )
        else:
            profile = sector_profile(located, width_deg)
        theta = [sector.center_deg * pi / 180 for sector in profile]
        if mode == "count":
            radius = [sector.count for sector in profile]
        elif mode == "distance":
            radius = [sector.max_distance_km or 0.0 for sector in profile]
        else:
            # Shift SNR to a non-negative radial scale; labels retain dB meaning.
            radius = [
                max(0.0, (sector.median_snr_db if sector.median_snr_db is not None else -30.0) + 30.0)
                for sector in profile
            ]
        quality_colors = TOKENS.confidence_levels
        bars = axis.bar(
            theta,
            radius,
            width=max(1, width_deg - 1) * pi / 180,
            color=[quality_colors[sector.quality_label] for sector in profile],
            alpha=0.42 if mode in ("snr", "normalized", "detrended", "receiver", "control") else 0.8,
        )
        for sector, bar in zip(profile, bars):
            start = sector.center_deg - width_deg / 2
            end = sector.center_deg + width_deg / 2
            hover = self._text("sector_hover").format(
                start=start,
                end=end,
                snr=(f"{sector.median_snr_db:+.1f} dB" if sector.median_snr_db is not None else "—"),
                confidence=(
                    self._text("confidence_range").format(
                        low=sector.confidence_low_db,
                        high=sector.confidence_high_db,
                    )
                    if sector.confidence_low_db is not None
                    else "—"
                ),
                count=sector.count,
                blocks=sector.time_block_count,
                receivers=sector.unique_receivers,
                distance=(f"{sector.max_distance_km:.0f} km" if sector.max_distance_km is not None else "—"),
                quality=self._text("quality_labels")[sector.quality_label],
                context=self._filter_context(),
            )
            self._graph_hover_data.append((bar, hover))
        detail_rows = [
                (
                    f"{sector.center_deg - width_deg / 2:.0f}–{sector.center_deg + width_deg / 2:.0f}°",
                    (
                        str(sector.count)
                        if mode == "count"
                        else f"{sector.max_distance_km:.0f} km"
                        if mode == "distance" and sector.max_distance_km is not None
                        else f"{sector.median_snr_db:+.1f} dB"
                        if sector.median_snr_db is not None
                        else "—"
                    ),
                    str(sector.count),
                    str(sector.unique_receivers),
                    self._text("quality_labels")[sector.quality_label],
                )
                for sector in profile
            ]
        if mode in ("receiver", "control"):
            labels = self._text("receiver_stability_labels")
            if control_group is not None:
                control_value = (
                    self._text("control_ready").format(
                        receivers=len(control_group.receiver_calls),
                        sectors=control_group.angular_sector_count,
                        blocks=control_group.comparable_block_count,
                    )
                    if control_group.ready
                    else self._text("control_unavailable").format(
                        reason=self._text("control_reasons")[
                            control_group.reason_code
                        ]
                    )
                )
                control_rows = [
                    (
                        self._text("control_group"),
                        control_value,
                        str(control_group.comparable_block_count),
                        str(len(control_group.receiver_calls)),
                        ", ".join(control_group.receiver_calls) or "—",
                    )
                ]
                control_rows.extend(
                    (
                        self._text("control_trend").format(
                            time=datetime.fromtimestamp(
                                point.block_index * 30 * 60,
                                tz=timezone.utc,
                            ).strftime("%Y-%m-%d %H:%M UTC")
                        ),
                        f"{point.adjustment_db:+.1f} dB",
                        str(point.receiver_count),
                        str(point.receiver_count),
                        "",
                    )
                    for point in control_group.trend[-48:]
                )
                detail_rows[0:0] = control_rows
            sorted_metrics = sorted(
                receiver_metrics,
                key=lambda value: (
                    value.stability_label == "insufficient",
                    -(
                        value.variability_mad_db
                        if value.variability_mad_db is not None
                        else -1.0
                    ),
                    value.receiver_call,
                ),
            )
            detail_rows.extend(
                (
                    f"RX {item.receiver_call}",
                    labels[item.stability_label],
                    str(item.report_count),
                    str(item.comparable_blocks),
                    self._text("receiver_stability_detail").format(
                        blocks=item.comparable_blocks,
                        mad=(
                            f"{item.variability_mad_db:.1f} dB"
                            if item.variability_mad_db is not None
                            else "—"
                        ),
                        weight=item.reliability_weight,
                        baseline=(
                            f"{item.relative_baseline_db:+.1f} dB"
                            if item.relative_baseline_db is not None
                            else "—"
                        ),
                    ),
                )
                for item in sorted_metrics[:100]
            )
            if len(sorted_metrics) > 100:
                detail_rows.append(
                    (
                        self._text("receiver_more").format(
                            count=len(sorted_metrics) - 100
                        ),
                        "…",
                        "",
                        "",
                        "",
                    )
                )
        self._set_graph_details(detail_rows)
        if mode in ("snr", "normalized", "detrended", "receiver", "control") and theta:
            interval_sectors = [
                (angle, sector)
                for angle, sector in zip(theta, profile)
                if sector.confidence_low_db is not None
            ]
            if interval_sectors:
                axis.vlines(
                    [item[0] for item in interval_sectors],
                    [max(0.0, item[1].confidence_low_db + 30.0) for item in interval_sectors],
                    [max(0.0, item[1].confidence_high_db + 30.0) for item in interval_sectors],
                    color=TOKENS.text_secondary,
                    linewidth=1.2,
                    alpha=0.85,
                    zorder=5,
                )
            # A finite angular kernel turns sector observations into broad
            # lobes. Unknown large gaps remain gaps instead of collapsing to
            # an invented -30 dB point at the centre.
            smoothed = smooth_sector_pattern(profile)
            outline_theta = [
                point.bearing_deg * pi / 180 for point in smoothed
            ]
            outline_radius = [
                (
                    max(0.0, point.level_db + 30.0)
                    if point.level_db is not None
                    else float("nan")
                )
                for point in smoothed
            ]
            axis.plot(
                outline_theta,
                outline_radius,
                color=TOKENS.chart_empirical_line,
                linewidth=2.4,
                label=self._text("measured_outline"),
                zorder=4,
            )
            if all(point.level_db is not None for point in smoothed):
                axis.fill(
                    outline_theta,
                    outline_radius,
                    color=TOKENS.chart_empirical_fill,
                    alpha=0.15,
                    zorder=2,
                )
        profile_id = self.antenna_profile.currentData()
        reference_bearings = ()
        if profile_id is not None:
            try:
                reference_bearings = expected_main_bearings(
                    self.repository.get_antenna_profile(profile_id)
                )
            except ValueError:
                pass
        reference_limit = 40.0 if mode in ("snr", "normalized", "detrended", "receiver", "control") else max([float(value) for value in radius] + [1.0])
        for index, bearing in enumerate(reference_bearings):
            angle = bearing * pi / 180
            axis.plot(
                [angle, angle],
                [0, reference_limit],
                color=TOKENS.chart_theoretical_reference,
                linestyle="--",
                linewidth=1.5,
                label=self._text("profile_reference") if index == 0 else None,
            )
        if mode in ("snr", "normalized", "detrended", "receiver", "control"):
            axis.set_rlim(0, 40)
            axis.set_yticks([10, 20, 30, 40], labels=["−20", "−10", "0", "+10 dB"])
        axis.tick_params(colors=TOKENS.chart_labels)
        axis.grid(color=TOKENS.chart_grid, alpha=0.8)
        title = self._text("graph_titles")[mode]
        if mode == "receiver":
            counts = {
                label: sum(
                    item.stability_label == label for item in receiver_metrics
                )
                for label in ("stable", "variable", "unstable", "insufficient")
            }
            title += "\n" + self._text("receiver_summary").format(**counts)
        elif mode == "control" and control_group is not None:
            if control_group.ready:
                title += "\n" + self._text("control_ready").format(
                    receivers=len(control_group.receiver_calls),
                    sectors=control_group.angular_sector_count,
                    blocks=control_group.comparable_block_count,
                )
            else:
                title += "\n" + self._text("control_unavailable").format(
                    reason=self._text("control_reasons")[
                        control_group.reason_code
                    ]
                )
        axis.set_title(title, color=TOKENS.text_primary, pad=14)
        if reference_bearings or mode in ("snr", "normalized", "detrended", "receiver", "control"):
            legend = axis.legend(
                loc="lower left",
                bbox_to_anchor=(-0.42, -0.02),
                fontsize=8,
                ncol=1,
            )
            for text_item in legend.get_texts():
                text_item.set_color(TOKENS.text_primary)
            legend.get_frame().set_facecolor(TOKENS.surface_1)
        self.figure.subplots_adjust(left=0.08, right=0.92, top=0.92, bottom=0.10)
        self._plot_annotation = axis.annotate(
            "",
            xy=(0, 0),
            xytext=(14, 14),
            textcoords="offset points",
            bbox={"boxstyle": "round", "fc": TOKENS.surface_2, "ec": TOKENS.accent},
            color=TOKENS.text_primary,
        )
        self._plot_annotation.set_visible(False)
        self.canvas.draw_idle()

    def _draw_model_chart(self) -> None:
        axis = self.figure.add_subplot(111, projection="polar")
        axis.set_facecolor(TOKENS.panel_background)
        axis.set_theta_zero_location("N")
        axis.set_theta_direction(-1)
        profile_id = self.antenna_profile.currentData()
        model = None
        frequency_hz = representative_frequency_hz(
            self.band.currentText(), self.mode.currentText()
        )
        if profile_id is not None:
            try:
                model = theoretical_azimuth_model(
                    self.repository.get_antenna_profile(profile_id), frequency_hz
                )
            except ValueError:
                model = None
        axis.set_title(self._text("graph_titles")["model"], color=TOKENS.text_primary, pad=20)
        axis.tick_params(colors=TOKENS.chart_labels)
        axis.grid(color=TOKENS.chart_grid, alpha=0.8)
        axis.set_rlim(0, 30)
        axis.set_yticks([0, 10, 20, 30], labels=["−30", "−20", "−10", "0 dB"])
        if model is None:
            message = (
                self._text("model_no_profile")
                if profile_id is None
                else self._text("model_unavailable")
            )
            axis.text(
                0.5, 0.5, message, transform=axis.transAxes, ha="center", va="center",
                color=TOKENS.text_secondary, wrap=True,
            )
            self._set_graph_details([(message, "—", "—", "—", "")])
        else:
            theta = [point.bearing_deg * pi / 180 for point in model.points]
            radius = [point.relative_gain_db + 30.0 for point in model.points]
            theta.append(theta[0])
            radius.append(radius[0])
            axis.plot(theta, radius, color=TOKENS.warning, linewidth=2.2)
            axis.fill(theta, radius, color=TOKENS.warning, alpha=0.18)
            profile_spots = self.repository.list_spots_for_profile(
                profile_id, band=self.band.currentText(), mode=self.mode.currentText()
            )
            profile_located = [
                item for spot in profile_spots if (item := locate_spot(spot, self.tx_grid.text()))
            ]
            calibration = calibrate_azimuth_model(model, profile_located)
            if calibration:
                calibration_theta = [point.bearing_deg * pi / 180 for point in calibration]
                calibration_radius = [max(0.0, point.measured_relative_db + 30.0) for point in calibration]
                axis.plot(
                    calibration_theta,
                    calibration_radius,
                    color=TOKENS.info,
                    linewidth=2.0,
                    linestyle="--",
                    marker="o",
                    label=self._text("model_calibration"),
                )
                legend = axis.legend(loc="upper right", fontsize=8)
                legend.get_frame().set_facecolor(TOKENS.surface_1)
                for text_item in legend.get_texts():
                    text_item.set_color(TOKENS.text_primary)
            detail = "\n".join(
                (
                    self._text("model_names")[model.model_name],
                    self._text("model_frequency").format(frequency=frequency_hz / 1_000_000),
                    *(self._text("model_assumptions")[item] for item in model.assumptions),
                )
            )
            axis.text(
                0.02, 0.02, detail, transform=axis.transAxes, ha="left", va="bottom",
                color=TOKENS.text_secondary, fontsize=8,
                bbox={"boxstyle": "round", "fc": TOKENS.surface_2, "ec": TOKENS.text_muted, "alpha": 0.95},
            )
            self._set_graph_details(
                [
                    (
                        f"{point.bearing_deg:.0f}°",
                        f"{point.relative_gain_db:+.1f} dB",
                        "—",
                        "—",
                        self._text("model_names")[model.model_name],
                    )
                    for point in model.points
                ]
                + [
                    (
                        f"{point.bearing_deg:.0f}°",
                        f"{point.measured_relative_db:+.1f} dB",
                        str(point.count),
                        "—",
                        self._text("model_calibration_detail").format(
                            measured=point.measured_relative_db,
                            model=point.model_relative_db,
                            residual=point.residual_db,
                        ),
                    )
                    for point in calibration
                ]
            )
        self.figure.tight_layout()
        self._plot_annotation = None
        self.canvas.draw_idle()

    def _draw_nec_chart(self) -> None:
        axis = self.figure.add_subplot(111, projection="polar")
        axis.set_facecolor(TOKENS.panel_background)
        axis.set_theta_zero_location("N")
        axis.set_theta_direction(-1)
        axis.set_title(self._text("graph_titles")["nec"], color=TOKENS.text_primary, pad=20)
        axis.tick_params(colors=TOKENS.chart_labels)
        axis.grid(color=TOKENS.chart_grid, alpha=0.8)
        axis.set_rlim(0, 60)
        axis.set_yticks([0, 20, 40, 60], labels=["−60", "−40", "−20", "0 dB"])
        if self._nec_pattern is None:
            message = self._text("nec_no_data")
            axis.text(0.5, 0.5, message, transform=axis.transAxes, ha="center", va="center", color=TOKENS.text_secondary, wrap=True)
            self._set_graph_details([(message, "—", "—", "—", "")])
        else:
            theta = [point.bearing_deg * pi / 180 for point in self._nec_pattern.points]
            radius = [point.relative_gain_db + 60.0 for point in self._nec_pattern.points]
            theta.append(theta[0])
            radius.append(radius[0])
            axis.plot(theta, radius, color=TOKENS.chart_series[3], linewidth=2.2)
            axis.fill(theta, radius, color=TOKENS.chart_series[3], alpha=0.16)
            self._set_graph_details(
                [
                    (f"{point.bearing_deg:.1f}°", f"{point.relative_gain_db:+.2f} dB", "—", "—", f"NEC {point.absolute_gain_db:+.2f} dB")
                    for point in self._nec_pattern.points
                ]
            )
        self.figure.tight_layout()
        self._plot_annotation = None
        self.canvas.draw_idle()

    def _draw_time_chart(self, located) -> None:
        axis = self.figure.add_subplot(111)
        axis.set_facecolor(TOKENS.panel_background)
        ordered = sorted(located, key=lambda item: item.spot.observed_at)
        times = [item.spot.observed_at for item in ordered]
        snrs = [item.spot.snr_db for item in ordered]
        colors = [item.bearing_deg for item in ordered]
        scatter = axis.scatter(times, snrs, c=colors, cmap="hsv", vmin=0, vmax=360, s=18, alpha=0.75)
        colorbar = self.figure.colorbar(scatter, ax=axis, pad=0.02)
        colorbar.set_label("Azimut / Bearing (°)", color=TOKENS.text_primary)
        colorbar.ax.tick_params(colors=TOKENS.chart_labels)
        labels = [
            f"{item.spot.observed_at.astimezone(timezone.utc):%Y-%m-%d %H:%M UTC}\n"
            f"{item.spot.rx_call} · {item.spot.snr_db:+d} dB · {item.bearing_deg:.0f}° · {item.distance_km:.0f} km\n"
            f"{self._filter_context()}"
            for item in ordered
        ]
        self._graph_hover_data.append((scatter, labels))
        self._set_graph_details(
            [
                (
                    item.spot.observed_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                    f"{item.spot.snr_db:+d} dB",
                    "1",
                    item.spot.rx_call,
                    f"{item.bearing_deg:.0f}° · {item.distance_km:.0f} km",
                )
                for item in ordered
            ]
        )
        axis.set_title(self._text("graph_titles")["time"], color=TOKENS.text_primary)
        axis.set_ylabel("SNR (dB)", color=TOKENS.text_primary)
        axis.tick_params(colors=TOKENS.chart_labels)
        axis.grid(color=TOKENS.chart_grid, alpha=0.8)
        self.figure.autofmt_xdate()
        self.figure.tight_layout()
        self._plot_annotation = axis.annotate(
            "",
            xy=(0, 0),
            xytext=(14, 14),
            textcoords="offset points",
            bbox={"boxstyle": "round", "fc": TOKENS.surface_2, "ec": TOKENS.accent},
            color=TOKENS.text_primary,
        )
        self._plot_annotation.set_visible(False)
        self.canvas.draw_idle()

    def _draw_receiver_map(self, located) -> None:
        axis = self.figure.add_subplot(111)
        axis.set_facecolor(TOKENS.panel_background)
        grouped = {}
        for item in located:
            key = (item.spot.rx_call, item.spot.rx_grid)
            grouped.setdefault(key, []).append(item)
        points = []
        for (call, grid), items in grouped.items():
            try:
                latitude, longitude = maidenhead_to_latlon(grid)
            except ValueError:
                continue
            points.append(
                (
                    call,
                    grid,
                    latitude,
                    longitude,
                    float(median(item.spot.snr_db for item in items)),
                    len(items),
                )
            )
        scatter = axis.scatter(
            [point[3] for point in points],
            [point[2] for point in points],
            c=[point[4] for point in points],
            s=[24 + min(point[5], 30) * 4 for point in points],
            cmap="viridis",
            vmin=-25,
            vmax=10,
            alpha=0.85,
            edgecolors=TOKENS.panel_background,
            linewidths=0.5,
        )
        labels = [
            self._text("map_hover").format(
                call=point[0], grid=point[1], snr=point[4], count=point[5]
            )
            + "\n"
            + self._filter_context()
            for point in points
        ]
        self._graph_hover_data.append((scatter, labels))
        self._set_graph_details(
            [
                (f"{point[0]} · {point[1]}", f"{point[4]:+.1f} dB", str(point[5]), "1", f"{point[2]:.2f}, {point[3]:.2f}")
                for point in points
            ]
        )
        try:
            tx_latitude, tx_longitude = maidenhead_to_latlon(self.tx_grid.text())
            axis.scatter(
                [tx_longitude],
                [tx_latitude],
                marker="*",
                s=130,
                color=TOKENS.danger,
                edgecolors=TOKENS.panel_background,
                linewidths=0.8,
                label=self.callsign.text().strip().upper() or "TX",
                zorder=5,
            )
            legend = axis.legend(loc="lower left")
            legend.get_frame().set_facecolor(TOKENS.surface_1)
            for text_item in legend.get_texts():
                text_item.set_color(TOKENS.text_primary)
        except ValueError:
            pass
        colorbar = self.figure.colorbar(scatter, ax=axis, pad=0.02)
        colorbar.set_label("Median SNR (dB)", color=TOKENS.text_primary)
        colorbar.ax.tick_params(colors=TOKENS.chart_labels)
        axis.set_xlim(-180, 180)
        axis.set_ylim(-90, 90)
        axis.set_xticks(range(-180, 181, 60))
        axis.set_yticks(range(-90, 91, 30))
        axis.set_xlabel("Longitude (°)", color=TOKENS.text_primary)
        axis.set_ylabel("Latitude (°)", color=TOKENS.text_primary)
        axis.set_title(self._text("graph_titles")["map"], color=TOKENS.text_primary)
        axis.tick_params(colors=TOKENS.chart_labels)
        axis.grid(color=TOKENS.chart_grid, alpha=0.8)
        self.figure.tight_layout()
        self._plot_annotation = axis.annotate(
            "",
            xy=(0, 0),
            xytext=(14, 14),
            textcoords="offset points",
            bbox={"boxstyle": "round", "fc": TOKENS.surface_2, "ec": TOKENS.accent},
            color=TOKENS.text_primary,
        )
        self._plot_annotation.set_visible(False)
        self.canvas.draw_idle()

    def _draw_exposure_chart(self) -> None:
        axis = self.figure.add_subplot(111, projection="polar")
        axis.set_facecolor(TOKENS.panel_background)
        axis.set_theta_zero_location("N")
        axis.set_theta_direction(-1)
        width_deg = int(self.sector_width.currentData() or 30)
        observations = self.repository.list_exposure_observations(
            profile_id=self.antenna_profile.currentData(),
            band=self.band.currentText(),
            mode=self.mode.currentText(),
        )
        sectors = exposure_sector_profile(observations, self.tx_grid.text(), width_deg)
        theta = [sector.center_deg * pi / 180 for sector in sectors]
        radius = [(sector.detection_rate or 0.0) * 100 for sector in sectors]
        bars = axis.bar(
            theta,
            radius,
            width=max(1, width_deg - 1) * pi / 180,
            color=[TOKENS.success if sector.opportunities >= 10 else TOKENS.text_muted for sector in sectors],
            alpha=0.82,
        )
        for sector, bar in zip(sectors, bars):
            rate = "—" if sector.detection_rate is None else f"{sector.detection_rate * 100:.1f}%"
            confidence = (
                "—"
                if sector.confidence_low is None
                else f"{sector.confidence_low * 100:.1f}–{sector.confidence_high * 100:.1f}%"
            )
            self._graph_hover_data.append(
                (
                    bar,
                    self._text("exposure_hover").format(
                        detections=sector.detections,
                        opportunities=sector.opportunities,
                        rate=rate,
                        receivers=sector.unique_receivers,
                        confidence=confidence,
                    )
                    + "\n"
                    + self._filter_context(),
                )
            )
        self._set_graph_details(
            [
                (
                    f"{sector.center_deg - width_deg / 2:.0f}–{sector.center_deg + width_deg / 2:.0f}°",
                    "—" if sector.detection_rate is None else f"{sector.detection_rate * 100:.1f}%",
                    f"{sector.detections}/{sector.opportunities}",
                    str(sector.unique_receivers),
                    "—" if sector.confidence_low is None else f"95% CI {sector.confidence_low * 100:.1f}–{sector.confidence_high * 100:.1f}%",
                )
                for sector in sectors
            ]
        )
        interval_sectors = [sector for sector in sectors if sector.confidence_low is not None]
        if interval_sectors:
            axis.vlines(
                [sector.center_deg * pi / 180 for sector in interval_sectors],
                [sector.confidence_low * 100 for sector in interval_sectors],
                [sector.confidence_high * 100 for sector in interval_sectors],
                color=TOKENS.text_secondary,
                linewidth=1.2,
            )
        axis.set_rlim(0, 100)
        axis.set_yticks([25, 50, 75, 100], labels=["25%", "50%", "75%", "100%"])
        axis.tick_params(colors=TOKENS.chart_labels)
        axis.grid(color=TOKENS.chart_grid, alpha=0.8)
        axis.set_title(self._text("graph_titles")["exposure"], color=TOKENS.text_primary, pad=20)
        self.figure.tight_layout()
        self._plot_annotation = axis.annotate(
            "",
            xy=(0, 0),
            xytext=(14, 14),
            textcoords="offset points",
            bbox={"boxstyle": "round", "fc": TOKENS.surface_2, "ec": TOKENS.accent},
            color=TOKENS.text_primary,
        )
        self._plot_annotation.set_visible(False)
        self.canvas.draw_idle()

    def _filter_context(self) -> str:
        profile_name = self.antenna_profile.currentText()
        time_code = (self.time_filter.currentData() or ("all", None))[0]
        distance_code = self.distance_filter.currentData() or "all"
        period_code = self.period_filter.currentData() or "all"
        source_code = self.source_filter.currentData() or "all"
        return self._text("filter_context").format(
            call=self.callsign.text().strip().upper() or "—",
            band=self.band.currentText(),
            time=self._text("time_filters")[time_code],
            period=self._text("period_filters")[period_code],
            distance=self._text("distance_filters")[distance_code],
            source=self._text("source_filters")[source_code],
            profile=profile_name,
        )

    def _on_graph_hover(self, event) -> None:
        if self._plot_pinned:
            return
        self._show_graph_hit(event)

    def _show_graph_hit(self, event) -> bool:
        annotation = self._plot_annotation
        if annotation is None or event.inaxes is None:
            return False
        for artist, payload in self._graph_hover_data:
            contains, detail = artist.contains(event)
            if not contains:
                continue
            text = payload
            if isinstance(payload, list):
                indices = detail.get("ind", [])
                if not len(indices):
                    continue
                text = payload[int(indices[0])]
            annotation.xy = (event.xdata, event.ydata)
            annotation.set_text(text)
            annotation.set_visible(True)
            self.canvas.draw_idle()
            return True
        if annotation.get_visible():
            annotation.set_visible(False)
            self.canvas.draw_idle()
        return False

    def _on_graph_click(self, event) -> None:
        if self._show_graph_hit(event):
            self._plot_pinned = True
            return
        self._plot_pinned = False

    def _set_graph_details(self, rows) -> None:
        if not hasattr(self, "graph_details"):
            return
        self.graph_details.setRowCount(len(rows))
        for row, values in enumerate(rows):
            for column, value in enumerate(values):
                self.graph_details.setItem(row, column, QTableWidgetItem(str(value)))
        self.graph_details.resizeColumnsToContents()

    def _graph_options_changed(self, *_args) -> None:
        if not hasattr(self, "canvas"):
            return
        self.settings.setValue("graph_view", self.graph_view.currentData())
        self.settings.setValue("sector_width", self.sector_width.currentData())
        self.settings.setValue("time_filter", (self.time_filter.currentData() or ("all", None))[0])
        self.settings.setValue("distance_filter", self.distance_filter.currentData() or "all")
        self.settings.setValue("period_filter", self.period_filter.currentData() or "all")
        self.settings.setValue("source_filter", self.source_filter.currentData() or "all")
        self._update_graph_tooltip()
        sector_enabled = self.graph_view.currentData() not in ("time", "map", "model", "nec")
        self.sector_width.setEnabled(sector_enabled)
        self.sector_width_label.setEnabled(sector_enabled)
        self.refresh()

    def _fill_table(self, located) -> None:
        sorting = self.table.isSortingEnabled()
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(located))
        for row, item in enumerate(located):
            spot = item.spot
            source_full = self._text("source_filters").get(spot.source, spot.source)
            values = (
                TechnicalTableItem(
                    format_utc_timestamp(spot.observed_at),
                    sort_value=spot.observed_at.timestamp(),
                    tooltip=f"{format_utc_timestamp(spot.observed_at)} UTC",
                ),
                TechnicalTableItem(spot.rx_call, tooltip=spot.rx_call),
                TechnicalTableItem(spot.rx_grid, tooltip=spot.rx_grid),
                TechnicalTableItem(
                    format_signed_snr(spot.snr_db),
                    sort_value=spot.snr_db,
                    tooltip=f"{format_signed_snr(spot.snr_db)} dB",
                    numeric=True,
                ),
                TechnicalTableItem(
                    format_distance_km(item.distance_km),
                    sort_value=item.distance_km,
                    tooltip=f"{format_distance_km(item.distance_km)} km",
                    numeric=True,
                ),
                TechnicalTableItem(
                    format_bearing(item.bearing_deg),
                    sort_value=item.bearing_deg,
                    numeric=True,
                ),
                TechnicalTableItem(
                    format_frequency_mhz(spot.frequency_hz),
                    sort_value=spot.frequency_hz,
                    tooltip=f"{format_frequency_mhz(spot.frequency_hz)} MHz",
                    numeric=True,
                ),
                TechnicalTableItem(
                    compact_source(spot.source),
                    sort_value=source_full,
                    tooltip=source_full,
                ),
            )
            for column, value in enumerate(values):
                self.table.setItem(row, column, value)
        self.table.setSortingEnabled(sorting)
        self.report_panel.set_report_count(len(located))
        if not located:
            self.report_panel.set_selected_detail("")

    def _report_selection_changed(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            self.report_panel.set_selected_detail("")
            return
        values = [
            self.table.item(row, column).text() if self.table.item(row, column) else "—"
            for column in range(self.table.columnCount())
        ]
        source = (
            self.table.item(row, 7).toolTip()
            if self.table.item(row, 7) is not None
            else values[7]
        )
        self.report_panel.set_selected_detail(
            self._text("report_detail").format(
                time=values[0],
                call=values[1],
                grid=values[2],
                snr=values[3],
                distance=values[4],
                bearing=values[5],
                frequency=values[6],
                source=source,
            )
        )

    def _save_settings(self) -> None:
        self.settings.setValue("callsign", self.callsign.text().strip().upper())
        self.settings.setValue("tx_grid", self.tx_grid.text().strip().upper())
        self.settings.setValue("band", self.band.currentText())
        self.settings.setValue("mode", self.mode.currentText())
        self.settings.setValue("language", self.language_code)
        self.settings.setValue("wsjtx_port", self.wsjtx_port.value())
        self.settings.setValue("wsjtx_host", self.wsjtx_host.text().strip())
        self.settings.setValue("wsjtx_forward", self.wsjtx_forward.text().strip())
        self.settings.setValue("hamlib_enabled", int(self.hamlib_enabled.isChecked()))
        self.settings.setValue("rotator_enabled", int(self.rotator_enabled.isChecked()))
        self.settings.setValue("rx_activity_enabled", int(self.rx_activity_enabled.isChecked()))
        self.settings.setValue("hamlib_port", self.hamlib_port.value())
        self.settings.setValue("rotator_port", self.rotator_port.value())

    def _save_splitter_state(self, *_args) -> None:
        if hasattr(self, "main_splitter"):
            self.settings.setValue(
                "ui/main_splitter_state",
                self.main_splitter.saveState(),
            )

    def _reset_layout(self) -> None:
        self.settings.remove("ui/main_splitter_state")
        self.main_splitter.setSizes([760, 420])
        self._save_splitter_state()

    def _text(self, key: str):
        return TRANSLATIONS[self.language_code][key]

    def _update_graph_tooltip(self) -> None:
        mode = self.graph_view.currentData() or "snr"
        content = (
            self._text("graph_help")[mode]
            + "\n\n"
            + self._text("pin_help")
        )
        self.graph_info.setToolTip(
            "<table width='340'><tr><td>"
            + escape(content).replace("\n", "<br>")
            + "</td></tr></table>"
        )
        self.graph_info.setAccessibleDescription(content)

    def _change_language(self, language_code: str) -> None:
        self.language_code = language_code
        self._apply_language()
        self._set_connection_state(self._connection_state, "")
        self.refresh()

    def _apply_language(self) -> None:
        self.subtitle.setText(self._text("subtitle"))
        self.callsign_label.setText(self._text("callsign"))
        self.tx_grid_label.setText(self._text("tx_grid"))
        self.band_label.setText(self._text("band"))
        self.mode_label.setText(self._text("mode"))
        self.language_label.setText(self._text("language"))
        self.wsjtx_port_label.setText(self._text("wsjtx_port"))
        self.wsjtx_host_label.setText(self._text("wsjtx_address"))
        self.wsjtx_forward_label.setText(self._text("wsjtx_forward"))
        self.wsjtx_host.setToolTip(self._text("wsjtx_network_tooltip"))
        self.wsjtx_forward.setToolTip(self._text("wsjtx_network_tooltip"))
        self.antenna_profile_label.setText(self._text("antenna_profile"))
        self.manage_profiles_button.setText(self._text("manage_profiles"))
        self.ab_compare_button.setText(self._text("ab_compare"))
        self.experiment_button.setText(self._text("experiment"))
        self.setup_button.setText(self._text("setup"))
        self.updates_button.setText(self._text("updates"))
        self.diagnostics_button.setText(self._text("diagnostics"))
        self.nec_import_button.setText(self._text("nec_import"))
        self.antenna_profile.setToolTip(self._text("profile_tooltip"))
        self.hamlib_label.setText(self._text("hamlib"))
        self.hamlib_enabled.setToolTip(self._text("hamlib_tooltip"))
        self.rx_activity_label.setText(self._text("rx_activity"))
        self.rx_activity_enabled.setToolTip(self._text("rx_activity_tooltip"))
        self.operational_header.collection.section_label.setText(
            self._text("collection_section")
        )
        self.graph_info.setAccessibleName(
            "Nápověda ke grafu" if self.language_code == "CZE" else "Chart help"
        )
        self._set_collection_ui_state(
            "running" if self._collecting else self._collection_ui_state
        )
        self.demo_button.setText(self._text("demo"))
        self.import_button.setText(self._text("import"))
        self.export_button.setText(self._text("export"))
        self.history_button.setText(self._text("history"))
        self.history_button.setToolTip(self._text("history_tooltip"))
        self.clear_button.setText(self._text("clear"))
        self.file_menu.setTitle(self._text("menu_file"))
        self.data_menu.setTitle(self._text("menu_data"))
        self.tools_menu.setTitle(self._text("menu_tools"))
        self.settings_menu.setTitle(self._text("menu_settings"))
        self.help_menu.setTitle(self._text("menu_help"))
        self.import_action.setText(self._text("import"))
        self.export_action.setText(self._text("export"))
        self.nec_action.setText(self._text("nec_import"))
        self.exit_action.setText(self._text("exit"))
        self.history_action.setText(self._text("history"))
        self.demo_action.setText(self._text("demo"))
        self.clear_action.setText(self._text("clear"))
        self.spot_map_action.setText(self._text("spot_map"))
        self.profiles_action.setText(self._text("manage_profiles"))
        self.ab_action.setText(self._text("ab_compare"))
        self.experiment_action.setText(self._text("experiment"))
        self.campaigns_action.setText(self._text("campaigns"))
        self.coverage_action.setText(self._text("coverage"))
        self.propagation_action.setText(self._text("propagation_conditions"))
        self.communications_action.setText(self._text("communications"))
        self.external_tools_action.setText(self._text("external_tools"))
        self.updates_action.setText(self._text("updates"))
        self.appearance_action.setText(
            "Vzhled aplikace…" if self.language_code == "CZE" else "Appearance…"
        )
        self.language_menu.setTitle(self._text("language_menu"))
        for code, action in self.language_actions.items():
            action.setChecked(code == self.language_code)
        self.reset_layout_action.setText(self._text("reset_layout"))
        self.diagnostics_action.setText(self._text("diagnostics"))
        self.help_contents_action.setText(self._text("help_contents"))
        self.about_action.setText(self._text("about"))
        self.wsjtx_indicator.setToolTip(self._text("wsjtx_tooltip"))
        self.graph_view_label.setText(self._text("graph_view"))
        self.sector_width_label.setText(self._text("sector_width"))
        self.time_filter_label.setText(self._text("time_filter"))
        self.distance_filter_label.setText(self._text("distance_filter"))
        self.period_filter_label.setText(self._text("period_filter"))
        self.source_filter_label.setText(self._text("source_filter"))
        for index in range(self.graph_view.count()):
            code = self.graph_view.itemData(index)
            self.graph_view.setItemText(index, self._text("graph_modes")[code])
        for index in range(self.time_filter.count()):
            code = self.time_filter.itemData(index)[0]
            self.time_filter.setItemText(index, self._text("time_filters")[code])
        for index in range(self.distance_filter.count()):
            code = self.distance_filter.itemData(index)
            self.distance_filter.setItemText(index, self._text("distance_filters")[code])
        for index in range(self.period_filter.count()):
            code = self.period_filter.itemData(index)
            self.period_filter.setItemText(index, self._text("period_filters")[code])
        for index in range(self.source_filter.count()):
            code = self.source_filter.itemData(index)
            self.source_filter.setItemText(index, self._text("source_filters")[code])
        self.sector_width.setToolTip(self._text("sector_tip"))
        self._update_graph_tooltip()
        self.graph_details.setAccessibleName(self._text("graph_details"))
        self.table.setAccessibleName(self._text("reports_title"))
        self.canvas.setAccessibleDescription(self._filter_context())
        self.callsign.setAccessibleName(self._text("callsign"))
        self.tx_grid.setAccessibleName(self._text("tx_grid"))
        self.band.setAccessibleName(self._text("band"))
        self.mode.setAccessibleName(self._text("mode"))
        self.antenna_profile.setAccessibleName(self._text("antenna_profile"))
        self.graph_details.setHorizontalHeaderLabels(self._text("graph_detail_headers"))
        sector_enabled = self.graph_view.currentData() not in ("time", "map", "model", "nec")
        self.sector_width.setEnabled(sector_enabled)
        self.sector_width_label.setEnabled(sector_enabled)
        self._render_wsjtx_indicator()
        self._render_hamlib_indicator()
        self._render_rotator_indicator()
        self._render_campaign_indicator()
        self.table.setHorizontalHeaderLabels(self._text("headers"))
        self.report_panel.set_texts(
            self._text("reports_title"),
            self._text("no_reports_title"),
            self._text("no_reports_detail"),
        )
        self.sector_quality_panel.set_title(self._text("sector_quality_title"))
        self._reload_antenna_profiles(self.antenna_profile.currentData())
        if not self.status.text():
            self.status.setText(self._text("ready"))

    def _reload_antenna_profiles(self, selected_id: int | None = None) -> None:
        if selected_id is None:
            current = self.antenna_profile.currentData() if self.antenna_profile.count() else None
            stored = self.settings.value("antenna_profile_id", None)
            selected_id = current if current is not None else (int(stored) if stored else None)
        self.antenna_profile.blockSignals(True)
        self.antenna_profile.clear()
        self.antenna_profile.addItem(self._text("no_profile"), None)
        for profile in self.repository.list_antenna_profiles():
            self.antenna_profile.addItem(profile.name, profile.id)
        index = self.antenna_profile.findData(selected_id)
        self.antenna_profile.setCurrentIndex(max(0, index))
        self.antenna_profile.blockSignals(False)

    def _manage_antenna_profiles(self) -> None:
        dialog = AntennaProfileDialog(self.repository, self.language_code, self)
        dialog.exec()
        self._reload_antenna_profiles(dialog.profile_id)
        self._antenna_profile_selected()

    def _open_ab_comparison(self) -> None:
        dialog = AbComparisonDialog(
            self.repository,
            self.language_code,
            self.tx_grid.text(),
            self.band.currentText(),
            self.mode.currentText(),
            self,
        )
        dialog.exec()

    def _open_experiment(self) -> None:
        dialog = ExperimentDialog(
            self.repository,
            self.language_code,
            self._select_profile_from_experiment,
            self,
            self.band.currentText(),
            self.mode.currentText(),
        )
        dialog.exec()

    def _open_campaigns(self) -> None:
        dialog = CampaignDialog(
            self.repository,
            self.language_code,
            self.callsign.text(),
            self.tx_grid.text(),
            self.band.currentText(),
            self.mode.currentText(),
            self.antenna_profile.currentData(),
            self,
        )
        dialog.exec()
        coverage_campaign_id = dialog.coverage_campaign_id
        self._render_campaign_indicator()
        self.refresh()
        if coverage_campaign_id is not None:
            self._show_coverage(coverage_campaign_id)

    def _open_coverage(self) -> None:
        active = self.repository.active_campaign()
        self._show_coverage(active.id if active is not None else None)

    def _open_propagation_conditions(self) -> None:
        PropagationConditionsDialog(
            self.repository,
            self.language_code,
            self,
        ).exec()

    def _show_coverage(self, campaign_id: int | None) -> None:
        campaign = (
            self.repository.get_campaign(campaign_id)
            if campaign_id is not None
            else None
        )
        if campaign is not None:
            context = (
                f"{self._text('campaign_active').format(name=campaign.name)} · "
                f"{campaign.tx_call} · {campaign.band} {campaign.mode} · "
                f"{campaign.antenna_profile_name or '—'}"
            )
        else:
            context = self._filter_context()
        CoverageDialog(
            list(self._located_spots(campaign_id)),
            self.language_code,
            context,
            self,
            campaign=campaign,
        ).exec()

    def _open_spot_map(self) -> None:
        if self._spot_map_dialog is not None:
            self._spot_map_dialog.close()
        dialog = SpotMapDialog(
            list(self._located_spots()),
            self.tx_grid.text().strip(),
            self.callsign.text().strip(),
            self.language_code,
            self._filter_context(),
            self,
        )
        self._spot_map_dialog = dialog
        dialog.destroyed.connect(
            lambda *_args, opened_dialog=dialog: self._spot_map_closed(opened_dialog)
        )
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def _spot_map_closed(self, dialog: SpotMapDialog) -> None:
        if self._spot_map_dialog is dialog:
            self._spot_map_dialog = None

    def _open_communication_settings(self) -> None:
        dialog = CommunicationSettingsDialog(
            CommunicationSettings(
                wsjtx_host=self.wsjtx_host.text().strip(),
                wsjtx_port=self.wsjtx_port.value(),
                wsjtx_forward=self.wsjtx_forward.text().strip(),
                hamlib_enabled=self.hamlib_enabled.isChecked(),
                hamlib_port=self.hamlib_port.value(),
                rotator_enabled=self.rotator_enabled.isChecked(),
                rotator_port=self.rotator_port.value(),
                rx_activity_enabled=self.rx_activity_enabled.isChecked(),
            ),
            self.language_code,
            self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        controls = (
            self.wsjtx_host,
            self.wsjtx_port,
            self.wsjtx_forward,
            self.hamlib_enabled,
            self.hamlib_port,
            self.rotator_enabled,
            self.rotator_port,
            self.rx_activity_enabled,
        )
        for control in controls:
            control.blockSignals(True)
        try:
            self.wsjtx_host.setText(values.wsjtx_host)
            self.wsjtx_port.setValue(values.wsjtx_port)
            self.wsjtx_forward.setText(values.wsjtx_forward)
            self.hamlib_enabled.setChecked(values.hamlib_enabled)
            self.hamlib_port.setValue(values.hamlib_port)
            self.rotator_enabled.setChecked(values.rotator_enabled)
            self.rotator_port.setValue(values.rotator_port)
            self.rx_activity_enabled.setChecked(values.rx_activity_enabled)
        finally:
            for control in controls:
                control.blockSignals(False)
        self._restart_wsjtx_listener()
        self._restart_hamlib()
        self._toggle_hamlib(values.hamlib_enabled)
        self._restart_rotator()
        self._toggle_rotator(values.rotator_enabled)
        self._rx_activity_toggled(values.rx_activity_enabled)
        self._save_settings()

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            self._text("about"),
            self._text("about_text").format(version=__version__),
        )

    def _show_help(self) -> None:
        HelpDialog(self.language_code, self).exec()

    def _open_setup(self) -> None:
        dialog = SetupDialog(self.settings, self.language_code, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.wsjtx_port.setValue(int(self.settings.value("wsjtx_port", 2237)))
            self.hamlib_port.setValue(int(self.settings.value("hamlib_port", 4532)))

    def _import_nec_output(self) -> None:
        filename, _selected = QFileDialog.getOpenFileName(
            self, self._text("nec_import_title"), "", "NEC output (*.out *.txt);;All files (*)"
        )
        if not filename:
            return
        try:
            self._nec_pattern = parse_nec_output(Path(filename).read_text(encoding="utf-8", errors="replace"))
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, self._text("nec_import_failed"), str(exc))
            return
        self.graph_view.setCurrentIndex(self.graph_view.findData("nec"))

    def show_setup_if_needed(self) -> None:
        if not bool(int(self.settings.value("onboarding_completed", 0))):
            self._open_setup()

    def _open_updates(self) -> None:
        UpdateDialog(self.settings, self.language_code, self).exec()

    def check_updates_at_startup(self) -> None:
        def worker() -> None:
            try:
                result = check_for_update(DEFAULT_RELEASE_MANIFEST_URL, __version__)
            except Exception as exc:
                self.bridge.update_failed.emit(str(exc))
            else:
                self.bridge.update_checked.emit(result)

        threading.Thread(target=worker, daemon=True, name="update-check").start()

    def _handle_update_check(self, result) -> None:
        if result.update_available:
            self.status.setText(
                self._text("update_available").format(version=result.manifest.version)
            )

    def _export_diagnostics(self) -> None:
        answer = QMessageBox.question(
            self,
            self._text("diagnostics_title"),
            self._text("diagnostics_confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        filename, _selected = QFileDialog.getSaveFileName(
            self,
            self._text("diagnostics_title"),
            "antenna-pattern-lab-diagnostics.json",
            "JSON (*.json)",
        )
        if not filename:
            return
        report = build_diagnostic_report(
            app_version=__version__,
            database_path=str(self.repository.path),
            spot_count=self.repository.count(),
            tx_session_count=self.repository.tx_session_count(),
            callsign=self.callsign.text(),
            tx_grid=self.tx_grid.text(),
            band=self.band.currentText(),
            mode=self.mode.currentText(),
            mqtt_state=self._connection_state,
            wsjtx_state=self._wsjtx_connection_state,
            wsjtx_operating_state=self._wsjtx_operating_state,
            hamlib_state=self._hamlib_connection_state,
            hamlib_enabled=self.hamlib_enabled.isChecked(),
            rotator_state=self._rotator_connection_state,
            rotator_enabled=self.rotator_enabled.isChecked(),
            database_schema_version=self.repository.schema_version,
            database_integrity=self.repository.integrity_status(),
            database_backup_path=(
                str(self.repository.last_backup_path)
                if self.repository.last_backup_path
                else None
            ),
            database_migration_performed=self.repository.migration_performed,
            dependencies=detect_external_tools(),
        )
        Path(filename).write_text(diagnostic_json(report), encoding="utf-8")
        self.status.setText(self._text("diagnostics_saved").format(path=filename))

    def _select_profile_from_experiment(self, profile_id: int) -> None:
        index = self.antenna_profile.findData(profile_id)
        if index >= 0:
            self.antenna_profile.setCurrentIndex(index)

    def _antenna_profile_selected(self, *_args) -> None:
        profile_id = self.antenna_profile.currentData()
        if profile_id is None:
            self.settings.remove("antenna_profile_id")
        else:
            self.settings.setValue("antenna_profile_id", profile_id)
        self._update_rotator_safety()
        if hasattr(self, "rotator_indicator"):
            self._render_rotator_indicator()
        if hasattr(self, "canvas"):
            self.refresh()

    def _selected_rotator_target(self) -> float | None:
        profile_id = self.antenna_profile.currentData()
        if profile_id is None:
            return None
        try:
            return mechanical_target(
                self.repository.get_antenna_profile(profile_id)
            )
        except ValueError:
            return None

    def _set_connection_state(self, state: str, detail: str) -> None:
        self._connection_state = state if state in ("disconnected", "connecting", "connected", "error") else "error"
        label = self._text("connection")[self._connection_state]
        semantic_state = {
            "disconnected": "inactive",
            "connecting": "connecting",
            "connected": "connected",
            "error": "error",
        }[self._connection_state]
        self.connection_indicator.set_indicator(
            "PSK Reporter",
            semantic_state,
            detail or self._text("connection_status")[self._connection_state],
            label,
        )
        self.status.setText(self._text("connection_status")[self._connection_state])
        if self._collecting:
            if self._connection_state == "connected":
                self._set_collection_ui_state("running")
            elif self._connection_state == "connecting":
                self._set_collection_ui_state("connecting")
            elif self._connection_state == "error":
                self._set_collection_ui_state("failed", detail)

    def _restart_wsjtx_listener(self) -> None:
        port = self.wsjtx_port.value()
        host = self.wsjtx_host.text().strip() or "127.0.0.1"
        try:
            targets = parse_forward_targets(
                self.wsjtx_forward.text(), listener_host=host, listener_port=port
            )
        except ValueError as exc:
            QMessageBox.warning(self, self._text("wsjtx_network_error"), str(exc))
            return
        if (
            port == self.wsjtx_listener.port
            and host == self.wsjtx_listener.host
            and targets == self.wsjtx_listener.forward_targets
            and self._wsjtx_connection_state != "error"
        ):
            return
        self._finish_active_tx_sessions()
        self.wsjtx_listener.stop()
        self.wsjtx_listener.port = port
        self.wsjtx_listener.host = host
        self.wsjtx_listener.forward_targets = targets
        self.settings.setValue("wsjtx_port", port)
        self.settings.setValue("wsjtx_host", host)
        self.settings.setValue("wsjtx_forward", self.wsjtx_forward.text().strip())
        self.wsjtx_listener.start()

    def _set_wsjtx_state(self, state: str, detail: str) -> None:
        self._wsjtx_connection_state = state
        self._wsjtx_detail = detail
        if state not in ("connected",):
            self._wsjtx_operating_state = ""
        self._render_wsjtx_indicator()

    def _render_wsjtx_indicator(self) -> None:
        state = self._wsjtx_connection_state
        label_key = self._wsjtx_operating_state if state == "connected" and self._wsjtx_operating_state else state
        labels = self._text("wsjtx")
        semantic_state = {
            "disconnected": "inactive",
            "waiting": "waiting",
            "connected": "connected",
            "stale": "warning",
            "error": "error",
        }.get(state, "error")
        self.wsjtx_indicator.set_indicator(
            "WSJT-X",
            semantic_state,
            f"{self._text('wsjtx_tooltip')}\n{self._wsjtx_detail}".strip(),
            labels.get(label_key, labels["error"]),
        )

    def _handle_wsjtx_message(self, message: object) -> None:
        if isinstance(message, Heartbeat):
            self._wsjtx_detail = " ".join(
                part for part in (message.header.instance_id, message.version, message.revision) if part
            )
            self._render_wsjtx_indicator()
            return
        if isinstance(message, Close):
            self._finish_tx_session(message.header.instance_id)
            self._set_wsjtx_state("waiting", message.header.instance_id)
            return
        if not isinstance(message, Status):
            return
        instance_id = message.header.instance_id
        self._wsjtx_operating_state = "tx" if message.transmitting else "rx"
        self._wsjtx_detail = (
            f"{instance_id} · {message.de_call or '?'} · {message.mode} · "
            f"{message.dial_frequency_hz / 1_000_000:.6f} MHz"
        )
        now = datetime.now(timezone.utc)
        if message.transmitting and instance_id not in self._active_tx_sessions:
            session_id = self.repository.start_tx_session(
                instance_id=instance_id,
                de_call=message.de_call or self.callsign.text(),
                de_grid=message.de_grid or self.tx_grid.text(),
                mode=message.tx_mode or message.mode,
                dial_frequency_hz=message.dial_frequency_hz,
                tx_frequency_hz=message.dial_frequency_hz + message.tx_df_hz,
                tx_message=message.tx_message,
                configuration_name=message.configuration_name,
                antenna_profile_id=self.antenna_profile.currentData(),
                rig_frequency_hz=(
                    self._latest_rig_state.frequency_hz if self._latest_rig_state else None
                ),
                rig_mode=self._latest_rig_state.mode if self._latest_rig_state else None,
                rig_ptt=self._latest_rig_state.ptt if self._latest_rig_state else None,
                started_at=now,
                rig_power_fraction=(
                    self._latest_rig_state.power_fraction if self._latest_rig_state else None
                ),
                rig_swr=self._latest_rig_state.swr if self._latest_rig_state else None,
                rotator_azimuth_deg=(
                    self._latest_rotator_state.azimuth_deg
                    if self._latest_rotator_state
                    else None
                ),
                rotator_elevation_deg=(
                    self._latest_rotator_state.elevation_deg
                    if self._latest_rotator_state
                    else None
                ),
            )
            self._active_tx_sessions[instance_id] = session_id
            self._tx_rotator_tracking[session_id] = (
                (
                    self._latest_rotator_state.azimuth_deg
                    if self._latest_rotator_state
                    else None
                ),
                0.0,
            )
            self._tx_rotator_targets[session_id] = self._selected_rotator_target()
            self._update_rotator_safety()
            self._render_rotator_indicator()
        elif not message.transmitting:
            self._finish_tx_session(instance_id, now)
        self._render_wsjtx_indicator()
        self.refresh()

    def _finish_tx_session(self, instance_id: str, ended_at=None) -> None:
        session_id = self._active_tx_sessions.pop(instance_id, None)
        if session_id is not None:
            start_azimuth, max_deviation = self._tx_rotator_tracking.pop(
                session_id, (None, 0.0)
            )
            self._tx_rotator_targets.pop(session_id, None)
            self.repository.finish_tx_session(
                session_id,
                ended_at or datetime.now(timezone.utc),
                rotator_azimuth_deg=(
                    self._latest_rotator_state.azimuth_deg
                    if self._latest_rotator_state
                    else None
                ),
                rotator_elevation_deg=(
                    self._latest_rotator_state.elevation_deg
                    if self._latest_rotator_state
                    else None
                ),
                rotator_max_deviation_deg=(
                    max_deviation if start_azimuth is not None else None
                ),
            )
            self._update_rotator_safety()
            self._render_rotator_indicator()

    def _finish_active_tx_sessions(self) -> None:
        for instance_id in list(self._active_tx_sessions):
            self._finish_tx_session(instance_id)

    def _toggle_hamlib(self, enabled: bool) -> None:
        self.settings.setValue("hamlib_enabled", int(enabled))
        if enabled:
            self.hamlib_monitor.start()
        else:
            self._latest_rig_state = None
            self.hamlib_monitor.stop()

    def _toggle_rotator(self, enabled: bool) -> None:
        self.settings.setValue("rotator_enabled", int(enabled))
        if enabled:
            self.rotator_monitor.start()
        else:
            self._latest_rotator_state = None
            self.rotator_monitor.stop()
            self._update_rotator_safety()
            self._render_rotator_indicator()

    def _activity_fields(self) -> list[str]:
        if not self.rx_activity_enabled.isChecked():
            return []
        return self.repository.known_receiver_fields(self.band.currentText(), limit=12)

    def _rx_activity_toggled(self, enabled: bool) -> None:
        self.settings.setValue("rx_activity_enabled", int(enabled))
        self._collection_configuration_changed()

    def _store_receiver_activity(self, spot: Spot) -> None:
        self.repository.record_receiver_activity(spot)

    def _restart_hamlib(self) -> None:
        port = self.hamlib_port.value()
        if port == self.hamlib_monitor.client.port:
            return
        was_enabled = self.hamlib_enabled.isChecked()
        self.hamlib_monitor.stop()
        self.hamlib_monitor.client.port = port
        self.settings.setValue("hamlib_port", port)
        if was_enabled:
            self.hamlib_monitor.start()

    def _restart_rotator(self) -> None:
        port = self.rotator_port.value()
        if port == self.rotator_monitor.client.port:
            return
        was_enabled = self.rotator_enabled.isChecked()
        self.rotator_monitor.stop()
        self.rotator_monitor.client.port = port
        self.settings.setValue("rotator_port", port)
        if was_enabled:
            self.rotator_monitor.start()

    def _set_hamlib_state(self, state: str, detail: str) -> None:
        self._hamlib_connection_state = state
        self._hamlib_detail = detail
        self._render_hamlib_indicator()

    def _handle_rig_state(self, state: RigState) -> None:
        self._latest_rig_state = state
        details = [
            f"{state.frequency_hz / 1_000_000:.6f} MHz",
            state.mode,
            "TX" if state.ptt else "RX",
        ]
        if state.power_fraction is not None:
            details.append(f"RF {state.power_fraction * 100:.0f}%")
        if state.swr is not None:
            details.append(f"SWR {state.swr:.2f}")
        self._hamlib_detail = " · ".join(details)
        self._render_hamlib_indicator()

    def _render_hamlib_indicator(self) -> None:
        state = self._hamlib_connection_state
        label = self._text("hamlib_states").get(state, self._text("hamlib_states")["error"])
        semantic_state = {
            "disabled": "inactive",
            "connecting": "connecting",
            "connected": "connected",
            "error": "error",
        }.get(state, "error")
        self.hamlib_indicator.set_indicator(
            "Hamlib",
            semantic_state,
            f"{self._text('hamlib_tooltip')}\n{self._hamlib_detail}".strip(),
            label,
        )

    def _set_rotator_state(self, state: str, detail: str) -> None:
        self._rotator_connection_state = state
        self._rotator_detail = detail
        self._update_rotator_safety()
        self._render_rotator_indicator()

    def _handle_rotator_state(self, state: RotatorState) -> None:
        self._latest_rotator_state = state
        for session_id, (start_azimuth, maximum) in tuple(
            self._tx_rotator_tracking.items()
        ):
            if start_azimuth is None:
                continue
            difference = abs(
                ((state.azimuth_deg - start_azimuth + 180.0) % 360.0) - 180.0
            )
            self._tx_rotator_tracking[session_id] = (
                start_azimuth,
                max(maximum, difference),
            )
        self._rotator_detail = (
            f"Az {state.azimuth_deg:.1f}° · El {state.elevation_deg:.1f}°"
        )
        self._update_rotator_safety()
        self._render_rotator_indicator()

    def _update_rotator_safety(self) -> None:
        if (
            self._rotator_connection_state != "connected"
            or self._latest_rotator_state is None
        ):
            self._rotator_safety = RotatorSafety("none", (), None, 0.0)
            return
        if self._active_tx_sessions:
            results = []
            for session_id in self._active_tx_sessions.values():
                _start, movement = self._tx_rotator_tracking.get(
                    session_id, (None, 0.0)
                )
                results.append(
                    evaluate_rotator_safety(
                        current_azimuth_deg=self._latest_rotator_state.azimuth_deg,
                        target_azimuth_deg=self._tx_rotator_targets.get(session_id),
                        movement_deg=movement,
                        transmitting=True,
                    )
                )
            warnings = tuple(
                code
                for code in ("moving_during_tx", "profile_mismatch")
                if any(code in result.warnings for result in results)
            )
            self._rotator_safety = RotatorSafety(
                severity="error" if warnings else "none",
                warnings=warnings,
                target_error_deg=max(
                    (
                        result.target_error_deg
                        for result in results
                        if result.target_error_deg is not None
                    ),
                    default=None,
                ),
                movement_deg=max(
                    (result.movement_deg for result in results), default=0.0
                ),
            )
            return
        self._rotator_safety = evaluate_rotator_safety(
            current_azimuth_deg=self._latest_rotator_state.azimuth_deg,
            target_azimuth_deg=self._selected_rotator_target(),
        )

    def _render_rotator_indicator(self) -> None:
        state = self._rotator_connection_state
        labels = self._text("rotator_states")
        safety = self._rotator_safety
        label = labels.get(state, labels["error"])
        if safety.warnings:
            label = " + ".join(
                self._text("rotator_alerts")[warning]
                for warning in safety.warnings
            )
        position = (
            f" · {self._latest_rotator_state.azimuth_deg:.0f}°"
            if state == "connected" and self._latest_rotator_state is not None
            else ""
        )
        alert_details = []
        if "moving_during_tx" in safety.warnings:
            alert_details.append(
                self._text("rotator_alert_detail")["moving_during_tx"].format(
                    movement=safety.movement_deg
                )
            )
        if "profile_mismatch" in safety.warnings:
            alert_details.append(
                self._text("rotator_alert_detail")["profile_mismatch"].format(
                    error=safety.target_error_deg or 0.0
                )
            )
        semantic_state = (
            "error"
            if safety.severity == "error"
            else "warning"
            if safety.severity == "warning"
            else {
                "disabled": "inactive",
                "connecting": "connecting",
                "connected": "connected",
                "error": "error",
            }.get(state, "error")
        )
        self.rotator_indicator.set_indicator(
            self._text("rotator_name"),
            semantic_state,
            "\n".join(
                part
                for part in (
                    self._text("rotator_tooltip"),
                    self._rotator_detail,
                    *alert_details,
                )
                if part
            ),
            f"{label}{position}",
        )

    def _render_campaign_indicator(self) -> None:
        active = self.repository.active_campaign()
        if active is None:
            self.campaign_indicator.setText(self._text("campaign_none"))
            self.campaign_indicator.setProperty("statusRole", "inactive")
            repolish(self.campaign_indicator)
            self.campaign_indicator.setToolTip("")
            return
        located = [
            item
            for spot in self.repository.list_spots(campaign_id=active.id)
            if (item := locate_spot(spot, active.tx_grid))
        ]
        progress = assess_campaign_progress(active, located)
        self.campaign_indicator.setText(
            (
                self._text("campaign_goal_reached").format(name=active.name)
                if progress.complete
                else self._text("campaign_goal_progress").format(
                    name=active.name,
                    met=progress.met_count,
                )
            )
        )
        self.campaign_indicator.setProperty(
            "statusRole", "success" if progress.complete else "warning"
        )
        repolish(self.campaign_indicator)
        self.campaign_indicator.setToolTip(
            (
                f"{active.band} {active.mode} · "
                + self._text("campaign_goal_tip").format(
                    spots=progress.spot_count,
                    target_spots=active.target_spots,
                    receivers=progress.unique_receivers,
                    target_receivers=active.target_receivers,
                    sectors=progress.supported_sector_count,
                    target_sectors=active.target_sectors,
                    blocks=progress.time_block_count,
                    target_blocks=active.target_time_blocks,
                )
            )
        )

    def closeEvent(self, event) -> None:
        self._finish_active_tx_sessions()
        self.wsjtx_listener.stop()
        self.hamlib_monitor.stop()
        self.rotator_monitor.stop()
        self.collector.stop()
        self._save_settings()
        self._save_splitter_state()
        super().closeEvent(event)
