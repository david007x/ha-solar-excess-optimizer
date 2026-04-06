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
        # Der Grid-Sensor ist ein NETTO-Wert: er zeigt den Überschuss BEREITS
        # nach Abzug aller laufenden Verbraucher.
        # Um korrekt zu regeln müssen wir den Brutto-Überschuss kennen:
        # Brutto = Netto + Summe aller aktuell laufenden Geräteverbrauche
        # So sieht jedes Gerät im Loop den vollen verfügbaren Überschuss
        # BEVOR seine eigene Leistung abgezogen wird.
        running_consumption = sum(
            d._actual_consumption_w for d in self.devices if d._active
        )
        gross_surplus = surplus + running_consumption
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
