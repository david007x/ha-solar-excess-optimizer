# ☀️ HA Solar Excess Optimizer v0.1.1

Modulare PV-Überschussregelung für Home Assistant.
Verteilt Solarstrom-Überschuss automatisch und priorisierg an konfigurierbare Verbraucher.

---

## Installation

1. Repository in HA hinzufügen:
   `https://github.com/david007x/ha-solar-excess-optimizer`
2. „HA Solar Excess Optimizer" im Add-on Store installieren & starten
3. Sidebar-Panel „Solar Optimizer" erscheint automatisch

---

## Voraussetzung: Netzleistungs-Sensor

Ein Sensor der die Netzleistung in Watt liefert wird benötigt:
- **Positiv** = Einspeisung (Überschuss)
- **Negativ** = Netzbezug

Falls kein direkter Sensor vorhanden (z.B. Hoymiles via WiFi):
```yaml
# configuration.yaml
template:
  - sensor:
      - name: "Netzleistung"
        unit_of_measurement: "W"
        state: >
          {{ states('sensor.hoymiles_grid_export') | float(0)
           - states('sensor.hoymiles_grid_import') | float(0) }}
```

---

## Gerätetypen

### `switch` – Einfaches An/Aus
Schaltet ein wenn Überschuss ≥ Leistung + Hysterese.
```yaml
- name: "Gefrierschrank"
  type: switch
  priority: 3
  enabled: true
  switch_entity: switch.steckdose_gefrier
  power_w: 150
```

### `stepped` – Mehrere fixe Leistungsstufen
Aktiviert automatisch die höchste Stufe die der Überschuss deckt.
Jede Stufe hat einen eigenen Switch-Entity.
```yaml
- name: "Heizstab"
  type: stepped
  priority: 2
  enabled: true
  steps:
    - switch_entity: switch.heizstab_stufe1
      power_w: 1000
    - switch_entity: switch.heizstab_stufe2
      power_w: 2000
    - switch_entity: switch.heizstab_stufe3
      power_w: 3000
```

### `variable` – Stufenlose Regelung
Passt Leistung kontinuierlich an via `number.*` Entity (z.B. Wallbox Ampere).
```yaml
- name: "Wallbox"
  type: variable
  priority: 1
  enabled: true
  switch_entity: switch.wallbox
  power_entity: number.wallbox_current_ampere
  power_min: 1400
  power_max: 11000
  power_step: 230
  ramp_interval_sec: 30
  condition_entity: binary_sensor.wallbox_auto_verbunden   # optional
  consumption_entity: sensor.wallbox_leistung              # optional
```

### `wallbox` – Portable Wallbox mit Ladestufen
Für Wallboxen die den Ladestrom nur im ausgeschalteten Zustand ändern können.
Bei jedem Stufenwechsel: AUS → Ampere setzen → EIN.
```yaml
- name: "Portable Wallbox"
  type: wallbox
  priority: 1
  enabled: true
  switch_entity: switch.wallbox
  power_entity: number.wallbox_ladestrom_ampere
  steps_a: "6,8,10,13,16"          # Kommagetrennt
  voltage: 230
  power_cycle_delay_sec: 3          # Pause zwischen AUS und EIN
  ramp_interval_sec: 30
  condition_entity: binary_sensor.wallbox_auto_verbunden   # optional
  consumption_entity: sensor.wallbox_leistung              # optional
```

### `timed` – Mindestlaufzeit pro Tag
Nutzt bevorzugt PV-Überschuss, erzwingt Betrieb am Abend falls Ziel nicht erreicht.
```yaml
- name: "Waschmaschine"
  type: timed
  priority: 4
  enabled: true
  switch_entity: switch.steckdose_waschmaschine
  power_w: 2000
  min_runtime_minutes: 90
```

### `battery` – Hausbatterie
Reserviert Überschuss für Batterie bis Ziel-SOC erreicht ist.
Geräte mit niedrigerer Priorität bekommen nur den verbleibenden Rest.
```yaml
- name: "Hausbatterie"
  type: battery
  priority: 1
  enabled: true
  soc_entity: sensor.batterie_soc
  power_entity: sensor.batterie_ladeleistung   # optional, nur Anzeige
  target_soc: 100
  max_charge_power_w: 5000
```

---

## Optionale Felder (alle Gerätetypen)

| Feld | Beschreibung |
|---|---|
| `condition_entity` | Gerät nur aktivieren wenn Entity = `on` / `true` / `> 0` |
| `consumption_entity` | Tatsächliche Leistung aus HA lesen statt Schätzwert nutzen |
| `on_delay_sec` | Sekunden Überschuss stabil sein muss vor dem Einschalten (Standard: 30) |
| `off_delay_sec` | Sekunden Defizit stabil sein muss vor dem Ausschalten (Standard: 20) |

---

## Globale Konfiguration

```yaml
grid_power_entity: sensor.netzleistung   # Pflicht
hysteresis_w: 150                        # Schalthysterese in Watt
update_interval_sec: 10                  # Regelintervall
on_delay_sec: 30                         # Globale Einschaltverzögerung
off_delay_sec: 20                        # Globale Ausschaltverzögerung
```

---

## Web UI (Port 8099)

| Tab | Inhalt |
|---|---|
| **Dashboard** | Echtzeit-Übersicht, Override-Buttons pro Gerät, Batterie-SOC |
| **Verbraucher** | Geräte hinzufügen/entfernen/deaktivieren mit Entity-Picker |
| **Log** | Letzte Regelzyklen mit Leistungsverteilung |

**Override-Modi** direkt im Dashboard pro Gerät:
- **⬆ Zwang AN** – läuft immer, egal ob Überschuss
- **⟳ Auto** – normale Regelung
- **⬇ Zwang AUS** – bleibt aus

---

## HA Sidebar Panel

Das Add-on registriert beim Start automatisch „Solar Optimizer" in der HA Sidebar.

Falls das nicht funktioniert, manuell in `configuration.yaml` eintragen:
```yaml
panel_custom:
  - name: solar-optimizer-panel
    sidebar_title: Solar Optimizer
    sidebar_icon: mdi:solar-power
    url_path: solar-optimizer
    module_url: /local/solar_optimizer_panel.js
```

---

## Projektstruktur

```
app/
├── main.py                  # Web UI + Regelschleife
├── controller.py            # Hauptregler mit Priorisierung
├── config.py                # Konfiguration laden/speichern
├── ha_client.py             # HA REST API
├── register_panel.py        # Sidebar Panel Registrierung
├── cleanup_panel.py         # Alte Panel-Einträge bereinigen
└── devices/
    ├── base.py              # Basisklasse (Hysterese, Override, condition/consumption)
    ├── factory.py           # Geräte-Factory
    ├── switch_device.py
    ├── stepped_device.py
    ├── variable_device.py
    ├── wallbox_device.py
    ├── timed_device.py
    └── battery_device.py
```

Neuen Gerätetyp hinzufügen: neue Klasse in `devices/` erstellen, in `factory.py` registrieren – fertig.
