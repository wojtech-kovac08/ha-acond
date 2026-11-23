# Acond Heat Pump – Home Assistant integration

Nevýhradní (unofficial) integrace pro tepelná čerpadla **Acond** komunikující přes **Modbus TCP**.
**Pouze čte** teploty dvou topných okruhů a vystavuje je jako `climate` entity (použitelné v Bubble Card).
Do jednotky se nikdy nezapisuje.

Repo: <https://github.com/wojtech-kovac08/ha-acond>

## Co integrace umí

**Climate entity** – `climate.acond_hp_topny_okruh_1` a `..._okruh_2` (read only)

| Vlastnost | Zdroj |
|---|---|
| Aktuální teplota | 30002 / 30004 |
| Žádaná teplota | 30001 / 30003 |

**Senzory** (zůstávají vedle climate entit)

| Entita | Registr |
|---|---|
| `sensor.acond_hp_zadana_teplota_okruh_1` | 30001 |
| `sensor.acond_hp_aktualni_teplota_okruh_1` | 30002 |
| `sensor.acond_hp_zadana_teplota_okruh_2` | 30003 |
| `sensor.acond_hp_aktualni_teplota_okruh_2` | 30004 |

Hodnoty jsou v datovém modelu `INT ×10`, integrace je převádí na °C (228 → 22,8 °C).
Celý blok 30001–30004 se čte jedním požadavkem na cyklus.

## Bubble Card

```yaml
type: custom:bubble-card
card_type: climate
entity: climate.acond_hp_topny_okruh_1
```

Karta zobrazí aktuální a žádanou teplotu. Protože entita nepodporuje
`TARGET_TEMPERATURE`, **posuvník se nezobrazí** – teplota se v HA nedá měnit,
na to slouží ovládání na jednotce.

## Požadavky

- Home Assistant **2024.2** nebo novější
- Tepelné čerpadlo Acond s **aktivovaným Modbus TCP** (aktivuje servis, v jednotce pak musí být ModbusTCP zaškrtnuté v tmavě modrém pruhu na hlavní stránce)
- IP adresa jednotky, port **502**, Modbus ID **1** (ID 2 je obsazené pro kaskádu)

## Instalace přes HACS

1. HACS → **⋮ → Custom repositories**
2. URL: `https://github.com/wojtech-kovac08/ha-acond`, kategorie **Integration**
3. Nainstaluj **Acond Heat Pump** a restartuj Home Assistant
4. **Nastavení → Zařízení a služby → Přidat integraci → Acond Heat Pump**
5. Zadej IP adresu, port, Modbus ID a interval čtení

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

- Integrace je **read only** – žádný zápis do jednotky, žádné změny nastavení.
- Režim (topení/chlazení/off) ani stavové slovo jednotky se nečtou, climate proto hlásí vždy `heat`.
- Hodnoty jsou jen ke čtení; nastavení teploty se dělá na jednotce nebo v jejím webovém rozhraní.
- Jen **jeden master** může jednotku číst současně.

## Řešení problémů

- **„nepodařilo se otevřít TCP spojení"** – jednotka na dané IP/portu neposlouchá (síť, firewall, jednotka offline).
- **„jednotka neodpovídá na Modbus dotazy"** – TCP jde, ale jednotka mlčí: ModbusTCP není zaškrtnuté/aktivované, nebo špatné ID.
- **„odpověděla chybou Modbusu"** – firmware jednotky neodpovídá dokumentaci v4.3.3.25.

## Roadmap

- [x] Čtení teplot 2 okruhů
- [x] `climate` entity (read only)
- [ ] Volitelně zápis žádané teploty (40001 / 40003)
- [ ] Teplota TV jako `water_heater` (40005)
- [ ] Binární sensory ze stavového slova 30007
- [ ] Kód poruchy 30021 / 30023 jako sensor s textovým popisem

## Poznámka

Projekt není nijak spojený s výrobcem. Vychází z dokumentace „Protocol – Modbus TCP/RTU" (`AC781180_52_v4.3.3.25`, resp. `AC781150_52_v4.3.3.25`).
