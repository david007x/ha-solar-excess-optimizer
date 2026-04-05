from devices.base import BaseDevice, OVERRIDE_FORCE_ON, OVERRIDE_FORCE_OFF
from ha_client import turn_on, turn_off, is_on


class SwitchDevice(BaseDevice):
    """Einfaches An/Aus Gerät mit zeitbasierter Hysterese und Override."""

    def __init__(self, cfg: dict, hysteresis_w: int = 150):
        super().__init__(cfg, hysteresis_w)
        self.switch_entity: str = cfg["switch_entity"]
        self.power_w: int = cfg["power_w"]

    async def apply(self, surplus_w: float) -> float:
        self._active = await is_on(self.switch_entity)

        # Force Override
        if self._override == OVERRIDE_FORCE_ON:
            if not self._active:
                await turn_on(self.switch_entity)
                self._active = True
                self.log("EIN (Override: force_on)")
            return self.power_w

        if self._override == OVERRIDE_FORCE_OFF:
            if self._active:
                await turn_off(self.switch_entity)
                self._active = False
                self.log("AUS (Override: force_off)")
            return 0

        # Automatische Regelung mit zeitbasierter Hysterese
        if not self._active:
            should_on = surplus_w >= self.power_w + self.hysteresis_w
            if self._check_on_delay(should_on):
                await turn_on(self.switch_entity)
                self._active = True
                self._on_condition_since = None
                self.log(f"EIN – Überschuss {surplus_w:.0f}W stabil ≥ {self.power_w}W")
        else:
            should_off = surplus_w < -self.hysteresis_w
            if self._check_off_delay(should_off):
                await turn_off(self.switch_entity)
                self._active = False
                self._off_condition_since = None
                self.log(f"AUS – Überschuss {surplus_w:.0f}W zu gering")

        return self.power_w if self._active else 0

    async def shutdown(self):
        await turn_off(self.switch_entity)
        self._active = False

    def status_dict(self) -> dict:
        return {
            **self._base_status(),
            "power_w": self.power_w if self._active else 0,
            "config_power_w": self.power_w,
        }
