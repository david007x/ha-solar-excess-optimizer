# Änderungshistorie – ha-solar-excess-optimizer

## v0.3.1 (2026-05-22)
**Fix: 401 Unauthorized bei allen HA API-Calls**

`homeassistant_api: true` fehlte in `config.yaml`. Ohne dieses Flag hat
`SUPERVISOR_TOKEN` keine Berechtigung die HA Core REST API aufzurufen
(`http://supervisor/core/api/...`). Betroffen waren Entity-Picker,
Zustandsabfragen und Gerätesteuerung (turn_on/off, set_number).

## v0.3.0 (2026-05-22)
**Fix: HA API-Auth – falscher Env-Var-Name**

`HA_TOKEN` → `SUPERVISOR_TOKEN` (primär) + `HA_TOKEN` (Fallback).

## v0.2.9 (2026-05-22)
**Fix: Startup-Crash bei Neuinstallation (KeyError: grid_power_entity)**

Config-Defaults werden jetzt immer gemergt; `controller.py` nutzt `.get()`.

## v0.2.8 (2026-05-22)
**Fix: SteppedDevice-Hysterese war nur einseitig**

## v0.2.7 (2026-05-22)
**Fix: Wallbox-Hysterese war nur einseitig**

## v0.2.6 (2026-05-22)
**15 Bugs behoben (vollständige Code-Analyse)**

## v0.2.2 – v0.1.7 (2026-05-14)
Siehe Git-History für ältere Einträge.
