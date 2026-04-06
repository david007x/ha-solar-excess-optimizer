from devices.base import BaseDevice, OVERRIDE_FORCE_ON, OVERRIDE_FORCE_OFF
from ha_client import turn_on, turn_off, is_on


class SwitchDevice(BaseDevice):

    def __init__(self, cfg: dict, hysteresis_w: int = 150):
        super().__init__(cfg, hysteresis_w)
        self.switch_entity: str = cfg["switch_entity"]
        self.power_w: int       = cfg["power_w"]

    async def apply(self, surplus_w: float) -> float:
        self._active = await is_on(self.switch_entity)

        # Override ignoriert condition_entity
        if self._override == OVERRIDE_FORCE_ON:
            if not self._active:
                await turn_on(self.switch_entity)
                self._active = True
                self.log("EIN (Override: force_on)")
            return await self.read_consumption(self.power_w)

        if self._override == OVERRIDE_FORCE_OFF:
            if self._active:
                await turn_off(self.switch_entity)
                self._active = False
                self.log("AUS (Override: force_off)")
            return 0

        # Condition prüfen
        self._condition_blocked = not await self.check_condition()
        if self._condition_blocked:
            if self._active:
                await turn_off(self.switch_entity)
                self._active = False
                self.log(f"AUS – Bedingung nicht erfüllt ({self.condition_entity})")
            return 0

        # Regelung mit zeitbasierter Hysterese
        if not self._active:
            if self._check_on_delay(surplus_w >= self.power_w + self.hysteresis_w):
                await turn_on(self.switch_entity)
                self._active = True
                self._on_condition_since = None
                self.log(f"EIN – Überschuss {surplus_w:.0f}W")
        else:
            if self._check_off_delay(surplus_w < -self.hysteresis_w):
                await turn_off(self.switch_entity)
                self._active = False
                self._off_condition_since = None
                self.log(f"AUS – Überschuss {surplus_w:.0f}W zu gering")

        if not self._active:
            return 0
        return await self.read_consumption(self.power_w)

    async def shutdown(self):
        await turn_off(self.switch_entity)
        self._active = False

    def status_dict(self) -> dict:
        return {**self._base_status(), "power_w": self._actual_consumption_w if self._active else 0, "config_power_w": self.power_w}
