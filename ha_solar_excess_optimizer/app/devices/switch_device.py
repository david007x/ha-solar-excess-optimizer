from devices.base import BaseDevice
from ha_client import turn_on, turn_off, is_on


class SwitchDevice(BaseDevice):
    """
    Einfaches An/Aus Gerät.
    Einschalten wenn Überschuss >= power_w + hysterese,
    ausschalten wenn Überschuss < power_w.
    """

    def __init__(self, cfg: dict, hysteresis_w: int = 150):
        super().__init__(cfg)
        self.switch_entity: str = cfg["switch_entity"]
        self.power_w: int = cfg["power_w"]
        self.hysteresis_w = hysteresis_w

    async def apply(self, surplus_w: float) -> float:
        self._active = await is_on(self.switch_entity)

        if not self._active and surplus_w >= self.power_w + self.hysteresis_w:
            await turn_on(self.switch_entity)
            self._active = True
            self.log(f"EIN – Überschuss {surplus_w:.0f}W ≥ {self.power_w}W")
            return self.power_w

        if self._active and surplus_w < -self.hysteresis_w:
            await turn_off(self.switch_entity)
            self._active = False
            self.log(f"AUS – Überschuss {surplus_w:.0f}W zu gering")
            return 0

        return self.power_w if self._active else 0

    async def shutdown(self):
        await turn_off(self.switch_entity)
        self._active = False

    def status_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.device_type,
            "priority": self.priority,
            "enabled": self.enabled,
            "active": self._active,
            "power_w": self.power_w if self._active else 0,
            "config_power_w": self.power_w,
            "log": self._log,
        }
