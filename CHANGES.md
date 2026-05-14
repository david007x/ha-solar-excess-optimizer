# Änderungshistorie – ha-solar-excess-optimizer

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
