# Solar Excess Optimizer v0.2.7

Home Assistant addon for managing solar excess power.

Controls devices (wallbox, switches, stepped devices) based on available solar surplus.

## Features
- Priority-based device control
- Bidirectional hysteresis for step-based devices (prevents flapping)
- Wallbox support with power-cycle step changes
- Time-based on/off delays
- Force on/off overrides
- Condition entity support
- HA sensor publishing
- Web dashboard via HA Ingress

## Device Types
- `switch` – simple on/off
- `stepped` – multiple fixed power levels
- `variable` – continuous power (e.g. via number entity)
- `wallbox` – stepped charging with power-cycle between steps
- `timed` – time-window controlled
- `battery` – battery SOC aware
