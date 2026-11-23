# Acond Heat Pump — Home Assistant integrace

[![Open your Home Assistant instance and open a repository in the Marketplace.](https://my.home-assistant.io/badges/marketplace_repository.svg)](https://my.home-assistant.io/redirect/marketplace_repository/?owner=wojtech-kovac08&repository=ha-acond&category=integration)
[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=acond)
![verze](https://img.shields.io/badge/verze-0.6.0-blue)
![HA](https://img.shields.io/badge/Home%20Assistant-2024.2%2B-41BDF5)
![read only](https://img.shields.io/badge/režim-read--only-success)
![licence](https://img.shields.io/badge/licence-MIT-lightgrey)

Nevýhradní (unofficial) integrace pro tepelná čerpadla **Acond** komunikující přes **Modbus TCP**.
Čte teploty, stavy a diagnostiku dvou topných okruhů a vystavuje je jako `climate`, `sensor`
a `binary_sensor` entity — **do jednotky se nikdy nezapisuje**.

---

## Obsah

- [Rychlý start](#rychlý-start)
- [Entity](#entity)
- [Jak to funguje](#jak-to-funguje)
- [Instalace](#instalace)
- [Konfigurace](#konfigurace)
- [Mapa registrů](#mapa-registrů)
- [Řešení problémů](#řešení-problémů)
- [Omezení](#omezení)
- [Roadmap](#roadmap)

---

## Rychlý start

1. Klikni na tlačítko **Marketplace** výše — přidá repo do tvého Marketplace/HACS a otevře ho
2. Nainstaluj **Acond Heat Pump** a restartuj Home Assistant
3. **Nastavení → Zařízení a služby → Přidat integraci → Acond Heat Pump**
4. Zadej IP adresu jednotky, port `502`, Modbus ID `1`

Nebo klikni na tlačítko **„Open … in My Home Assistant"** nahoře.

---

## Entity

Všechno je **read only**. Počet entit závisí na zapnutých volbách (viz [Konfigurace](#konfigurace)).

### Climate

| Entita | Aktuální teplota | Žádaná teplota |
|---|---|---|
| `climate.acond_hp_topny_okruh_1` | 30002 | 30001 |
| `climate.acond_hp_topny_okruh_2` | 30004 | 30003 |

Climate jen zobrazuje — nepodporuje `TARGET_TEMPERATURE`, takže v kartě není posuvník.
Jde o záměr: integrace nic nenastavuje.

Pro **Bubble Card**:

```yaml
type: custom:bubble-card
card_type: climate
entity: climate.acond_hp_topny_okruh_1
```

### Senzory (základ — vždy)

| Entita | Registr | Jednotka |
|---|---|---|
| `sensor.acond_hp_zadana_teplota_okruh_1` | 30001 | °C |
| `sensor.acond_hp_aktualni_teplota_okruh_1` | 30002 | °C |
| `sensor.acond_hp_zadana_teplota_okruh_2` | 30003 | °C |
| `sensor.acond_hp_aktualni_teplota_okruh_2` | 30004 | °C |
| `sensor.acond_hp_zadana_teplota_tuv` | 30005 | °C |
| `sensor.acond_hp_teplota_tuv` | 30006 | °C |
| `sensor.acond_hp_stav_cerpadla_30007` | 30007 | – |
| `sensor.acond_hp_vratna_voda` | 30009 | °C |
| `sensor.acond_hp_venkovni_teplota` | 30010 | °C |
| `sensor.acond_hp_rezim_cerpadla` | 30014 | – |
| `sensor.acond_hp_typ_regulace` | 30015 | – |
| `sensor.acond_hp_vystupni_voda` | 30018 | °C |
| `sensor.acond_hp_porucha` | 30021 | – |

### Senzory (volitelné — `enable_energy`)

| Entita | Registr | Jednotka |
|---|---|---|
| `sensor.acond_hp_cop` | 30029 | – |
| `sensor.acond_hp_scop` | 30041 | – |
| `sensor.acond_hp_vytapeni_energie` | 30035 (DINT) | kWh |
| `sensor.acond_hp_vytapeni_elektrina` | 30037 (DINT) | kWh |
| `sensor.acond_hp_chlazeni_energie` | 30069 (DINT) | kWh |
| `sensor.acond_hp_chlazeni_elektrina` | 30071 (DINT) | kWh |

Energetické senzory mají `device_class: energy`, kWh a `total_increasing`, takže je lze přidat
do **Nastavení → Dashboardy → Energie**.

### Senzory (volitelné — `enable_silent`)

| Entita | Registr | Jednotka |
|---|---|---|
| `sensor.acond_hp_tichy_rezim_od` | 30033 | min |
| `sensor.acond_hp_tichy_rezim_do` | 30034 | min |

Hodnota jsou minuty od půlnoci, atribut `time` je ve tvaru `06:30`.

### Binární senzory — 16 bitů stavového slova 30007

`hp_on`, `hp_operation`, `hp_failure`, `dhw_heating`, `circulation_1`, `circulation_2`,
`solar_circulation`, `pool_circulation`, `defrosting`, `electric_heater`, `summer_mode`,
`brine_circulation`, `cooling`, `sg_ready_1`, `sg_ready_2`, `sg_ready_modbus`

Stejné bity najdeš i jako atributy u `sensor.acond_hp_stav_cerpadla_30007` (a celé slovo
jako `bits` v binárním tvaru).

### Speciální stavy

| Entita | Stav | Atributy |
|---|---|---|
| `sensor.acond_hp_porucha` | kód poruchy (`OK`, `A01`, `W07`, …) | `code`, `description` |
| `sensor.acond_hp_rezim_cerpadla` | Automatika / Jen čerpadlo / Jen záložní topení / Vypnuto / Ruční režim / Chlazení | `raw` |
| `sensor.acond_hp_typ_regulace` | AcondTherm / Equiterm / Ručně | `raw` |
| `sensor.acond_hp_tichy_rezim_od/_do` | minuty | `time` (`06:30`) |

---

## Jak to funguje

```
Home Assistant
   │  poll každých 30 s (volitelně 5–3600 s)
   ▼
AcondCoordinator ──► AcondModbusClient ──► TCP :502, unit id 1
   │                    (jen FC4 = read input registers)
   ▼
decoding INT ×10 / DINT (32 bit, high word first)
   │
   ├─► sensor / binary_sensor entity (21 nebo 13 hodnot)
   └─► climate entity (2 okruhy)
```

**Čtení po malých blocích.** Registrová mapa se nečte jedním dotazem, ale jedenácti malými bloky
(max. 4 registry). Důvod: jednotka, která nemá implementované všechny adresy v dlouhém rozsahu,
by odmítla celý dotaz. Takhle spadne jen ten jeden blok.

| Blok | Registry | Obsah |
|---|---|---|
| 1 | 30001–30004 | teploty okruhů |
| 2 | 30005–30008 | TUV + stavové slovo 30007 |
| 3 | 30009–30010 | vratná voda, venkovní teplota |
| 4 | 30018 | výstupní voda |
| 5 | 30021 | kód poruchy |
| 6 | 30029 | COP *(volitelné)* |
| 7 | 30035–30038 | energie vytápění *(volitelné)* |
| 8 | 30041 | SCOP *(volitelné)* |
| 9 | 30069–30072 | energie chlazení *(volitelné)* |
| 10 | 30014–30015 | režim čerpadla, typ regulace |
| 11 | 30033–30034 | tichý režim *(volitelné)* |

**Ošetření chyb.**

- Blok, který jednotka odmítne (Modbus exception), se po **třech pokusech** přestane čítat
  a do logu se zapíše `Heat pump does not implement registers 300xx-300yy`.
  Ostatní bloky fungují dál.
- Když spadne TCP spojení, integrace se mezi bloky **jednou reconnectne**.
- Když jednotka neodpoví vůbec, entity zšednou (`unavailable`) a zkusí to znovu v dalším cyklu.

**Dekódování.**

| Typ | Význam | Příklad |
|---|---|---|
| `INT ×10` | teploty, COP | 228 → 22,8 °C, 45 → 4,5 |
| `DINT` | 32bitové energie | 2 registry, **high word první** |
| `WORD` | bitová maska | 33 = bit 0 + bit 5 |

**Žádný zápis.** Transport umí jen `connect`, `read_input_registers` a `close`.
V kódu není ani jedno `write_register` / `write_coils` — hlídá to i validační skript.

---

## Instalace

### Marketplace / HACS (doporučeno)

Nejjednodušší je tlačítko **„Open … in the Marketplace"** nahoře — otevře repo přímo
v Marketplace tvé instance a nabídne jeho přidání jako custom repository.

Ručně:

1. **Marketplace** (v HA 2026.11+, dříve **HACS**) → **⋮ → Custom repositories**
2. URL `https://github.com/wojtech-kovac08/ha-acond`, kategorie **Integration**
3. Nainstalovat **Acond Heat Pump** → restart HA
4. Přidat integraci

Marketplace i HACS čtou stejný katalog, takže funguje obojí.

### Ručně

Zkopíruj `custom_components/acond` do `config/custom_components/acond` a restartuj HA.

### Požadavky

- Home Assistant **2024.2+**
- Acond s **aktivovaným Modbus TCP** (aktivuje servis; v jednotce musí být ModbusTCP zaškrtnuté
  v tmavě modrém pruhu na hlavní stránce)
- IP adresa jednotky, port **502**, Modbus ID **1** (ID 2 je obsazené pro kaskádu)

---

## Konfigurace

| Parametr | Výchozí | Význam |
|---|---|---|
| `host` | – | IP adresa jednotky |
| `port` | 502 | TCP port Modbus |
| `slave` | 1 | Modbus ID (2 = kaskáda, nepoužívat) |
| `scan_interval` | 30 s | interval čtení (5–3600) |
| `enable_circuit_2` | zapnuto | druhý topný okruh |
| `enable_energy` | **vypnuto** | COP, SCOP, energie |
| `enable_silent` | **vypnuto** | tichý režim |

Všechno jde kdykoli změnit přes **Nastavení → Zařízení a služby → Acond HP → Konfigurovat**.
Vypnuté volby znamenají, že se dané registry vůbec nečtou a entity nevzniknou.

Počet entit podle voleb:

| energie | tichý režim | bloků | senzorů |
|---|---|---|---|
| ✗ | ✗ | 6 | 13 |
| ✗ | ✓ | 7 | 15 |
| ✓ | ✗ | 10 | 19 |
| ✓ | ✓ | 11 | 21 |

*(plus vždy 16 binárních senzorů a 2 climate)*

---

## Mapa registrů

Kompletní přehled použitých adres (podrobná dokumentace výrobce je `AC781180_52_v4.3.3.25`).

| Registr | Název | Typ | Význam |
|---|---|---|---|
| 30001–30004 | T_set/act_indoor1/2 | INT ×10 | žádaná / skutečná teplota okruhů |
| 30005–30006 | T_set/act_TUV | INT ×10 | TUV |
| 30007 | TC_status | WORD | stavové slovo (16 bitů) |
| 30009 | T_act_water_back | INT ×10 | vratná voda |
| 30010 | T_act_air | INT ×10 | venkovní teplota |
| 30014 | rezim_pan | INT | režim čerpadla |
| 30015 | typ_reg_pan | INT | typ regulace |
| 30018 | T_act_water_outlet | INT ×10 | výstupní voda |
| 30021 | err_number | INT | kód poruchy |
| 30029 | COP | INT ×10 | aktuální COP |
| 30033–30034 | silent_mode_start/stop | INT | tichý režim |
| 30035 / 30037 | TES / EES | DINT ×10 | energie vytápění (kWh) |
| 30041 | SCOP | INT ×10 | sezónní COP |
| 30069 / 30071 | Cooling/ECE | DINT ×10 | energie chlazení (kWh) |

**Neimplementované registry.** Některé jednotky (včetně testované) vrací „illegal data address"
na všechno nad ~30028. Tam pak zůstanou volitelné hodnoty nedostupné — není to chyba integrace.

Chceš-li zjistit, co tvoje jednotka opravdu má, spusť diagnostiku:

```bash
pip install pymodbus
python tools/probe_acond.py 192.168.0.11
```

Skript projde adresy 30001–30079 (jen čtení) a vypíše, které odpovídají.

---

## Řešení problémů

| Problém | Příčina / řešení |
|---|---|
| `Invalid handler specified` | neúplná kopie souborů — zkopíruj celou složku `custom_components/acond` a restartuj |
| „nepodařilo se otevřít TCP spojení" | jednotka na dané IP/portu neposlouchá (síť, firewall, offline) |
| „jednotka neodpovídá na Modbus dotazy" | TCP jde, ale jednotka mlčí → ModbusTCP není zaškrtnuté/aktivované, nebo špatné ID |
| „odmítla požadavek Modbus" | exception response; v logu je vidět které registry |
| hodnota `Neznámý` u COP/SCOP/energií | jednotka ty registry nemá → nech `enable_energy` vypnuté |
| hodnota `Neznámý` u tichého režimu | jednotka nemá 30033/30034 → nech `enable_silent` vypnuté |
| entity `Nedostupné` po uložení nastavení | normální — reload integrace, další cyklus se srovná |
| české popisky chybí (syrové `enable_energy`) | nezkopírovaný `translations/cs.json`, po restartu HA se načte |

Log v HA filtruj na `acond` — jsou tam konkrétní chyby i rozsahy registrů.

---

## Omezení

- Integrace je **read only** — žádný zápis, žádné změny nastavení jednotky.
- Teplota se nastavuje na jednotce nebo v jejím webovém rozhraní.
- `climate` hlásí vždy `heat` (režim okruhu se z těchto registrů nedá zjistit).
- Jen **jeden master** může jednotku číst současně.

---

## Roadmap

- [x] Teploty 2 okruhů + `climate` (read only)
- [x] TUV, venkovní, vratná a výstupní voda
- [x] Energie, COP, SCOP (volitelně)
- [x] Binární senzory ze stavového slova 30007
- [x] Kód poruchy s textem
- [x] Režim čerpadla a typ regulace
- [x] Tichý režim (volitelně)
- [ ] Diagnostika driveru (30023) jako samostatný sensor
- [ ] `diagnostics.py` pro snadné reporty
- [x] GitHub Actions (hassfest + HACS validation)
- [ ] Zařazení do katalogu Marketplace

---

## Zařazení do katalogu Marketplace

Aby se integrace objevila v katalogu (a nemusela se přidávat ručně odkazem), musí projít revizí
v [hacs/default](https://github.com/hacs/default). Co k tomu repo potřebuje:

- [x] `manifest.json` s `domain`, `name`, `version`, `documentation`, `issue_tracker`, `codeowners`
- [x] `hacs.json` s `name`
- [x] `README.md`
- [x] brand ikona — `custom_components/acond/brand/icon.png`
- [x] GitHub Actions: **hassfest** a **HACS validation** (`.github/workflows/validate.yml`)
- [ ] **vydaný GitHub release** (samotný tag nestačí)
- [ ] popis repa, topics a zapnuté issues na GitHubu
- [ ] PR do `hacs/default` → soubor `integration`, abecedně

Revize nových repozitářů trvá měsíce. Do té doby funguje přidání přes odkaz výše.

---

## Licence

MIT — viz [LICENSE](LICENSE).

Projekt není nijak spojený s výrobcem. Vychází z dokumentace „Protocol – Modbus TCP/RTU"
(`AC781180_52_v4.3.3.25`, resp. `AC781150_52_v4.3.3.25`). Použití na vlastní riziko.
