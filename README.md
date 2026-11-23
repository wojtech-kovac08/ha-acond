# Acond Heat Pump – Home Assistant integration

Nevýhradní (unofficial) integrace pro tepelná čerpadla **Acond** komunikující přes **Modbus TCP**.
**Pouze čte** – do jednotky se nikdy nezapisuje.

Repo: <https://github.com/wojtech-kovac08/ha-acond>

## Entity

**Climate** – `climate.acond_hp_topny_okruh_1` a `..._okruh_2` (read only, jen zobrazení teplot)

| Vlastnost | Registr |
|---|---|
| Aktuální teplota | 30002 / 30004 |
| Žádaná teplota | 30001 / 30003 |

**Senzory**

| Entita | Registr | Jednotka |
|---|---|---|
| `sensor.acond_hp_zadana_teplota_okruh_1` | 30001 | °C |
| `sensor.acond_hp_aktualni_teplota_okruh_1` | 30002 | °C |
| `sensor.acond_hp_zadana_teplota_okruh_2` | 30003 | °C |
| `sensor.acond_hp_aktualni_teplota_okruh_2` | 30004 | °C |
| `sensor.acond_hp_zadana_teplota_tuv` | 30005 | °C |
| `sensor.acond_hp_teplota_tuv` | 30006 | °C |
| `sensor.acond_hp_vratna_voda` | 30009 | °C |
| `sensor.acond_hp_venkovni_teplota` | 30010 | °C |
| `sensor.acond_hp_vystupni_voda` | 30018 | °C |
| `sensor.acond_hp_cop` | 30029 | – |
| `sensor.acond_hp_scop` | 30041 | – |
| `sensor.acond_hp_vytapeni_energie` | 30035 (DINT) | kWh |
| `sensor.acond_hp_vytapeni_elektrina` | 30037 (DINT) | kWh |
| `sensor.acond_hp_chlazeni_energie` | 30069 (DINT) | kWh |
| `sensor.acond_hp_chlazeni_elektrina` | 30071 (DINT) | kWh |
| `sensor.acond_hp_porucha` | 30021 | – |

`sensor.acond_hp_porucha` má stav ve tvaru kódu (`OK`, `A01`, `W07`, …) a atributy `code`, `description`.
Tabulka všech 62+ kódů je v dokumentaci, integrace ji má kompletní.

**Binární sensory** – všech 16 bitů stavového slova 30007

`hp_on`, `hp_operation`, `hp_failure`, `dhw_heating`, `circulation_1`, `circulation_2`,
`solar_circulation`, `pool_circulation`, `defrosting`, `electric_heater`, `summer_mode`,
`brine_circulation`, `cooling`, `sg_ready_1`, `sg_ready_2`, `sg_ready_modbus`

## Energy dashboard

Čtyři energetické senzory mají `device_class: energy`, jednotku kWh a `state_class: total_increasing`,
takže je lze přidat do **Nastavení → Dashboardy → Energie** (vytápění i chlazení, zvlášť energie a elektřina).

## Jak se čte

Čte se **9 malých bloků**, každý zvlášť – jednotka, která neumí dlouhý blok nebo nemá
implementované některé adresy, tak nezablokuje celou integraci:

| Blok | Registry | Co v něm je |
|---|---|---|
| 1 | 30001–30004 | teploty okruhů |
| 2 | 30005–30008 | TUV + stavové slovo 30007 |
| 3 | 30009–30010 | vratná voda, venkovní |
| 4 | 30018 | výstupní voda |
| 5 | 30021 | kód poruchy |
| 6 | 30029 | COP |
| 7 | 30035–30038 | energie vytápění (2× DINT) |
| 8 | 30041 | SCOP |
| 9 | 30069–30072 | energie chlazení (2× DINT) |

- 32bitové hodnoty (`DINT`, energie) se čtou jako dvě registry, **high word první** (Big Endian).
- Teploty a COP jsou `INT ×10` → 228 = 22,8 °C, 45 = 4,5.
- Když jednotka některý blok odmítne, jeho entity zůstanou `unknown`, ostatní fungují dál
  a do logu se zapíše `Heat pump refused registers 300xx-300yy`.
