# Roadmap projektu

## Produktový cíl

Vytvořit snadno spustitelnou Windows x86-64 aplikaci, která radioamatérovi pomůže měřit změny anténní sestavy pomocí FT8/WSPR reportů, transparentně ukazuje nejistotu a navrhuje další kontrolovaný experiment.

## Milník 1 — měřitelný základ (MVP 0.1)

- [x] lokální desktopová aplikace bez serveru,
- [x] PSK Reporter MQTT adaptér pro vlastní FT8 spoty,
- [x] potvrzený indikátor MQTT spojení a CZE/ENG rozhraní,
- [x] bezpečný reset databáze a přepnutí značky/pásma za běhu,
- [x] SQLite persistence a deduplikace,
- [x] Maidenhead, vzdálenost a azimut,
- [x] hrubý sektorový profil, tabulka, CSV a demo,
- [x] automatické testy a PyInstaller build,
- [x] export diagnostického JSON pro reprodukovatelné ověření celého živého řetězce,
- [ ] ověřit živý sběr s OK7PS na reálném vysílání,
- [x] HTTP import poslední historie PSK Reporteru (max. 24 hodin, rate limit),
- [x] instalační balíček a bezpečné opt-in aktualizační jádro,
- [ ] důvěryhodný Authenticode podpis a zveřejněný release kanál.

## Milník 2 — znát podmínky vysílání

- [x] posluchač WSJT-X UDP protokolu: frekvence, mód, TX stav a čas slotu,
- [x] barevný WSJT-X stav Čekám/RX/TX/Bez dat/Chyba,
- [x] evidence TX relací a párování následných PSK spotů podle času/frekvence,
- [x] multicast a validované UDP forwarding cíle pro souběh s JTAlert/GridTracker,
- [x] profily anténních konfigurací (typ, výšky, orientace, poznámky),
- [x] typové šablony Vertical/EFHW/EFRW/Dipól/Inverted-V/Yagi/Ostatní,
- [x] typově správný význam orientace a referenční osy v polárním grafu,
- [x] ruční evidence výkonu a stavu tuneru v profilu,
- [x] volitelný read-only Hamlib/rigctld monitor frekvence, módu a PTT,
- [x] detekce Hamlibu a průvodce modelem rádia/COM portem/baud rate včetně řízeného spuštění `rigctld`,
- [x] automatická evidence relativního RFPOWER a volitelného SWR, pokud ji rádio/backend přes Hamlib poskytuje,
- [x] přiřazení spotů ke konkrétní TX relaci a konfiguraci,
- [x] časová osa experimentu a kontrola kvality přiřazení TX relací.

## Milník 3 — korektnější statistika

- [x] omezený field-stream sběr aktivity známých přijímačů na stejném pásmu a v 5minutových oknech,
- [x] expozice: pozitivní detekce i doložené nezachycení proti skutečným WSJT-X TX relacím,
- [x] interaktivní rozdělení podle vzdálenosti,
- [x] rozdělení den/noc podle přibližného místního slunečního času TX,
- [x] robustní A/B normalizace se stejnou vahou každého RX,
- [x] vyvážení širších časových podmínek stejnou vahou 30minutových oken,
- [x] robustní odečtení pozvolného společného trendu propagace nad rámec blokového vyvážení,
- [x] viditelná popisná kvalita každého sektoru podle počtu reportů a unikátních RX,
- [x] bootstrap intervaly výběrové nejistoty hlavního profilu,
- [x] geografická mapa přijímačů jasně oddělená od efektivního profilu,
- [x] samostatná velká offline mapa světa s agregovanými RX spoty, trasou po velké kružnici při najetí, azimutem, vzdáleností, SNR a časem posledního zachycení,
- [x] pevný celosvětový rozsah mapy bez technické navigační lišty; filtrování mapy přebírá hlavní filtry včetně zdroje dat,
- [x] samostatně označený zjednodušený fyzikální model, jasně oddělený od empirických dat a NEC.

## Průběžný UX milník — nápověda nad grafy

