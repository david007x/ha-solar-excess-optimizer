# Dashboard Setup Guide

## Aufbau

```
HA Dashboard
├── Tab 1: Übersicht      → native Lovelace (live Entities)
├── Tab 2: Konfiguration  → iframe → Web UI Port 8099
└── Tab 3: Statistiken    → Verlaufsdiagramme
```

## Automatisch erstellte Entities

Das Add-on schreibt nach jedem Regelzyklus folgende Sensor-Entities in HA:

| Entity | Beschreibung |
|--------|-------------|
| `sensor.seo_surplus_w` | PV Überschuss in W |
| `sensor.seo_consuming_w` | Summe aller aktiven Verbraucher |
| `sensor.seo_remaining_w` | Verbleibend nach Regelung |
| `sensor.seo_active_devices` | Anzahl aktiver Geräte |
| `sensor.seo_device_<name>_w` | Leistung pro Gerät |
| `sensor.seo_device_<name>_runtime` | Laufzeit heute (timed-Geräte) |
| `sensor.seo_device_<name>_step` | Aktive Stufe (stepped-Geräte) |
| `sensor.seo_device_<name>_pct` | Auslastung % (variable-Geräte) |

`<name>` = Gerätename in Kleinbuchstaben, z.B. "Wallbox" → `seo_device_wallbox_w`

## Benötigte Custom Cards (via HACS)

- **mushroom** – Status-Karten
- **apexcharts-card** – Verlaufsdiagramme
- **power-flow-card-plus** – Energiefluss (optional)

## Dashboard installieren

### Option A – Neues Dashboard (empfohlen)
1. HA → Einstellungen → Dashboards → + Dashboard hinzufügen
2. Titel: `Solar Excess Optimizer`, Icon: `mdi:solar-power`
3. Dashboard öffnen → ⋮ → Bearbeiten → ⋮ → Raw-Konfigurationseditor
4. Inhalt von `lovelace_dashboard.yaml` einfügen

### Option B – YAML-Datei
`configuration.yaml`:
```yaml
lovelace:
  dashboards:
    solar-optimizer:
      mode: yaml
      title: Solar Optimizer
      icon: mdi:solar-power
      filename: lovelace/solar_excess_optimizer_dashboard.yaml
      show_in_sidebar: true
```

## Sidebar Panel (direkter Link zur Konfig-UI)

`configuration.yaml`:
```yaml
panel_iframe:
  solar_optimizer_config:
    title: "SEO Konfiguration"
    icon: mdi:cog
    url: "http://homeassistant.local:8099"
    require_admin: true
```

## Ingress (kein offener Port nötig)

In `config.yaml` des Add-ons ergänzen:
```yaml
ingress: true
ingress_port: 8099
```
Dann im Dashboard-iframe:
```yaml
url: "/api/hassio_ingress/ha_solar_excess_optimizer"
```
