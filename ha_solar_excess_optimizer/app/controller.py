import logging
from devices.factory import create_device
from devices.base import BaseDevice
from ha_client import get_numeric_state

logger = logging.getLogger(__name__)


class SolarController:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.hysteresis_w: int = cfg.get("hysteresis_w", 150)
        self.grid_entity: str = cfg["grid_power_entity"]
        self.cycle_log: list[dict] = []

        # Geräte instanziieren, deaktivierte überspringen, nach Priorität sortieren
        self.devices: list[BaseDevice] = []
        for dev_cfg in cfg.get("devices", []):
            if not dev_cfg.get("enabled", True):
                logger.info(f"Gerät '{dev_cfg['name']}' deaktiviert – übersprungen.")
                continue
            try:
                device = create_device(dev_cfg, hysteresis_w=self.hysteresis_w)
                self.devices.append(device)
                logger.info(f"Gerät geladen: [{device.priority}] {device.name} ({device.device_type})")
            except Exception as e:
                logger.error(f"Fehler beim Laden von '{dev_cfg.get('name', '?')}': {e}")

        self.devices.sort(key=lambda d: d.priority)

    def reload(self, cfg: dict):
        """Konfiguration neu laden (nach Web UI Änderung)."""
        logger.info("Konfiguration wird neu geladen...")
        self.__init__(cfg)

    async def get_surplus_w(self) -> float:
        """Netzleistung lesen. Positiv = Einspeisung = Überschuss."""
        return await get_numeric_state(self.grid_entity)

    async def run_cycle(self) -> dict:
        surplus = await self.get_surplus_w()
        available = surplus
        results = []

        # Regelung: Geräte nach Priorität abarbeiten
        for device in self.devices:
            consumed = await device.apply(available)
            available -= consumed
            results.append({
                "name": device.name,
                "consumed_w": round(consumed),
                "available_after_w": round(available),
            })
            logger.debug(f"{device.name}: {consumed:.0f}W verbraucht, "
                         f"verbleibend: {available:.0f}W")

        entry = {
            "surplus_w": round(surplus, 1),
            "remaining_w": round(available, 1),
            "devices": results,
        }
        self.cycle_log.insert(0, entry)
        self.cycle_log = self.cycle_log[:30]

        return {
            "surplus_w": round(surplus, 1),
            "remaining_w": round(available, 1),
            "devices": [d.status_dict() for d in self.devices],
            "cycle_log": self.cycle_log[:10],
        }
