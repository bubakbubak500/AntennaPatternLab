from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QListWidget,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
)


HELP = {
    "CZE": {
        "title": "Nápověda Antenna Pattern Lab",
        "close": "Zavřít",
        "sections": [
            (
                "quick",
                "Začínáme",
                """
                <h2>Začínáme</h2>
                <ol>
                  <li>Vyplňte vlastní značku a TX lokátor.</li>
                  <li>Zvolte pásmo, mód a neměnnou verzi anténního profilu.</li>
                  <li>Pro kontrolu rozhraní použijte <b>Nápověda → Přidat demo data</b>.</li>
                  <li>Pro reálné měření spusťte WSJT-X a živý sběr PSK Reporteru.</li>
                  <li>Delší měření ukládejte jako pojmenovanou kampaň.</li>
                </ol>
                <p>Hlavním výsledkem není sledování FT8 provozu, ale empirické
                modelování směrového diagramu antény z opakovaných reportů.</p>
                """,
            ),
            (
                "sources",
                "Zdroje dat a import",
                """
                <h2>Zdroje dat</h2>
                <p><b>Živý sběr</b> odebírá nové reporty z MQTT PSK Reporteru.
                Zelené spojení znamená potvrzené přihlášení a odběr tématu.</p>
                <p><b>Načíst historii</b> používá oddělené HTTP rozhraní pro
                posledních 1–24 hodin a respektuje pětiminutový limit.</p>
                <p><b>CSV</b> přenáší úplné řádky spotů Antenna Pattern Lab.
                <b>ADIF</b> importuje dokončená QSO z WSJT-X; RST_RCVD představuje
                report, který protistanice poslala o vašem signálu. ADIF je
                výběrový vzorek uskutečněných spojení, nikoli náhrada pasivních
                PSK Reporter detekcí, proto lze zdroje filtrovat odděleně.</p>
                <p><b>Vymazat spoty</b> odstraní spoty a přiřazení TX relací po
                potvrzení, ale nemaže definice kampaní, profily ani jejich deníky.</p>
                """,
            ),
            (
                "wsjtx",
                "WSJT-X a TX relace",
                """
                <h2>WSJT-X UDP</h2>
                <p>WSJT-X nastavte na UDP server a port uvedený v Nastavení →
                Komunikace. Stav RX/TX se potvrdí až platným Heartbeat/Status
                paketem. Multicast a UDP forwarding umožní souběh s JTAlert nebo
                GridTrackerem.</p>
                <p>Během vysílání aplikace vytvoří TX relaci a uloží frekvenci,
                mód, zprávu, profil antény, stav rádia a rotátoru. Pozdější spot se
                k relaci přiřadí podle času, značky, módu a frekvence.</p>
                """,
            ),
            (
                "graphs",
                "Grafy a filtry",
                """
                <h2>Grafy a filtry</h2>
                <p>Čas, vzdálenost, den/noc, pásmo, mód a zdroj dat vždy určují
                vstup grafu i tabulky. Užší sektor dává více detailu, ale méně
                vzorků.</p>
                <ul>
                  <li><b>Směrový profil</b>: medián SNR a fyzikálně rozumně
                  vyhlazený obrys bez vymyšlených nul.</li>
                  <li><b>Časově vyvážený</b>: každý 30minutový blok má stejnou váhu.</li>
                  <li><b>Po odečtení trendu</b>: odstraní pomalý společný drift.</li>
                  <li><b>Vyvážený podle RX</b>: jeden hlas přijímače na sektor,
                  omezený skórem stability.</li>
                  <li><b>Kontrolní skupina</b>: odečte společný trend pouze při
                  dostatku stabilních RX v různých směrech.</li>
                  <li><b>Počet, dosah, čas, mapa a expozice</b>: doplňkové pohledy
                  na pokrytí, extrémy, průběh a doložené příležitosti k detekci.</li>
                </ul>
                <p>Ikona ⓘ vysvětluje aktivní graf. Bod lze kliknutím připnout;
                stejné hodnoty jsou v tabulce pod grafem.</p>
                """,
            ),
            (
                "map",
                "Mapa spotů",
                """
                <h2>Mapa spotů</h2>
                <p>Samostatná mapa přebírá aktivní filtry hlavního okna. Při
                najetí na RX vykreslí trasu po velké kružnici, azimut, vzdálenost,
                medián SNR, počet reportů a poslední čas. Mapa má pevný celosvětový
                rozsah; záměrně nemá navigační lištu, aby se její měřítko a význam
                neměnily nechtěným zoomem.</p>
                """,
            ),
            (
                "profiles",
                "Anténní profily a model",
                """
                <h2>Anténní profily</h2>
                <p>Profil popisuje fyzickou konfiguraci: typ, výšky, orientaci,
                výkon, tuner a typově specifické rozměry. Změna měřicí konfigurace
                vytvoří novou revizi; historie se nepřepisuje.</p>
                <p>Zjednodušený model je geometrická reference, nikoli absolutní
                zisk. Externí NEC import zobrazuje azimutový řez solveru odděleně
                od empirických dat.</p>
                """,
            ),
            (
                "propagation",
                "Podmínky šíření",
                """
                <h2>Podmínky šíření</h2>
                <p>Obrazovka <b>Nástroje → Podmínky šíření</b> načítá po
                výslovném stisku tlačítka oficiální data NOAA SWPC: Kp, F10.7,
                číslo slunečních skvrn, rychlost slunečního větru, IMF Bt/Bz a
                stupnice R/S/G. Doplňují je snímky D-RAP, aurorálního oválu a
                Slunce v pásmu GOES SUVI 195 Å.</p>
                <p>Stažená data zůstávají v lokální cache. Aplikace rozlišuje
                aktuální, zastaralý, částečný a offline stav. Snapshot lze uložit
                k vybrané kampani; obsahuje normalizované hodnoty, UTC časy,
                použité původní řádky NOAA JSON a jejich SHA-256.</p>
                <p>Tyto údaje jsou kontext měření, nikoli předpověď konkrétní
                trasy ani automatická korekce zisku antény.</p>
                """,
            ),
            (
                "campaigns",
                "Měřicí kampaně",
                """
                <h2>Měřicí kampaně</h2>
                <p>Kampaň uzamkne značku, lokátor, pásmo, mód, profil, interval a
                cíl měření. Spoty a TX relace se přiřadí pouze při shodě konfigurace
                a času. Nastavte cíle počtu spotů, RX, sektorů a časových bloků.</p>
                <p>Deník ukládá změny sestavy, prostředí, výkonu a problémy s UTC
                časem. Přílohy jsou spravované kopie s SHA-256, nikoli odkazy na
                původní soubory.</p>
                """,
            ),
            (
                "experiments",
                "A/B experimenty",
                """
                <h2>A/B experimenty</h2>
                <p>Řízený protokol střídá dva profily až po potvrzení fyzického
                přepnutí. Porovnání páruje nejbližší reporty stejného RX a každý
                přijímač má ve výsledku stejnou váhu.</p>
                <p>Dodržte stejné pásmo, výkon, vzdálenostní vrstvu a střídání v
                čase. Bootstrap interval popisuje výběrovou nejistotu, ale sám
                nedokazuje příčinu.</p>
                """,
            ),
            (
                "coverage",
                "Pokrytí a plánování",
                """
                <h2>Pokrytí a další okno</h2>
                <p>Pokrytí hodnotí počet spotů, různých RX, 30minutových bloků a
                šířku intervalu v každém směru. Matice azimut × vzdálenost ×
                den/noc odhalí jednostranné vzorkování.</p>
                <p>Plánovač doporučí další UTC okno podle skutečné historie RX a
                chybějících buněk. Nejde o předpověď ionosféry.</p>
                """,
            ),
            (
                "hardware",
                "Hamlib a rotátor",
                """
                <h2>Rádio a rotátor</h2>
                <p><code>rigctld</code> poskytuje read-only frekvenci, mód a PTT.
                <code>rotctld</code> poskytuje skutečný azimut/elevaci. Aplikace
                upozorní na odchylku osy profilu a pohyb během TX a uloží je ke
                kvalitě relace.</p>
                <p>Aplikace v současném bezpečném režimu neposílá povely rádiu,
                rotátoru ani WSJT-X.</p>
                """,
            ),
            (
                "settings",
                "Nastavení a externí nástroje",
                """
                <h2>Nastavení</h2>
                <p>Komunikace obsahuje adresy a porty MQTT/WSJT-X/Hamlib/rotátoru.
                Průvodce externími nástroji nabízí ověřené oficiální
                instalátory a vždy vyžaduje samostatný souhlas se stažením i
                spuštěním. U Hamlibu načte názvy podporovaných rádií a umí po
                stisku tlačítka spustit nakonfigurovaný <code>rigctld</code>.</p>
                <p>Aktualizace jsou opt-in, používají HTTPS manifest a povinný
                SHA-256. Uživatelská data leží mimo instalační adresář.</p>
                """,
            ),
            (
                "data_safety",
                "Databáze a diagnostika",
                """
                <h2>Bezpečnost dat</h2>
                <p>Před migrací schématu vznikne ověřená SQLite záloha; při
                poškození zdroje, kopie nebo při novější verzi schématu se migrace
                zastaví. Uchovává se pět posledních kopií.</p>
                <p>Diagnostický JSON se vytváří lokálně až po potvrzení. Obsahuje
                konfiguraci, stavy spojení a integritu databáze, nikoli jednotlivé
                spoty, zprávy nebo hesla.</p>
                """,
            ),
            (
                "interpretation",
                "Správná interpretace",
                """
                <h2>Co lze z výsledku vyvozovat</h2>
                <p>Výsledek je empirický profil dosahu dané sestavy, času, pásma,
                módu, výkonu, přijímací sítě a propagace. Nejlépe slouží k
                opakovanému porovnávání řízených konfigurací.</p>
                <p>Samotný spot neurčuje absolutní zisk, elevační diagram ani
                účinnost antény. Nemíchejte pásma, módy, výrazně odlišný výkon,
                ADIF QSO a pasivní reporty bez kontroly zdroje. Silný závěr
                vyžaduje úhlovou, časovou a přijímačovou diverzitu.</p>
                """,
            ),
        ],
    },
    "ENG": {
        "title": "Antenna Pattern Lab help",
        "close": "Close",
        "sections": [
            ("quick", "Getting started", "<h2>Getting started</h2><ol><li>Enter your callsign and TX grid.</li><li>Select band, mode and an immutable antenna-profile revision.</li><li>Use <b>Help → Add demo data</b> to verify the interface.</li><li>For real measurements, run WSJT-X and start PSK Reporter collection.</li><li>Store longer measurements as named campaigns.</li></ol><p>The primary purpose is empirical antenna-pattern modelling, not merely monitoring FT8 traffic.</p>"),
            ("sources", "Data sources and import", "<h2>Data sources</h2><p><b>Live collection</b> receives new MQTT reports. <b>History</b> loads 1–24 hours through the rate-limited HTTP service. <b>CSV</b> transfers complete Antenna Pattern Lab spot rows. <b>ADIF</b> imports completed WSJT-X QSOs; RST_RCVD is the report the remote station sent about your signal. ADIF is a selected QSO sample, not a passive-detection substitute, so sources can be filtered separately.</p><p><b>Clear spots</b> removes spot and TX-session observations after confirmation but preserves campaign definitions, profiles and logs.</p>"),
            ("wsjtx", "WSJT-X and TX sessions", "<h2>WSJT-X UDP</h2><p>Configure the UDP server and port shown under Settings → Communications. RX/TX is confirmed only after a valid Heartbeat/Status packet. Multicast and forwarding allow concurrent use with JTAlert or GridTracker.</p><p>Each transmission stores frequency, mode, message, antenna profile, rig and rotator state. Later reports are matched by time, callsign, mode and frequency.</p>"),
            ("graphs", "Charts and filters", "<h2>Charts and filters</h2><p>Time, distance, day/night, band, mode and data source define the chart and table input. Narrow sectors add detail but reduce support.</p><ul><li><b>Directional</b>: median SNR with a finite, gap-preserving outline.</li><li><b>Time balanced</b>: equal weight per 30-minute block.</li><li><b>Detrended</b>: removes slow common drift.</li><li><b>Receiver balanced</b>: one stability-weighted vote per RX and sector.</li><li><b>Stable control</b>: removes a common trend only with enough stable RX in diverse directions.</li><li><b>Count, reach, time, map and exposure</b>: coverage and detection context.</li></ul><p>The ⓘ icon explains the active view. Click a data item to pin its tooltip; the same data is in the accessible table.</p>"),
            ("map", "Spot map", "<h2>Spot map</h2><p>The separate map inherits the main-window filters. Hover over an RX to display the great-circle route, bearing, distance, median SNR, report count and last time. Its world extent is fixed and the navigation toolbar is intentionally omitted.</p>"),
            ("profiles", "Antenna profiles and model", "<h2>Antenna profiles</h2><p>A profile records type, dimensions, orientation, power, tuner and notes. A physical change creates a new revision instead of rewriting history.</p><p>The simplified model is a geometric reference, not absolute gain. External NEC output remains separate from empirical observations.</p>"),
            ("propagation", "Propagation conditions", "<h2>Propagation conditions</h2><p><b>Tools → Propagation conditions</b> downloads official NOAA SWPC data only after an explicit button press: Kp, F10.7, sunspot number, solar-wind speed, IMF Bt/Bz and R/S/G scales. D-RAP, auroral-oval and GOES SUVI 195 Å solar images provide visual context.</p><p>Downloaded products remain in a local cache with current, stale, partial and offline states. A snapshot can be saved to a campaign with normalized values, UTC timestamps, the canonical NOAA JSON source rows used, and their SHA-256.</p><p>These indicators are measurement context—not a path forecast or an automatic antenna-gain correction.</p>"),
            ("campaigns", "Measurement campaigns", "<h2>Measurement campaigns</h2><p>A campaign fixes callsign, grid, band, mode, profile, interval and objective. Spots and TX sessions are assigned only when time and configuration match. Set targets for spots, RX, sectors and time blocks.</p><p>The UTC log records setup and environment changes. Attachments are managed SHA-256-verified copies.</p>"),
            ("experiments", "A/B experiments", "<h2>A/B experiments</h2><p>The guided protocol changes profiles only after physical-switch confirmation. Comparison pairs nearby reports from the same RX and gives each receiver equal result weight.</p><p>Keep band, power and distance layer comparable and alternate profiles in time. A bootstrap interval describes sampling uncertainty but does not prove causality.</p>"),
            ("coverage", "Coverage and planning", "<h2>Coverage and planning</h2><p>Coverage combines report, RX, time-block and interval support. The bearing × distance × day/night matrix reveals one-sided samples. The next-window planner uses observed RX availability and missing cells; it is not an ionospheric forecast.</p>"),
            ("hardware", "Hamlib and rotator", "<h2>Rig and rotator</h2><p><code>rigctld</code> supplies read-only frequency, mode and PTT. <code>rotctld</code> supplies actual position. Movement and profile-axis mismatch are warned and stored with TX quality.</p><p>The current safety model sends no command to the rig, rotator or WSJT-X.</p>"),
            ("settings", "Settings and external tools", "<h2>Settings</h2><p>Communications contains MQTT/WSJT-X/Hamlib/rotator addresses and ports. The external-tool assistant offers verified official installers and requires separate download and launch consent. For Hamlib it loads the supported radio names and can start the configured <code>rigctld</code> when you press the button.</p><p>Updates are opt-in and require an HTTPS manifest plus SHA-256. User data remains outside the install directory.</p>"),
            ("data_safety", "Database and diagnostics", "<h2>Data safety</h2><p>A verified SQLite backup is created before schema migration. Corrupt, unverifiable or newer schemas stop the migration. Five backups are retained.</p><p>The local diagnostic JSON is created only after confirmation and contains configuration, connection state and database integrity—not individual spots, messages or passwords.</p>"),
            ("interpretation", "Correct interpretation", "<h2>Correct interpretation</h2><p>The result is an empirical reach profile for a particular station, time, band, mode, power, receiver network and propagation state. It is most useful for repeated controlled comparisons.</p><p>A spot alone does not establish absolute gain, elevation pattern or efficiency. Do not mix bands, modes, major power changes, ADIF QSOs and passive reports without the source filter. Strong conclusions need angular, temporal and receiver diversity.</p>"),
        ],
    },
}


class HelpDialog(QDialog):
    def __init__(self, language: str, parent=None):
        super().__init__(parent)
        self.text = HELP[language if language in HELP else "CZE"]
        self.setWindowTitle(self.text["title"])
        self.resize(940, 680)

        layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.sections = QListWidget()
        self.sections.setMinimumWidth(230)
        self.content = QTextBrowser()
        self.content.setOpenExternalLinks(True)
        splitter.addWidget(self.sections)
        splitter.addWidget(self.content)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter, 1)

        for _code, title, _html in self.text["sections"]:
            self.sections.addItem(title)
        self.sections.currentRowChanged.connect(self._show_section)
        self.sections.setCurrentRow(0)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Close).setText(
            self.text["close"]
        )
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _show_section(self, row: int) -> None:
        if 0 <= row < len(self.text["sections"]):
            self.content.setHtml(self.text["sections"][row][2])
