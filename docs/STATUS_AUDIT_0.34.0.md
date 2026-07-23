# Stav aplikace Antenna Pattern Lab 0.34.0

Datum auditu: 23. 7. 2026

## Výsledek

Verze 0.34.0 uzavírá plánovaný základ ucelené Windows x86-64 aplikace pro modelování empirických vyzařovacích diagramů antén z reálného provozu. Nejde jen o monitor FT8: příjem reportů je vstupem pro profilování antény, řízené experimenty, kontrolu pokrytí a porovnání konfigurací.

Automatická sada obsahuje 130 testů a v okamžiku vydání všechny procházejí. Instalační a přenosný build jsou vytvořeny ze stejného zdrojového stavu.

## Hotové funkční celky

| Celek | Stav | Poznámka |
| --- | --- | --- |
| PSK Reporter | Hotovo | MQTT/TLS live stav, HTTP historie do 24 h, deduplikace a potvrzený stav spojení |
| WSJT-X | Hotovo | UDP Heartbeat/RX/TX, TX relace, multicast a forwarding |
| Import/export | Hotovo | CSV a standardní ADIF/ADI; CSV export respektuje aktivní filtry |
| Původ dat | Hotovo | `pskreporter` a `adif` se ukládají a filtrují samostatně |
| Databáze | Hotovo | SQLite schéma 2, migrace se zálohou, integrita, flush spotů |
| Anténní profily | Hotovo | Vertical, EFHW, EFRW, Dipól, Inverted-V, Yagi a obecný typ; neměnné revize |
| Grafy | Hotovo | Empirický obrys, časové/RX normalizace, nejistota, dosah, mapa RX, expozice, model a NEC |
| Mapa spotů | Hotovo | Samostatné velké okno, offline svět, trasy po velké kružnici, hover detail; pevný rozsah bez toolbaru |
| Experimenty | Hotovo | A/B párování, řízené střídání, kampaně, cíle, deník, přílohy a plánovač pokrytí |
| Hardware | Hotovo | Read-only `rigctld` a `rotctld`, evidence stavu a kontrola odchylek |
| UX a nápověda | Hotovo | CZE/ENG, kompaktní hlavní plocha, strukturovaná nápověda, grafické tooltipy a aplikační ikona |
| Instalace | Hotovo | Inno Setup, upgrade přes stálé AppId, detekce nástrojů, ověřené nabídnutí Hamlibu/WSJT-X |
| Aktualizace | Jádro hotovo | Validovaný HTTPS manifest a SHA-256; veřejný release kanál zatím není publikován |

## ADIF: správný význam a omezení

ADIF import není náhradou MQTT. U WSJT-X dokončeného QSO se `RST_RCVD` použije jako report protistanice o našem vysílaném signálu. ADIF však typicky obsahuje pouze vybraná dokončená spojení, zatímco PSK Reporter reprezentuje širší pasivní síť zachycení. Aplikace proto zdroj ukládá do každého spotu a nabízí samostatný filtr; výchozí kombinovaný pohled je nutné interpretovat s vědomím tohoto výběru.

## Ověření a známá omezení

- Automatické testy ověřují doménu, parsery, databázové migrace, analytiku, dialogy, menu, instalační definici a hlavní UI.
- Fyzikální výsledek stále závisí na kvalitě reálných dat, stabilitě výkonu, časovém pokrytí, přijímací síti a propagaci.
- Parametrický model není plný elektromagnetický solver; pro externí referenci lze importovat NEC výstup.
- Hamlib a WSJT-X se neinstalují tiše. Uživatel musí zvlášť schválit stažení i spuštění oficiálního instalátoru.
- Build zatím není Authenticode podepsán. To vyžaduje code-signing certifikát.
- Zbývá provést živý ověřovací scénář s OK7PS na skutečném vysílání.

## Další rozvoj

Nevyřízené návrhy jsou zachovány v `docs/ROADMAP.md`. Nejvyšší přínos mají:

1. blokový bootstrap a leave-one-out citlivost po RX a čase,
2. volitelná reprodukovatelná metadata kosmického počasí,
3. HTML/PDF protokol a přenositelný balíček kampaně,
4. záloha a obnova databáze přímo z aplikace,
5. publikovaný podepsaný release kanál,
6. terénní horizont a validace empirického profilu proti NEC po pásmech.

Pokročilé automatické řízení rotátoru zůstává záměrně pozdějším opt-in milníkem s bezpečnostními blokacemi a auditní stopou.