- [x] kompaktní dvouřádková provozní lišta; graf a data jsou dominantní obsah hlavního okna,
- [x] nativní světlá systémová paleta bez globálního stylesheetu přetékajícího do dialogů,
- [x] světlé a kontrastní provedení všech hlavních, A/B a experimentálních grafů,
- [x] přesun WSJT-X, forwarding, Hamlib a RX expozice do dialogu Nastavení → Komunikace,
- [x] aplikační menu Soubor/Data/Nástroje/Nastavení/Nápověda včetně O programu,
- [x] strukturovaná CZE/ENG nápověda ke všem logickým částem aplikace a jejich doporučenému použití,
- [x] přesun demo dat do menu Nápověda a sjednocená aplikační/instalační ikona,
- [x] kruhová výkonová interpolace empirického obrysu s konečnou úhlovou podporou bez umělých nul,
- [x] tooltip při najetí na sektor polárního grafu: rozsah azimutu, medián SNR, počet spotů, počet unikátních RX a nejdelší cesta,
- [x] tooltip vždy uvede aktivní značku, pásmo, časový rozsah a konfiguraci antény,
- [x] vizuálně odlišit sektor s dostatkem vzorků od sektoru s nízkou spolehlivostí,
- [x] u intervalů nejistoty vysvětlit střední odhad i dolní/horní mez,
- [x] informační ikona nad hlavním grafem s krátkým popisem „co graf říká“ a „co z něj nelze vyvozovat“,
- [x] jednotné CZE/ENG texty nápovědy pro polární profil, mapu, časovou osu, A/B porovnání a zjednodušený model,
- [x] CZE/ENG nápověda a přístupná tabulka pro importovaný externí NEC výstup,
- [x] možnost tooltip připnout kliknutím, aby šel údaj pohodlně opsat nebo porovnat,
- [x] přístupná varianta stejné informace přes klávesnici a tabulkový přehled.

## UX milník 0.37 — technické měřicí pracoviště

- [x] provozní hlavička oddělující kontext měření, stav sběru a jedinou dominantní akci Start/Stop,
- [x] explicitní stavy sběru zastaveno/připojování/běží/zastavování/selhání,
- [x] kompaktní metriky oddělené od stavů externích integrací,
- [x] sjednocená lišta analytických filtrů,
- [x] uživatelsky nastavitelný a perzistentní poměr graf/reporty s bezpečným resetem rozložení,
- [x] větší polární graf se sémantickými barvami a kontrolovanými okraji pro světlý i tmavý motiv,
- [x] responzivní přehled reportů s řazením, technickým formátováním, tooltipy, detailem výběru a vysvětlujícím prázdným stavem,
- [x] kompaktní 36sektorová matice kvality s textovým stavem a inspektorem vybraného sektoru,
- [x] stavový řádek omezený na PSK Reporter, WSJT-X, Hamlib, rotátor a závažná upozornění,
- [x] přístupné názvy a popisy, vazby label–control, klávesnicové pořadí a nebarevné rozlišení stavů,
- [x] vizuální ověření Classic/Monitor Light/Monitor Dark, CZE/ENG, 1180×720 až 1920×1080 a škálování 125–200 %,
- [x] sjednocení reprezentativních dialogů Vzhled, Komunikace, Profily antén a První spuštění.

### Následná práce po 0.37

- [ ] rozšířit sjednocená pravidla dialogů na kampaně, A/B porovnání, pokrytí a mapu po doplnění charakterizačních testů,
- [ ] oddělit vlastnictví Matplotlib grafu z `MainWindow` do samostatného panelu při nejbližší větší změně grafů,
- [ ] provést nativní Windows test s odečítačem obrazovky a přechodem okna mezi monitory s rozdílným DPI,
- [ ] znovu vyhodnotit přechod reportů z `QTableWidget` na modelový `QTableView` pouze tehdy, pokud měření ukáže problém s výkonem nebo údržbou.

## UX milník 0.38 — Hamlib modely a spuštění rigctld

