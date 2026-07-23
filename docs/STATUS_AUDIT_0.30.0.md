# Stavový audit Antenna Pattern Lab 0.30.0

Datum auditu: 2026-07-23

## Závěr

Aplikace je funkčně ucelený lokální nástroj pro plánování, sběr, třídění a
analýzu empirických směrových dat antén. Není to laboratorní měřicí přístroj:
výsledek zůstává observačním odhadem ovlivněným propagací, sítí přijímačů,
časem, výkonem a úplností metadat.

Verze 0.30.0 uzavírá milníky 1–8 s výjimkou dvou externích provozních kroků:
reálného ověření živého řetězce na stanici OK7PS a veřejného podepsaného
release kanálu. Milníky 9–13 jsou záměrně otevřené.

## Ověřitelné důkazy

- 113 automatických testů v 36 testovacích souborech prošlo.
- PyInstaller x86-64 sestava a Inno Setup instalátor byly vytvořeny bez chyby.
- Instalační EXE i přenosný ZIP mají vypočtený SHA-256.
- Roadmapa obsahuje 91 dokončených a 28 otevřených položek.
- Aplikační EXE i instalátor jsou podle Windows `NotSigned`.
- Ve workspace není publikovaný `release-manifest.json`; aktualizační
  mechanismus je implementovaný, ale release kanál není zprovozněný.
- PyInstaller hlásí především volitelné nebo platformně cizí moduly
  (`posix`, `pwd`, `tornado`, proxy doplňky MQTT). Build byl dokončen, ale
  tento seznam nenahrazuje spuštění na čistém cílovém PC.

## Stav funkčních oblastí

### Sběr a vstup dat — implementováno, čeká polní ověření

- MQTT PSK Reporter pro FT8 a WSPR, indikátor skutečného spojení.
- HTTP historie do 24 hodin, deduplikace překryvu live/history.
- CSV import/export a reprodukovatelná demo data.
- Maidenhead, vzdálenost, azimut a lokální sluneční čas.

Hlavní zbývající důkaz: několik reálných TX relací OK7PS se souběžným
MQTT, WSJT-X a případně Hamlib záznamem.

### WSJT-X a původ TX — implementováno

- UDP Heartbeat/Status/Close, multicast a validovaný forwarding.
- Evidence začátku a konce TX relace, frekvence, módu, zprávy a profilu.
- Časové přiřazení spotů k TX relaci a kampani.
- Read-only CAT snímek z `rigctld`: frekvence, mód, PTT, volitelně RFPOWER
  a SWR.

### Databáze a reprodukovatelnost — silný základ, chybí provozní ochrana

- SQLite persistence, deduplikace a nedestruktivní rozšiřování schématu.
- Neměnné revize anténních profilů.
- Kampaně, cíle, deník a přílohy s SHA-256.
- Reset spotů neodstraňuje definice kampaní ani profilů.

Nejvyšší riziko: před migrací zatím nevzniká automatická záloha a aplikace
nemá uživatelské obnovení databáze.

### Statistika a diagramy — pokročilé, stále observační

- Robustní sektorové mediány, bootstrap intervaly a datová kvalita.
- Vyvážení 30minutových bloků a odečtení pomalého společného trendu.
- Omezená kruhová interpolace v lineárním výkonu bez umělých bodových nul.
- Vzdálenost, den/noc, RX expozice a přístupné tabulkové varianty.
- A/B párování se stejnou vahou každého přijímače.

Největší metodická mezera: chybí dlouhodobá kalibrace RX, kontrolní skupina
stabilních přijímačů, metadata kosmického počasí a citlivostní analýza.

### Mapy a vizualizace — implementováno

- Polární diagramy, časové grafy, kvalita a interaktivní tooltipy.
- Velká offline mapa světa s agregací RX a trasou po velké kružnici.
- Azimut, vzdálenost, SNR a poslední zachycení při najetí.
- CZE/ENG a tabulkové alternativy důležitých grafů.

### Modely antén a NEC — vhodné jako reference

- Typové profily Vertical, EFHW, EFRW, Dipól, Inverted-V a Yagi.
- Parametrické relativní modely a import externího NEC azimutového řezu.
- Empirické reziduum proti modelu.

Omezení: bez profilu terénu, přesné země, elevace a ionosféry nelze model
interpretovat jako absolutní předpověď zisku.

### Kampaně a plánování — implementováno

- Minimální cíle spotů, RX, podložených sektorů a časových bloků.
- Úhlová úplnost a matice azimut × vzdálenost × den/noc.
- Porovnání dvou kampaní podle času, vzdáleností a překryvu RX sítě.
- Doporučení dalšího místního slunečního okna, převod na UTC, délka,
  cílové směry a datová jistota.

### Rotátor a směrový hardware — read-only milník dokončen

- Samostatné read-only připojení k `rotctld`.
- Počáteční/koncový azimut a elevace a maximální odchylka každé TX relace.
- Porovnání osy profilu, skutečné polohy a podloženého empirického maxima.
- Oranžové předletové varování při odchylce nad 5°.
- Červené živé varování při pohybu nad 3° nebo nesouladu během TX.
- Pohyb se trvale promítne do kvality relace.

Aplikace rotátor neovládá. To je správné bezpečnostní omezení současné verze.

### Instalace a aktualizace — lokálně funkční, veřejně nedokončené

- x86-64 instalátor, upgrade se stejným AppId, odinstalace.
- Opt-in stažení Hamlib/WSJT-X pouze z povolených oficiálních zdrojů.
- Kontrola názvu, velikosti a SHA-256 a samostatné potvrzení spuštění.
- Aktualizační klient s HTTPS manifestem a kontrolním součtem.

Blokující kroky pro veřejné vydání: Authenticode certifikát, podpis,
hostovaný manifest, archiv verzí a ověření upgradu/rollbacku na čistém PC.

## Doporučené pořadí dalšího vývoje

1. **Polní validační protokol:** skutečný FT8 test OK7PS, uložená diagnostika,
   porovnání časů MQTT/WSJT-X/Hamlib a ruční kontrola několika spotů.
2. **Ochrana dat:** automatická záloha před každou migrací, kontrola integrity
   a uživatelské obnovení.
3. **Omezení zkreslení:** kalibrace RX, kontrolní skupina a leave-one-out
   citlivost přijímačů, časů a směrů.
4. **Provenance a report:** HTML/PDF protokol a přenosný balíček kampaně
   s verzí algoritmu, schématu a kontrolními součty.
5. **Validace modelu:** časová křížová validace, stabilita hlavního směru,
   NEC rezidua a až potom terén/horizont.
6. **Asistovaná automatizace:** plán měření; případné řízení rotátoru až po
   readbacku, softwarových limitech, TX interlocku a neměnném auditu.

## Doporučení k použití současné verze

Verze 0.30.0 je vhodná pro lokální experimentování a sběr reprodukovatelných
kampaní. Pro rozhodnutí o konstrukční změně antény je vhodné požadovat více
časových bloků, více nezávislých RX, opakovanou kampaň a shodu několika
analytických pohledů. Jediné maximum SNR nebo jeden dobrý večer není dostatečný
důkaz změny vyzařovacího diagramu.
