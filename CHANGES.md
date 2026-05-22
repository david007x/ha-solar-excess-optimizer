# Änderungshistorie – ha-solar-excess-optimizer

## v0.2.8 (2026-05-22)
**Fix: SteppedDevice-Hysterese war nur einseitig**

Dieselbe Korrektur wie v0.2.7 für die Wallbox: `new_target`-Berechnung nutzt
jetzt bidirektionale Hysterese.

- Hochschalten zu Stufe i: `surplus >= power_w + hysteresis`
- Halten / Runterschalten: `surplus >= power_w - hysteresis`

Previell bot `off_delay_sec` eine zeitliche Abpufferung, aber der Leistungsschwellwert
selbst war in beide Richtungen falsch – schon ein minimaler Einbruch unter
`power_w + hysteresis` löste den Off-Timer aus.

## v0.2.7 (2026-05-22)
**Fix: Wallbox-Hysterese war nur einseitig**

Die Funktion `_watts_to_step` hat bisher für Hoch- UND Runterschalten denselben
Schwellwert `watts + hysteresis` verwendet. Das bedeutet: sobald der Überschuss
nur 1W unter `watts_i + hysteresis` fiel, wurde sofort eine Stufe runtergeschaltet –
obwohl die aktuelle Stufe noch problemlos gedeckt wäre.

**Korrektur:** Bidirektionale Hysterese:
- Hochschalten zu Stufe i: `surplus >= watts_i + hysteresis` (strenger)
- Halten / Runterschalten: `surplus >= watts_i - hysteresis` (großzügiger)

Beispiel bei 8A-Stufe (1840W) und 150W Hysterese:
- Vorher: Stufenwechsel sobald Überschuss < 1990W
- Nachher: Stufenwechsel erst wenn Überschuss < 1690W (300W Hysterese-Band)

## v0.2.6 (2026-05-22)
**15 Bugs behoben (vollständige Code-Analyse)**

| # | Datei | Fix |
|---|-------|-----|
| 1 | `variable_device.py` | **Kritisch:** Falsch eingerücktes `return` machte die gesamte Auto-Logik unerreichbar – Variable-Device war in Auto-Mode komplett kaputt |
| 2 | `switch/stepped/timed_device.py` | **Kritisch:** `_allocated_w` wurde bei aktivem Gerät nie gesetzt → Brutto-Überschuss-Berechnung im Controller war dauerhaft falsch |
| 3 | `main.py` | **Kritisch:** Drag-and-Drop im Devices-Tab hatte CSS und JS-Funktionen, aber keine Event-Handler im DOM – Feature war tot |
| 4 | `variable_device.py` | `voltage`-Feld hinzugefügt (Standard: 230V) – `_set_power()` hat bisher immer durch 230 geteilt, auch bei 3-Phasen-Geräten |
| 5 | `main.py` | Regelintervall wird jetzt nach Config-Reload dynamisch aus `controller.cfg` gelesen statt einmalig beim Start |
| 6 | `switch/stepped/variable/timed_device.py` | `_record_activation()` / `_record_deactivation()` in allen Gerätetypen aufgerufen → `min_runtime_sec` (Advanced-Setting) wirkt jetzt auch für diese Typen |
| 7 | `timed_device.py` | `datetime.now().day` durch `date.today()` ersetzt – Tagesvergleich per Tag-im-Monat konnte nach >1 Monat Uptime falsch zurücksetzen |
| 8 | `wallbox_device.py` | `asyncio.ensure_future()` (deprecated seit Python 3.10) durch `asyncio.create_task()` ersetzt |
| 9 | `main.py` | `bat-power-entity` Feld wird jetzt in `addDevice()` und `editDevice()` gespeichert und wiederhergestellt |
| 10 | `main.py` | `renderDashboard()` Guard hinzugefügt – kein stiller Crash mehr wenn `/api/status` vor dem ersten Regelzyklus aufgerufen wird |
| 11 | `main.py` | `ha_publisher.publish()` wird jetzt nach jedem Regelzyklus aufgerufen – virtuelle HA-Sensoren (`sensor.seo_*`) werden endlich befüllt |
| 12 | `main.py` | Log-Nachrichten in Gerätekarten werden jetzt durch `escapeHtml()` geschützt (XSS) |
| 13 | `main.py` | Entity-Picker escaped `entity_id`, `friendly_name`, `state`, `unit` korrekt (XSS) |
| 14 | `main.py` | `showPage()` nutzt Event-Parameter statt deprecated `event`-Global |
| 15 | `main.py` | `saveConfig()` validiert Grid Power Entity vor dem Speichern |