- [x] načíst z nainstalované verze Hamlibu úplné mapování model ID → výrobce a název rádia,
- [x] nabídnout prohledávatelný výběr podporovaných rádií se zachováním dříve uloženého ID,
- [x] odstranit pasivní náhled příkazové řádky a nahradit jej akcí **Spustit rigctld**,
- [x] před spuštěním validovat model, COM port, baud rate a TCP port a zabránit zjevnému duplicitnímu startu na obsazeném portu,
- [x] zobrazit nebarevný stav spouštění, úspěchu nebo selhání; WSJT-X UDP konfiguraci ponechat beze změny.

## Milník 4 — A/B experimenty

- [x] protokol a časovač řízeného střídání konfigurací A/B s potvrzením fyzické změny,
- [x] první párování nejbližších reportů od stejného RX,
- [x] tabulka relativního rozdílu SNR a robustní medián B − A,
- [x] 45° sektorové výsledky a bootstrap intervaly výběrové nejistoty,
- [x] WSPR jako samostatně filtrovaný live/history/demo a A/B zdroj,
- [x] doporučení zbývajících párů/RX a odhad délky dalšího měření podle rychlosti sběru.

## Milník 5 — návrhy změn antény

- [x] cíle experimentu podle pásma, azimutu, vzdálenosti a ručně ověřovaného omezení SWR,
- [x] parametrické azimutové profily dipól/inverted-V, EFHW/EFRW, vertikál a Yagi,
- [x] volitelný backend pro import normálního azimutového výstupu externího NEC solveru bez závislosti běžného spuštění,
- [x] empirická kalibrace relativního tvaru modelu profilově přiřazenými TX/A/B daty s viditelným reziduem,
- [x] konzervativní plánovač doporučující další bezpečný a ověřitelný A/B experiment,
- [x] nikdy neuvádět přesný přínos bez odpovídající opory v datech/modelu.

## Závěrečný milník — instalace a první spuštění

- [x] Windows x86-64 instalátor s odinstalací, Start Menu a volitelným zástupcem na ploše,
- [ ] Authenticode podpis instalátoru a odinstalátoru po dodání code-signing certifikátu,
- [x] při instalaci i prvním spuštění zjistit dostupnost Hamlib/`rigctld`; pokud chybí, nabídnout pouze oficiální stabilní x64 release,
- [x] na souhrnné instalační stránce skutečně vypsat výsledek detekce Hamlibu a WSJT-X bez prázdného textového pole,
- [x] zjistit instalaci WSJT-X; pokud chybí, nabídnout oficiální stabilní x64 release,
- [x] dynamicky vybrat pouze očekávaný GitHub release asset a vyžadovat publikovaný SHA-256,
- [x] atomické stažení do uživatelské složky a samostatné potvrzení před spuštěním vendor instalátoru,
- [x] spuštění vendor instalátoru přes Windows ShellExecute/UAC místo přímého CreateProcess,
- [x] nikdy neinstalovat Hamlib ani WSJT-X tiše bez výslovného souhlasu uživatele,
- [x] průvodce prohledávatelným seznamem Hamlib rádií, COM portem, baud rate, TCP portem a řízeným spuštěním `rigctld`,
- [x] průvodce nastavením WSJT-X UDP portu a ověřením první Heartbeat zprávy,
- [x] aktualizace přes stejné AppId se zachováním databáze a uživatelských profilů mimo instalační adresář,
- [x] opt-in automatická kontrola přes validovaný HTTPS manifest a stažení s povinným SHA-256,
- [ ] zveřejnění manifestu a instalátorů v oficiálním release kanálu.

## Nejbližší ověřovací scénář

1. Spustit aplikaci s demo daty a ověřit UI/build na cílovém PC.
2. Smazat pouze demo databázi nebo použít nový profil měření.
3. Na 20 m vysílat FT8 se stabilním výkonem a jednou anténní konfigurací.
4. Ověřit příjem živých spotů, lokátory a deduplikaci.
5. Ověřit WSJT-X UDP při reálném provozu a zkontrolovat správné přiřazení spotů k TX relacím.

## Otevřená rozhodnutí

