# ☀️ HA Solar Excess Optimizer v5 – Home Assistant Add-on

Modulare PV-Überschussregelung mit 4 Gerätetypen, Web UI und YAML-Konfiguration.

## Gerätetypen

| Typ | Beschreibung | Beispiel |
|---|---|---|
| `switch` | Einfaches An/Aus | Steckdose, einfacher Heizstab |
| `stepped` | Mehrere fixe Leistungsstufen | Heizstab 1/2/3 kW |
| `variable` | Stufenlose Regelung via `number.*` | Wallbox (Ampere) |
| `timed` | Mindestlaufzeit pro Tag | Waschmaschine, Spülmaschine |

## Installation

1. GitHub Repo mit diesem Code erstellen
2. In HA: **Einstellungen → Add-ons → Store → ⋮ → Repositories** → URL einfügen
3. "HA Solar Excess Optimizer" installieren & starten

## Wichtigster Sensor: Netzleistung

```yaml
# configuration.yaml – falls kein direkter Sensor vorhanden
template:
  - sensor:
      - name: "Netzleistung"
        unit_of_measurement: "W"
        # Positiv = Einspeisung (Überschuss) | Negativ = Bezug
        state: >
          {{ states('sensor.hoymiles_grid_export') | float(0)
           - states('sensor.hoymiles_grid_import') | float(0) }}
```

## Konfiguration (config.yaml / Web UI)

```yaml
grid_power_entity: sensor.netzleistung   # Pflicht
hysteresis_w: 150
update_interval_sec: 10

devices:
  # Typ 1: Switch
  - name: "Gefrierschrank"
    type: switch
    priority: 3
    enabled: true
    switch_entity: switch.steckdose_gefrier
    power_w: 150

  # Typ 2: Stufen
  - name: "Heizstab"
    type: stepped
    priority: 2
    enabled: true
    steps:
      - switch_entity: switch.heizstab_stufe1
        power_w: 1000
      - switch_entity: switch.heizstab_stufe2
        power_w: 2000

  # Typ 3: Stufenlos (Wallbox)
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

  # Typ 4: Zeitgesteuert
  - name: "Waschmaschine"
    type: timed
    priority: 4
    enabled: true
    switch_entity: switch.waschmaschine
    power_w: 2000
    min_runtime_minutes: 90
```

## Web UI (Port 8099)

- **Dashboard**: Echtzeit-Übersicht aller Geräte
- **Verbraucher**: Geräte hinzufügen/entfernen/deaktivieren ohne YAML-Edit
- **Log**: Letzten Regelzyklen

## Projektstruktur

```
app/
├── main.py              # Web UI + Regelschleife
├── controller.py        # Hauptregler
├── config.py            # Laden/Speichern der Konfiguration
├── ha_client.py         # HA REST API
└── devices/
    ├── base.py          # Abstrakte Basisklasse
    ├── factory.py       # Geräte-Factory (Typ → Klasse)
    ├── switch_device.py
    ├── stepped_device.py
    ├── variable_device.py
    └── timed_device.py
```

Neuen Gerätetyp hinzufügen: neue Klasse in `devices/` erstellen,
in `factory.py` registrieren – fertig.

## HA Sidebar Panel

Das Add-on registriert beim Start automatisch ein **Custom Panel** in der HA Sidebar
unter dem Namen "Solar Optimizer" mit dem Icon ☀.

### Manueller Fallback (falls automatisch nicht klappt)

1. Panel HTML liegt nach Add-on-Start unter `/config/www/solar_excess_optimizer.html`
2. Folgendes in `configuration.yaml` eintragen und HA neu starten:

```yaml
panel_custom:
  solar_excess_optimizer:
    name: solar-optimizer-panel
    sidebar_title: Solar Optimizer
    sidebar_icon: mdi:solar-power
    url_path: solar-optimizer
    module_url: /local/solar_excess_optimizer.html
```

3. HA neu starten → "Solar Optimizer" erscheint in der Sidebar
