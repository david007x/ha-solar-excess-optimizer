# Änderungshistorie – ha-solar-excess-optimizer

## v0.3.0 (2026-05-22)
**Fix: HA API-Auth fehlgeschlagen – Entity-Picker und Gerätesteuerung tot**

HA Supervisor setzt den API-Token als `SUPERVISOR_TOKEN`, nicht als `HA_TOKEN`.
Da `ha_client.py` den falschen Variablennamen gelesen hat, war der Token immer
leer → alle HA API-Calls schlugen mit 401 fehl → Entity-Picker zeigte keine
Ergebnisse, Gerätesteuerung (turn_on/off, set_number) funktionierte nicht.

- `ha_client.py`: liest jetzt `SUPERVISOR_TOKEN` (primär) und `HA_TOKEN` (Fallback)
- Warnung im Addon-Log wenn kein Token gefunden wird
- 401-Fehler bei `get_all_states()` wird explizit geloggt

## v0.2.9 (2026-05-22)
**Fix: Startup-Crash bei Neuinstallation (KeyError: grid_power_entity)**

HA Supervisor schreibt bei `schema: {}` ein leeres `{}` in `options.json`.
`config.load()` gab diese leere Config zurück ohne Defaults zu mergen,
`SolarController.__init__` crashte dann mit `KeyError: 'grid_power_entity'`.

- `config.py`: Loaded config wird immer mit `_DEFAULTS` gemergt
- `controller.py`: `cfg.get()` statt `cfg[]`; `run_cycle()` überspringt Zyklus wenn nicht konfiguriert

## v0.2.8 (2026-05-22)
**Fix: SteppedDevice-Hysterese war nur einseitig**

## v0.2.7 (2026-05-22)
**Fix: Wallbox-Hysterese war nur einseitig**

## v0.2.6 (2026-05-22)
**15 Bugs behoben (vollständige Code-Analyse)**

## v0.2.2 – v0.1.7 (2026-05-14)
Siehe Git-History für ältere Einträge.