- První reálná anténa a její měnitelné parametry.
- Zda bude první priorita jednopásmový experiment na 20 m, nebo více pásem.
- Dostupnost CAT/Hamlib a měření výkonu/SWR.
- Požadavek na přenositelnost databáze mezi počítači.

## Milník 6 — měřicí kampaně a původ dat

- [x] Standardní import `.adi`/`.adif` z WSJT-X s korektní interpretací `RST_RCVD`, statistikou přeskočených záznamů a zachováním zdroje.
- [x] Databázová migrace a filtr zdroje `pskreporter`/`adif`, aby se výběrová QSO nemíchala bez upozornění s pasivními reporty.
- [x] Pojmenované měřicí kampaně s cílem, časovým intervalem, značkou, lokátorem, pásmem, módem, profilem antény a poznámkami.
- [x] Automatické přiřazení TX relací a spotů pouze ke kampani, jejímuž času a konfiguraci odpovídají.
- [x] Statistiky kampaně a otevření pokrytí aktivní i historické kampaně bez vlivu klouzavého filtru „posledních N hodin“.
- [x] Neměnné verze anténního profilu: změna výšky, orientace, délky nebo napájení založí novou variantu místo přepsání historie.
- [x] Strukturovaný deník podmínek s UTC časem a kategoriemi pro sestavu, prostředí, změnu antény, výkon, pozorování a problémy.
- [x] Volitelné přílohy kampaně: spravované kopie fotografií, exportů analyzátoru a dalších podkladů s limitem velikosti, SHA-256, deduplikací a kontrolou integrity.
- [x] Živá kontrola úplnosti metadat před zahájením srozumitelně odlišená od technické připravenosti sběru.

## Milník 7 — plánovač kvality měření

- [x] Úhlová mapa úplnosti podle počtu spotů, unikátních RX, 30minutových bloků a šířky intervalu.
- [x] Doporučení tří nejslaběji pokrytých azimutů a chybějících šestihodinových UTC oken.
- [x] Matice azimut × vzdálenost × den/noc, aby „zaplněný“ sektor nebyl tvořen pouze jedním typem spojení.
- [x] Nastavitelná minimální kritéria pro spoty, unikátní RX, podložené 30° sektory a 30minutové bloky včetně živého oznámení splnění cíle.
- [x] Porovnání dvou kampaní podle místních slunečních 30minutových oken, počtu bloků, den/noc, vzdáleností a sítě RX včetně konkrétních varování a návrhu doplnění.
- [x] Návrh dalšího vysílacího okna podle dosavadní rychlosti sběru, chybějících směrů a dostupnosti RX, včetně převodu místního slunečního času na nejbližší UTC začátek, délky měření a úrovně jistoty.

## Milník 8 — směrové antény a hardware

- [x] Read-only připojení k Hamlib `rotctld` a viditelný stav rotátoru.
- [x] Záznam počátečního a koncového azimutu/elevace rotátoru a maximální úhlové odchylky ke každé TX relaci.
- [x] Porovnání zamýšlené mechanické osy profilu, skutečného natočení a podloženého maxima empirických dat včetně kruhových odchylek, počtu podkladů a jistoty.
- [x] Živé neblokující upozornění na pohyb rotátoru nad 3° během TX a na odchylku mechanické osy od neměnného profilu nad 5°, včetně trvalého označení kvality relace.

## Milník 9 — omezení zkreslení a normalizace

- [x] Kalibrace přijímačů podle dlouhodobé stability a omezení váhy velmi aktivních reportérů: jeden hlas RX na sektor, robustní MAD proti souběžnému společnému trendu, omezená váha 0,25–1 a viditelná diagnostika bez metodicky chybného odečtení pevné směrové úrovně.
- [x] Kontrolní skupina stabilních RX pro rozlišení změny antény od společné změny propagace: nejméně 3 stabilní RX ve 3 různých 60° směrech a 3 společných blocích, centrovaný trend odchylek vůči vlastní úrovni RX a transparentní odmítnutí korekce při nedostatečných datech.
- [ ] Volitelná metadata sluneční a geomagnetické aktivity uložená reprodukovatelně s kampaní.
- [ ] Striktní oddělení výsledků podle pásma, módu, výkonu a významné změny RX sítě.
- [ ] Citlivostní analýza: jak se výsledek změní po vynechání nejsilnějšího RX, času nebo směru.

