import logging
from devices.factory import create_device
from devices.base import BaseDevice, OVERRIDE_AUTO
from ha_client import get_numeric_state

logger = logging.getLogger(__name__)


class SolarController:
    def __init__(self, cfg: dict):
        self.cfg          = cfg
        self.hysteresis_w = cfg.get("hysteresis_w", 150)
        self.grid_entity  = cfg["grid_power_entity"]
        self.sensor_stabilize_sec: int = cfg.get("sensor_stabilize_sec", 60)
        self.cycle_log: list[dict] = []

        self.devices: list[BaseDevice] = []
        for dev_cfg in cfg.get("devices", []):
            if not dev_cfg.get("enabled", True):
                logger.info(f"'{dev_cfg['name']}' disabled – skipping.")
                continue
            try:
                device = create_device(dev_cfg, hysteresis_w=self.hysteresis_w)
                self.devices.append(device)
                logger.info(f"[P{device.priority}] {device.name} ({device.device_type}) loaded")
            except Exception as e:
                logger.error(f"Error loading '{dev_cfg.get('name','?')}': {e}")

        self.devices.sort(key=lambda d: d.priority)

    def reload(self, cfg: dict):
        """Reload configuration, preserving manual overrides."""
        overrides = {d.name: d.override for d in self.devices}
        self.__init__(cfg)
        for d in self.devices:
            if d.name in overrides and overrides[d.name] != OVERRIDE_AUTO:
                d.set_override(overrides[d.name])

    def get_device(self, name: str) -> BaseDevice | None:
        return next((d for d in self.devices if d.name == name), None)

    async def get_surplus_w(self) -> float:
        """Read grid power. Positive = export = surplus."""
        return await get_numeric_state(self.grid_entity)

    async def run_cycle(self) -> dict:
        surplus = await self.get_surplus_w()

        # ── Brutto-Überschuss berechnen ───────────────────────────────────────
        # Grid-Sensor ist NETTO: zeigt Überschuss NACH laufenden Verbrauchern.
        #
        # Strategie: Hybridansatz mit Lag-Schutz
        # - Direkt nach Einschalten (< stabilize_sec): _allocated_w nutzen
        #   (Sensor hat noch nicht reagiert → allocated ist zuverlässiger)
        # - Nach Stabilisierung (>= stabilize_sec): consumption_entity nutzen
        #   wenn vorhanden (echte Leistung, z.B. Auto fast voll → weniger als allocated)
        # - Ohne consumption_entity: immer _allocated_w
        STABILIZE_SEC = self.sensor_stabilize_sec
        import time as _time
        running_w = 0.0
        for d in self.devices:
            if not d._active:
                continue
            active_sec = _time.time() - d._active_since if hasattr(d, '_active_since') and d._active_since > 0 else 0
            has_sensor = hasattr(d, 'consumption_entity') and d.consumption_entity and d._actual_consumption_w > 0
            if has_sensor and active_sec >= STABILIZE_SEC:
                # Sensor stabil → minimum aus allocated und sensor (konservativer Ansatz)
                running_w += min(d._allocated_w, d._actual_consumption_w)
            else:
                # Noch nicht stabil oder kein Sensor → allocated nutzen
                running_w += d._allocated_w
        gross_surplus = surplus + running_w
        available = gross_surplus
        results   = []

        for device in self.devices:
            consumed = await device.apply(available)
            available -= consumed
            results.append({
                "name": device.name,
                "consumed_w": round(consumed),
                "available_after_w": round(available),
            })

        allocated = gross_surplus - available

        entry = {
            "surplus_w":   round(surplus, 1),
            "gross_surplus_w": round(gross_surplus, 1),
            "remaining_w": round(surplus, 1),   # Anzeige = Netto-Grid (korrekt)
            "allocated_w": round(allocated, 1),
            "devices":     results,
        }
        self.cycle_log.insert(0, entry)
        self.cycle_log = self.cycle_log[:30]

        return {
            "surplus_w":       round(surplus, 1),
            "gross_surplus_w": round(gross_surplus, 1),
            "remaining_w":     round(surplus, 1),
            "allocated_w":     round(allocated, 1),
            "devices":         [d.status_dict() for d in self.devices],
            "cycle_log":       self.cycle_log[:10],
        }
