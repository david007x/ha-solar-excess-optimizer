import logging
from devices.factory import create_device
from devices.base import BaseDevice, OVERRIDE_AUTO
from ha_client import get_numeric_state

logger = logging.getLogger(__name__)


class SolarController:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.hysteresis_w: int  = cfg.get("hysteresis_w", 150)
        self.grid_entity: str   = cfg["grid_power_entity"]

        # Batterie-Konfiguration
        self.battery_soc_entity: str | None = cfg.get("battery_soc_entity")
        self.battery_min_soc: int           = cfg.get("battery_min_soc", 0)
        # Priorität der Batterie: Geräte mit priority > battery_priority werden
        # erst aktiviert wenn Batterie >= battery_min_soc
        self.battery_priority: int          = cfg.get("battery_priority", 0)

        self.cycle_log: list[dict] = []

        self.devices: list[BaseDevice] = []
        for dev_cfg in cfg.get("devices", []):
            if not dev_cfg.get("enabled", True):
                logger.info(f"'{dev_cfg['name']}' deaktiviert – übersprungen.")
                continue
            try:
                device = create_device(dev_cfg, hysteresis_w=self.hysteresis_w)
                self.devices.append(device)
                logger.info(f"[P{device.priority}] {device.name} ({device.device_type}) geladen")
            except Exception as e:
                logger.error(f"Fehler bei '{dev_cfg.get('name','?')}': {e}")

        self.devices.sort(key=lambda d: d.priority)

    def reload(self, cfg: dict):
        # Override-Zustände vor Reload sichern
        overrides = {d.name: d.override for d in self.devices}
        self.__init__(cfg)
        # Overrides wiederherstellen
        for d in self.devices:
            if d.name in overrides and overrides[d.name] != OVERRIDE_AUTO:
                d.set_override(overrides[d.name])

    def get_device(self, name: str) -> BaseDevice | None:
        return next((d for d in self.devices if d.name == name), None)

    async def get_surplus_w(self) -> float:
        return await get_numeric_state(self.grid_entity)

    async def get_battery_soc(self) -> float | None:
        if not self.battery_soc_entity:
            return None
        return await get_numeric_state(self.battery_soc_entity)

    async def run_cycle(self) -> dict:
        surplus   = await self.get_surplus_w()
        battery   = await self.get_battery_soc()
        available = surplus
        results   = []

        # Batterie-Info für Dashboard
        battery_ok = True
        if battery is not None and self.battery_min_soc > 0:
            battery_ok = battery >= self.battery_min_soc

        for device in self.devices:
            # Batterie-Sperre: Geräte mit priority > battery_priority warten
            # bis Batterie geladen genug ist (außer bei manuellem Override)
            from devices.base import OVERRIDE_AUTO
            battery_blocked = (
                not battery_ok
                and device.priority > self.battery_priority
                and device.override == OVERRIDE_AUTO
            )

            if battery_blocked:
                results.append({
                    "name": device.name,
                    "consumed_w": 0,
                    "available_after_w": round(available),
                    "blocked": "battery",
                })
                device.log(f"Warte auf Batterie ({battery:.0f}% < {self.battery_min_soc}%)")
                continue

            consumed = await device.apply(available)
            available -= consumed
            results.append({
                "name": device.name,
                "consumed_w": round(consumed),
                "available_after_w": round(available),
                "blocked": None,
            })

        entry = {"surplus_w": round(surplus, 1), "remaining_w": round(available, 1), "devices": results}
        self.cycle_log.insert(0, entry)
        self.cycle_log = self.cycle_log[:30]

        return {
            "surplus_w":   round(surplus, 1),
            "remaining_w": round(available, 1),
            "battery_soc": round(battery, 1) if battery is not None else None,
            "battery_ok":  battery_ok,
            "battery_min_soc": self.battery_min_soc,
            "devices":     [d.status_dict() for d in self.devices],
            "cycle_log":   self.cycle_log[:10],
        }
