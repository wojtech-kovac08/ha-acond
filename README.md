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
| `sensor.acond_hp_zadana_teplota_tv` | 30005 | °C |
| `sensor.acond_hp_teplota_tv` | 30006 | °C |
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

- Blok **30001–30044** a blok **30069–30072** – dva požadavky na jeden cyklus.
- 32bitové hodnoty (`DINT`, energie) se čtou jako dvě registry, **high word první** (Big Endian).
- Teploty a COP jsou `INT ×10` → 228 = 22,8 °C, 45 = 4,5.
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

## Omezení

- Integrace je **read only** – žádný zápis, žádné změny nastavení jednotky.
- Climate hlásí vždy `heat` a nepodporuje `TARGET_TEMPERATURE`; teplota se nastavuje na jednotce.
- Jen **jeden master** může jednotku číst současně.

## Řešení problémů

- **„nepodařilo se otevřít TCP spojení"** – jednotka na dané IP/portu neposlouchá.
- **„jednotka neodpovídá na Modbus dotazy"** – TCP jde, ale jednotka mlčí (ModbusTCP není zaškrtnuté, nebo špatné ID).
- **„odpověděla chybou Modbusu"** – firmware neodpovídá dokumentaci v4.3.3.25.

## Roadmap

- [x] Teploty 2 okruhů + climate (read only)
- [x] TV, venkovní, vratná a výstupní voda
- [x] Energie, COP, SCOP
- [x] Binární sensory ze stavového slova 30007
- [x] Kód poruchy s textem
- [ ] Diagnostika driveru (30023) jako samostatný sensor
- [ ] Diagnostics endpoint pro HA
- [ ] Volitelně zápis žádané teploty (až na vyžádání)

## Poznámka

Projekt není nijak spojený s výrobcem. Vychází z dokumentace „Protocol – Modbus TCP/RTU"
(`AC781180_52_v4.3.3.25`, resp. `AC781150_52_v4.3.3.25`).
