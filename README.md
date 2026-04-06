# HA Solar Excess Optimizer

Home Assistant Add-on Repository für modulare PV-Überschussregelung.

Maintainer: [david007x](https://github.com/david007x)

## Installation

1. [![Repository hinzufügen](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https://github.com/david007x/ha-solar-excess-optimizer)

   **Oder manuell:**
   Einstellungen → Add-ons → Add-on Store → ⋮ → Repositories → diese URL einfügen:
   ```
   https://github.com/david007x/ha-solar-excess-optimizer
   ```

2. „HA Solar Excess Optimizer" im Store suchen & installieren
3. Add-on starten – Sidebar-Panel wird automatisch registriert

## Features

- **6 Gerätetypen:** switch · stepped · variable · wallbox · timed · battery
- **Priorisierung:** Überschuss wird nach Priorität auf Geräte verteilt
- **Zeitbasierte Hysterese:** Flapping-Schutz via Ein-/Ausschaltverzögerung
- **Manueller Override:** Gerät per Klick zwingen (AN / AUTO / AUS)
- **condition_entity:** Gerät nur aktivieren wenn Bedingung erfüllt (z.B. Auto verbunden)
- **consumption_entity:** Tatsächlichen Verbrauch aus HA lesen statt Schätzwert
- **Entity-Picker:** Live-Suche aller HA-Entities im Web UI
- **HA Sidebar Panel:** Automatische Registrierung beim Add-on-Start
- **Mobile UI:** Responsives Dashboard für Smartphone und Tablet

## Add-ons in diesem Repository

### ☀️ HA Solar Excess Optimizer v0.1.1

| Gerätetyp | Beschreibung | Beispiel |
|---|---|---|
| `switch` | Einfaches An/Aus | Smarte Steckdose, Relais |
| `stepped` | Mehrere fixe Leistungsstufen | Heizstab 1/2/3 kW |
| `variable` | Stufenlose Regelung via `number.*` | Wallbox (Ampere) |
| `wallbox` | Portable Wallbox mit fixen Ladestufen + Ein/Aus-Zyklus | 6/8/10/13/16A Wallbox |
| `timed` | Mindestlaufzeit pro Tag | Waschmaschine |
| `battery` | Aktive Ladeleistungsreservierung | Hausbatterie |