- Výchozí interval 30 s, volitelný 5–3600 s.

## Požadavky

- Home Assistant **2024.2** nebo novější
- Acond s **aktivovaným Modbus TCP** (aktivuje servis, v jednotce pak musí být ModbusTCP zaškrtnuté v tmavě modrém pruhu na hlavní stránce)
- IP adresa jednotky, port **502**, Modbus ID **1** (ID 2 je obsazené pro kaskádu)

## Instalace přes HACS

1. HACS → **⋮ → Custom repositories**
2. URL: `https://github.com/wojtech-kovac08/ha-acond`, kategorie **Integration**
3. Nainstaluj **Acond Heat Pump** a restartuj Home Assistant
4. **Nastavení → Zařízení a služby → Přidat integraci → Acond Heat Pump**

## Ruční instalace

Zkopíruj složku `custom_components/acond` do `config/custom_components/acond` a restartuj HA.

## Konfigurace

| Parametr | Výchozí | Poznámka |
|---|---|---|
| host | – | IP adresa jednotky |
| port | 502 | TCP port Modbus |
| slave | 1 | Modbus ID (2 = kaskáda, nepoužívat) |
| scan_interval | 30 s | interval čtení |
| enable_circuit_2 | zapnuto | druhý topný okruh; vypni u jednookruhových jednotek |
| enable_energy | **vypnuto** | COP, SCOP a energetické registry (30029, 30035–30038, 30041, 30069–30072) |

Obě volby jde kdykoli změnit přes **Nastavení → Zařízení a služby → Acond HP → Konfigurovat**.
Když jsou vypnuté, příslušné entity vůbec nevzniknou (a registry se vůbec nečtou).

## Omezení

- Integrace je **read only** – žádný zápis, žádné změny nastavení jednotky.
- Climate hlásí vždy `heat` a nepodporuje `TARGET_TEMPERATURE`; teplota se nastavuje na jednotce.
- Jen **jeden master** může jednotku číst současně.

## Řešení problémů

- **„nepodařilo se otevřít TCP spojení"** – jednotka na dané IP/portu neposlouchá.
- **„jednotka neodpovídá na Modbus dotazy"** – TCP jde, ale jednotka mlčí (ModbusTCP není zaškrtnuté, nebo špatné ID).
- **COP / SCOP / energie jsou `unknown`** – jednotka tyto registry nemá. Nech `enable_energy`
  vypnuté, nebo je zapni jen když je jednotka opravdu implementuje.
- **„odmítla požadavek Modbus"** – jednotka vrátila exception response, obvykle na blok,
  který nemá implementovaný. Integrace se i tak nastaví a čte ostatní bloky.
  Po třech odmítnutích stejného bloku ho přestane čítat (aby nezasypával log)
  a napíše `Heat pump does not implement registers 300xx-300yy`.

## Diagnostika mapy registrů

Když některé entity zůstávají `unknown`, jednotka dané registry nejspíš nemá.
Skript `tools/probe_acond.py` projde adresy 30001–30079 a vypíše, které odpovídají:

```bash
pip install pymodbus
python tools/probe_acond.py 192.168.0.11
```

Výstup ukáže rozsahy implementovaných registrů i první nenulové hodnoty.
Podle něj se mapa v `const.py` upraví (nebo se nefunkční hodnoty vypustí).

## Roadmap

- [x] Teploty 2 okruhů + climate (read only)
- [x] TUV, venkovní, vratná a výstupní voda
- [x] Energie, COP, SCOP
- [x] Binární sensory ze stavového slova 30007
- [x] Kód poruchy s textem
- [ ] Diagnostika driveru (30023) jako samostatný sensor
- [ ] Diagnostics endpoint pro HA
- [ ] Volitelně zápis žádané teploty (až na vyžádání)

## Poznámka

Projekt není nijak spojený s výrobcem. Vychází z dokumentace „Protocol – Modbus TCP/RTU"
(`AC781180_52_v4.3.3.25`, resp. `AC781150_52_v4.3.3.25`).
