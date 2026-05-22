# Änderungshistorie – ha-solar-excess-optimizer

## v0.2.9 (2026-05-22)
**Fix: Startup-Crash bei Neuinstallation (KeyError: grid_power_entity)**

HA Supervisor schreibt bei `schema: {}` ein leeres `{}` in `options.json`.
`config.load()` gab diese leere Config zurück ohne Defaults zu mergen,
`SolarController.__init__` crashte dann mit `KeyError: 'grid_power_entity'`.
Da der Webserver erst nach dem Controller startet, war die UI nie erreichbar.

- `config.py`: Loaded config wird immer mit `_DEFAULTS` gemergt → fehlende Schlüssel
  fallen auf Defaults zurück statt zu crashen. `grid_power_entity` Default ist jetzt
  leer-String (nicht mehr `sensor.grid_power`) um den User zur Konfiguration zu zwingen.
- `controller.py`: `cfg.get()` statt `cfg[]` als Sicherheitsnetz. `run_cycle()` überspringt
  den Zyklus mit Warning wenn `grid_power_entity` noch nicht konfiguriert ist.

## v0.2.8 (2026-05-22)
**Fix: SteppedDevice-Hysterese war nur einseitig**

Dieselbe Korrektur wie v0.2.7 für die Wallbox: `new_target`-Berechnung nutzt
jetzt bidirektionale Hysterese.

- Hochschalten zu Stufe i: `surplus >= power_w + hysteresis`
- Halten / Runterschalten: `surplus >= power_w - hysteresis`

## v0.2.7 (2026-05-22)
**Fix: Wallbox-Hysterese war nur einseitig**

`_watts_to_step` hat bisher für Hoch- UND Runterschalten denselben
Schwellwert `watts + hysteresis` verwendet.

Korrektur: Bidirektionale Hysterese:
- Hochschalten zu Stufe i: `surplus >= watts_i + hysteresis`
- Halten / Runterschalten: `surplus >= watts_i - hysteresis`

## v0.2.6 (2026-05-22)
**15 Bugs behoben (vollständige Code-Analyse)**

| # | Datei | Fix |
|---|-------|-----|
| 1 | `variable_device.py` | **Kritisch:** Falsch eingerücktes `return` machte die gesamte Auto-Logik unerreichbar |
| 2 | `switch/stepped/timed_device.py` | **Kritisch:** `_allocated_w` wurde bei aktivem Gerät nie gesetzt |
| 3 | `main.py` | **Kritisch:** Drag-and-Drop hatte keine Event-Handler im DOM |
| 4 | `variable_device.py` | `voltage`-Feld hinzugefügt (Standard: 230V) |
| 5 | `main.py` | Regelintervall wird dynamisch aus `controller.cfg` gelesen |
| 6 | `switch/stepped/variable/timed_device.py` | `_record_activation/deactivation` in allen Typen |
| 7 | `timed_device.py` | `datetime.now().day` durch `date.today()` ersetzt |
| 8 | `wallbox_device.py` | `asyncio.ensure_future()` → `asyncio.create_task()` |
| 9 | `main.py` | `bat-power-entity` wird gespeichert/wiederhergestellt |
| 10 | `main.py` | `renderDashboard()` Guard gegen leeres Status-Dict |
| 11 | `main.py` | `ha_publisher.publish()` nach jedem Zyklus aufgerufen |
| 12-13 | `main.py` | XSS-Schutz via `escapeHtml()` |
| 14 | `main.py` | `showPage()` nutzt Event-Parameter |
| 15 | `main.py` | `saveConfig()` validiert Grid Power Entity |

## v0.2.2 (2026-05-14)
**Fix: Doppelte Sidebar-Spalte**

## v0.2.1 (2026-05-14)
**Fix: API-Calls durch HA Ingress**

## v0.2.0 (2026-05-14)
**Fix: Dashboard Verbindung zurückgesetzt**

## v0.1.9 (2026-05-14)
**Fix: Möglicher Startup-Crash (lazy imports)**

## v0.1.8 (2026-05-14)
**Fix: Docker Build schlägt fehl**

## v0.1.7 (2026-05-14)
**9 Bugs behoben (Code-Analyse)**
