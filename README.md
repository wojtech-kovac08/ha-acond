# Acond Heat Pump – Home Assistant integration

Nevýhradní (unofficial) integrace pro tepelná čerpadla **Acond** komunikující přes **Modbus TCP**.
Čte teploty dvou topných okruhů a vystavuje je jako `climate` entity (použitelné v Bubble Card).

Repo: <https://github.com/wojtech-kovac08/ha-acond>

## Co integrace umí

**Climate entity** – `climate.acond_hp_topny_okruh_1` a `..._okruh_2`

| Vlastnost | Zdroj |
|---|---|
| Aktuální teplota | 30002 / 30004 |
| Žádaná teplota (10–30 °C, krok 0,1) | čtení 30001 / 30003, zápis 40001 / 40003 |
| Režim OFF / HEAT / COOL | čtení 30014, zápis 40006 |
| `hvac_action` (topí / chladí / idle) | 30007 (bity 0 a 1) |

**Senzory** (zůstávají vedle climate entit)

| Entita | Registr |
|---|---|
| `sensor.acond_hp_zadana_teplota_okruh_1` | 30001 |
| `sensor.acond_hp_aktualni_teplota_okruh_1` | 30002 |
| `sensor.acond_hp_zadana_teplota_okruh_2` | 30003 |
| `sensor.acond_hp_aktualni_teplota_okruh_2` | 30004 |

Hodnoty jsou v datovém modelu `INT ×10`, integrace je převádí na °C (228 → 22,8 °C).
Celý blok 30001–30014 se čte jedním požadavkem na cyklus.

## Bubble Card

```yaml
type: custom:bubble-card
card_type: climate
entity: climate.acond_hp_topny_okruh_1
```

Karta si sama vezme aktuální teplotu, slider žádané teploty i tlačítka režimů.

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

## Omezení a chování zápisu

- Režim je **globální pro celou jednotku** – obě climate entity (okruh 1 i 2) proto ukazují a mění stejný režim.
- `HEAT` zapisuje bit 0 (automatický režim), aby zůstalo povolené i záložní/bivalentní topení. `COOL` = bit 4, `OFF` = bit 3.
- Ostatní bity slova 40006 (solar, bazén, SG ready, přepnutí zima/léto) integrace **zachová** – před zápisem si je přečte.
- Pokud je jednotka v režimu „jen záložní topení" (3) nebo „ručně" (5), climate hlásí `HEAT`; přepnutím na `HEAT` se jednotka přepne do automatiky.
- Hodnota žádané teploty mimo 10–30 °C jednotka ignoruje a použije hodnotu z čidla.

## Řešení problémů

- **„nepodařilo se otevřít TCP spojení"** – jednotka na dané IP/portu neposlouchá (síť, firewall, jednotka offline).
- **„jednotka neodpovídá na Modbus dotazy"** – TCP jde, ale jednotka mlčí: ModbusTCP není zaškrtnuté/aktivované, nebo špatné ID.
- **„odpověděla chybou Modbusu"** – firmware jednotky neodpovídá dokumentaci v4.3.3.25.
- Jen **jeden master** může jednotku číst současně.

## Roadmap

- [x] Čtení teplot 2 okruhů
- [x] `climate` entity + zápis žádané teploty a režimu
- [ ] Teplota TV jako `water_heater` (40005)
- [ ] Binární sensory ze stavového slova 30007
- [ ] Kód poruchy 30021 / 30023 jako sensor s textovým popisem
- [ ] Tichý režim (`switch`) – 40018–40020
- [ ] Energetické sensory (30035+, 30069+)

## Poznámka

Projekt není nijak spojený s výrobcem. Vychází z dokumentace „Protocol – Modbus TCP/RTU" (`AC781180_52_v4.3.3.25`, resp. `AC781150_52_v4.3.3.25`).
Použití na vlastní riziko – zápis do registrů ovlivňuje provoz vytápění.