## Milník 10 — reporty a přenositelnost

- [ ] Export uceleného HTML/PDF protokolu s grafy, filtry, kvalitou pokrytí a popisem použitých dat.
- [ ] Přenosný balíček kampaně obsahující spoty, TX relace, verzi profilu, nastavení analýzy a kontrolní součty.
- [ ] Import balíčku v režimu pouze pro čtení a porovnání dvou kampaní z různých počítačů.
- [ ] Záloha a obnova databáze z aplikace včetně kontroly integrity.
- [ ] Úplná provenance výsledku: verze aplikace, algoritmu, databázového schématu a času vytvoření.

## Milník 11 — provoz a vydávání

- [x] Automatická bezpečná záloha databáze před migrací schématu: kontrola integrity zdroje i kopie, atomické dokončení, uchování pěti posledních záloh a odmítnutí migrace při chybě.
- [ ] Publikovaný aktualizační manifest, archiv starších verzí a podporovaný návrat na poslední funkční build.
- [ ] Authenticode podpis aplikace, instalátoru a odinstalátoru.
- [ ] Anonymní opt-in diagnostický balíček vytvořený lokálně a odesílaný pouze výslovným krokem uživatele.

## Milník 12 — validace modelu a prostředí stanoviště

- [ ] Reprodukovatelný profil místního horizontu a terénu s ručním importem výškových dat a jasně uvedeným zdrojem.
- [ ] Porovnání NEC reference a empirického diagramu po pásmech, vzdálenostních vrstvách a denní době včetně mapy reziduí.
- [ ] Křížová validace po časových blocích: model se vytvoří z části kampaně a ověří na dosud nepoužitých datech.
- [ ] Odhad stability hlavního směru a šířky laloku mezi kampaněmi, nikoli pouze rozdíl jednoho maxima.
- [ ] Detekce dlouhodobého driftu sestavy, například změny orientace, napájení nebo kabelu proti referenční kampani.

## Milník 13 — asistované řízení měření

- [ ] Volitelný plán kampaně složený z doporučených měřicích oken, profilů, pásem a cílových směrů.
- [ ] Bezpečné opt-in řízení rotátoru přes `rotctld` s potvrzením cíle, softwarovými limity a povinným readbackem skutečné polohy.
- [ ] Blokování pohybu rotátoru během TX a blokování zahájení TX, dokud poloha není stabilní v nastavené toleranci.
- [ ] Neměnný auditní záznam každého požadovaného směru, odpovědi hardware, potvrzení uživatele a případného selhání.
- [ ] Režim „průvodce měřením“, který vede obsluhu krok za krokem, ale nikdy samostatně nezahájí vysílání.

## Milník 14 — auditovatelná nejistota a falsifikace

- [ ] Blokový bootstrap po časových oknech a RX, který zachová korelaci opakovaných reportů místo předpokladu nezávislosti jednotlivých spotů.
- [ ] Placebo test záměnou profilů nebo časových štítků; aplikace upozorní, pokud podobně silný „efekt“ vzniká i bez skutečné změny antény.
- [ ] Automatický leave-one-out přehled po RX, časových blocích a sektorech s označením výsledku závislého na jediné části dat.
- [ ] Hierarchický experimentální model oddělující společný časový trend, stabilní rozdíly RX a směr, použitý pouze při dostatečně překrytém pokrytí.
- [ ] Neměnný recept analýzy s verzí algoritmu, parametry, vstupním hashem a možností přesně zopakovat publikovaný výsledek.

Pořadí milníků je záměrné: nejdříve se musí zachovat původ a srovnatelnost dat, poté lze spolehlivě plánovat měření, zapojit směrový hardware a teprve nad tím stavět pokročilejší normalizaci, reprodukovatelné reporty a falsifikační testy.