## v0.2.2 (2026-05-14)
**Fix: Doppelte Sidebar-Spalte**
- `config.yaml`: `panel_icon` + `panel_title` hinzugefügt → HA Supervisor erstellt Sidebar-Eintrag automatisch via Ingress
- `run.sh`: `register_panel.py` nicht mehr aufgerufen (war Ursache des Doppeleintrags)
- `cleanup_panel.py`: Regex-Fix – erkennt jetzt beide Varianten (`End` und `Ende`), entfernt alten `panel_custom`-Eintrag beim Start

## v0.2.1 (2026-05-14)
**Fix: API-Calls durch HA Ingress (Login-Fehler in HA-Log)**
- `main.py`: `const _BASE = window.location.pathname` berechnet den Ingress-Pfad dynamisch
- Alle `fetch('/api/...')` Calls nutzen jetzt `_BASE + '/api/...'`
- Funktioniert sowohl via Ingress als auch direktem Port-Zugriff

## v0.2.0 (2026-05-14)
**Fix: Dashboard "Verbindung zurückgesetzt"**
- `config.yaml`: `ingress: true` + `ingress_port: 8099` aktiviert
- `solar_optimizer_panel.js`: iframe-URL von `http://{host}:8099` auf `/api/hassio/app/ha_solar_excess_optimizer` geändert
- Ursache: Moderne Browser blockieren HTTP-iframes auf HTTPS-Seiten (Mixed Content)

## v0.1.9 (2026-05-14)
**Fix: Möglicher Startup-Crash**
- `base.py`: `ha_client`-Imports wieder als lazy imports innerhalb der Methoden (verhindert Importfehler beim Start)
- `run.sh`: Versionsstring aktualisiert

## v0.1.8 (2026-05-14)
**Fix: Docker Build schlägt fehl**
- `build.yaml` hinzugefügt – HA Supervisor konnte `$BUILD_FROM` nicht setzen
- Base-Images für alle Architekturen: amd64, aarch64, armhf, armv7 (Python 3.12 / Alpine 3.19)
- `Dockerfile`: Überflüssiges `apk add python3 py3-pip` entfernt

## v0.1.7 (2026-05-14)
**9 Bugs behoben (Code-Analyse)**

| # | Datei | Fix |
|---|-------|-----|
| 1 | `controller.py` | `import time` auf Modulebene verschoben |
| 2 | `ha_client.py` | Geteilte `aiohttp.ClientSession` (Connection-Pooling) |
| 3 | `ha_client.py` | Response-Status-Checks für `turn_on`, `turn_off`, `set_number` |
| 4 | `ha_client.py` | Neue `get_all_states()` Funktion |
| 5 | `base.py` | `forced`-Feld in `_base_status()` → Force-Badge im Frontend funktioniert |
| 6 | `battery_device.py` | `OVERRIDE_FORCE_ON` wird jetzt korrekt behandelt |
| 7 | `wallbox_device.py` | Überflüssige `hasattr`-Checks entfernt |
| 8 | `main.py` | XSS-Schutz via `escapeHtml()` für Gerätenamen |
| 9 | `main.py` | Totes doppeltes `loadEntities` entfernt, `handle_entities` nutzt `get_all_states()` |
