# Acond Heat Pump – Home Assistant integration

Nevýhradní (unofficial) integrace pro tepelná čerpadla **Acond** komunikující přes **Modbus TCP**.
Zatím jen **čtení teplot** dvou topných okruhů – žádaná a skutečná hodnota (registry 30001–30004).

Repo: <https://github.com/wojtech-kovac08/ha-acond>

## Co integrace umí

| Entita | Registr | Význam |
|---|---|---|
| `sensor.acond_hp_zadana_teplota_okruh_1` | 30001 | Žádaná teplota okruhu 1 |
| `sensor.acond_hp_aktualni_teplota_okruh_1` | 30002 | Aktuální teplota okruhu 1 (čidlo) |
| `sensor.acond_hp_zadana_teplota_okruh_2` | 30003 | Žádaná teplota okruhu 2 |
| `sensor.acond_hp_aktualni_teplota_okruh_2` | 30004 | Aktuální teplota okruhu 2 (čidlo) |

Hodnoty jsou v datovém modelu vedené jako `INT ×10`, integrace je převádí na °C (215 → 21,5 °C).
Čtení probíhá jedním blokem 4 registrů, takže na lince je jen jeden požadavek na cyklus.

## Požadavky

- Home Assistant **2024.2** nebo novější
- Tepelné čerpadlo Acond s **aktivovaným Modbus TCP** (aktivaci provádí servis – v jednotce je pak potřeba zaškrtnout ModbusTCP v tmavě modrém pruhu na hlavní stránce)
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

Při přidávání integrace se ověří, že se blok registrů skutečně přečte – když ne, dialog vrátí `cannot_connect`.

## Řešení problémů

- **cannot_connect** – zkontroluj IP, port, ID, a hlavně jestli je Modbus TCP v jednotce aktivovaný *a* zaškrtnutý. Stav „ModbusTCP false“ na displeji znamená, že v intervalu `MaxCommDataRefresh` nepřišla žádná data.
- **Entita je `unknown` / `unavailable`** – spojení spadlo; integrace se pokusí připojit znovu v dalším cyklu.
- **Nesmyslné hodnoty** – zkontroluj, že v jednotce běží firmware s tímto rozsahem registrů (dokumentace `v4.3.3.25`, 07.04.2026). Dokumentace OEM i Grandis je v tomto rozsahu shodná.
- Jen **jeden master** může být připojený současně – pokud jednotku čte i nějaký jiný systém, čtení se budou střídat/hádat.

## Roadmap

- [x] Čtení teplot 2 okruhů (žádaná + skutečná)
- [ ] Teplota TV, bazénu, venkovní a výstupní/vratné vody
- [ ] Binární sensory ze stavového slova 30007 (HP on, porucha, defrost, …)
- [ ] Kód poruchy 30021 / 30023 jako sensor s textovým popisem
- [ ] Zápis: žádané teploty (40001, 40003, 40005) a režim (40006)
- [ ] `number` / `select` / `climate` entity

## Poznámka

Projekt není nijak spojený s výrobcem. Vychází z dokumentace „Protocol – Modbus TCP/RTU“ (`AC781180_52_v4.3.3.25`, resp. `AC781150_52_v4.3.3.25`).
Použití na vlastní riziko – zápis do registrů může ovlivnit provoz vytápění.
