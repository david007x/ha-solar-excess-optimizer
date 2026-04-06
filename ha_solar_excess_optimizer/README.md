# ☀️ HA Solar Excess Optimizer v0.1.1 – Home Assistant Add-on

Modular PV surplus control for wallbox, heating rod, smart plugs, and battery.

## Device Types

| Type | Description | Example |
|---|---|---|
| `switch` | Simple on/off with hysteresis | Smart plug, simple relay |
| `stepped` | Multiple fixed power levels | Heating rod 1/2/3 kW |
| `variable` | Continuous control via `number.*` | Wallbox (ampere) |
| `timed` | Minimum runtime per day | Washing machine, dishwasher |
| `battery` | Active charge power reservation | Home battery |

## Installation

1. Create a GitHub repository with this code
2. In HA: **Settings → Add-ons → Store → ⋮ → Repositories** → paste URL
3. Install "HA Solar Excess Optimizer" and start

## Required Sensor: Grid Power

```yaml
# configuration.yaml – if no direct sensor available
template:
  - sensor:
      - name: "Grid Power"
        unit_of_measurement: "W"
        # Positive = export (surplus) | Negative = import
        state: >
          {{ states('sensor.hoymiles_grid_export') | float(0)
           - states('sensor.hoymiles_grid_import') | float(0) }}
```

## Configuration

```yaml
grid_power_entity: sensor.grid_power   # required
hysteresis_w: 150
update_interval_sec: 10
on_delay_sec: 30
off_delay_sec: 20

devices:
  # Battery (highest priority)
  - name: "Home Battery"
    type: battery
    priority: 1
    enabled: true
    soc_entity: sensor.battery_soc
    power_entity: sensor.battery_charge_power   # optional
    target_soc: 100
    max_charge_power_w: 5000

  # Wallbox (variable)
  - name: "Wallbox"
    type: variable
    priority: 2
    enabled: true
    switch_entity: switch.wallbox
    power_entity: number.wallbox_current_ampere
    power_min: 1400
    power_max: 11000
    power_step: 230
    ramp_interval_sec: 30
    condition_entity: binary_sensor.car_connected   # optional
    consumption_entity: sensor.wallbox_power        # optional

  # Heating rod (stepped)
  - name: "Heating Rod"
    type: stepped
    priority: 3
    enabled: true
    steps:
      - switch_entity: switch.heating_rod_level1
        power_w: 1000
      - switch_entity: switch.heating_rod_level2
        power_w: 2000

  # Smart plug (switch)
  - name: "Freezer"
    type: switch
    priority: 4
    enabled: true
    switch_entity: switch.plug_freezer
    power_w: 150

  # Washing machine (timed)
  - name: "Washing Machine"
    type: timed
    priority: 5
    enabled: true
    switch_entity: switch.plug_washing_machine
    power_w: 2000
    min_runtime_minutes: 90
```

## Optional Device Fields (all types)

| Field | Description |
|---|---|
| `condition_entity` | Only activate when entity = `on` / `true` / `> 0` |
| `consumption_entity` | Read actual power from HA sensor instead of using estimate |
| `on_delay_sec` | Seconds surplus must be stable before switching on |
| `off_delay_sec` | Seconds deficit must be stable before switching off |

## Web UI (Port 8099)

- **Dashboard** – real-time overview of all devices with manual override buttons
- **Devices** – add/remove/disable devices with entity picker
- **Log** – last control cycles

## HA Sidebar Panel

The add-on automatically registers a **Custom Panel** in the HA sidebar on startup.

### Manual Fallback

If automatic registration fails, add to `configuration.yaml` and restart HA:

```yaml
panel_custom:
  - name: solar-optimizer-panel
    sidebar_title: Solar Optimizer
    sidebar_icon: mdi:solar-power
    url_path: solar-optimizer
    module_url: /local/solar_optimizer_panel.js
```

## Project Structure

```
app/
├── main.py              # Web UI + control loop
├── controller.py        # Main controller
├── config.py            # Load/save configuration
├── ha_client.py         # HA REST API
├── register_panel.py    # Sidebar panel registration
└── devices/
    ├── base.py          # Abstract base class
    ├── factory.py       # Device factory
    ├── switch_device.py
    ├── stepped_device.py
    ├── variable_device.py
    ├── timed_device.py
    └── battery_device.py
```

To add a new device type: create a new class in `devices/`, register it in `factory.py`.
