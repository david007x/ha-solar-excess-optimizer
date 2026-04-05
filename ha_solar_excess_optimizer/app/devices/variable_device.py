import time
from devices.base import BaseDevice, OVERRIDE_FORCE_ON, OVERRIDE_FORCE_OFF
from ha_client import turn_on, turn_off, is_on, set_number


class VariableDevice(BaseDevice):
    """Stufenlose Leistungsregelung mit Hysterese, Rampe und Override."""

    def __init__(self, cfg: dict, hysteresis_w: int = 150):
        super().__init__(cfg, hysteresis_w)
        self.switch_entity: str = cfg["switch_entity"]
        self.power_entity: str  = cfg["power_entity"]
        self.power_min: int     = cfg.get("power_min", 1400)
        self.power_max: int     = cfg.get("power_max", 11000)
        self.power_step: int    = cfg.get("power_step", 230)
        self.ramp_interval: int = cfg.get("ramp_interval_sec", 30)
        self._current_power_w: float = 0
        self._last_ramp_time: float  = 0

    async def apply(self, surplus_w: float) -> float:
        self._active = await is_on(self.switch_entity)
        now = time.time()
        ramp_ready = (now - self._last_ramp_time) >= self.ramp_interval

        # Override
        if self._override == OVERRIDE_FORCE_ON:
            if not self._active:
                await turn_on(self.switch_entity)
                self._active = True
                self._current_power_w = self.power_max
                await self._set_power(self.power_max)
                self.log(f"EIN mit Max {self.power_max}W (Override)")
            return self._current_power_w

        if self._override == OVERRIDE_FORCE_OFF:
            if self._active:
                await turn_off(self.switch_entity)
                self._active = False
                self._current_power_w = 0
                self.log("AUS (Override)")
            return 0

        # Einschalten mit Verzögerung
        if not self._active:
            should_on = surplus_w >= self.power_min + self.hysteresis_w
            if self._check_on_delay(should_on):
                await turn_on(self.switch_entity)
                self._active = True
                self._current_power_w = self.power_min
                await self._set_power(self.power_min)
                self._on_condition_since = None
                self._last_ramp_time = now
                self.log(f"EIN mit Min {self.power_min}W")
            return 0

        # Ausschalten mit Verzögerung
        should_off = surplus_w < -self.hysteresis_w and self._current_power_w <= self.power_min
        if self._check_off_delay(should_off):
            await turn_off(self.switch_entity)
            self._active = False
            self._current_power_w = 0
            self._off_condition_since = None
            self.log("AUS – zu wenig Überschuss")
            return 0
        elif not should_off:
            self._check_off_delay(False)

        # Leistung anpassen (Rate-Limit)
        if ramp_ready and self._active:
            target = self._current_power_w + surplus_w
            target = round(target / self.power_step) * self.power_step
            target = max(self.power_min, min(self.power_max, target))
            if abs(target - self._current_power_w) >= self.power_step:
                self.log(f"Regelung: {self._current_power_w:.0f}W → {target:.0f}W")
                self._current_power_w = target
                await self._set_power(target)
                self._last_ramp_time = now

        return self._current_power_w

    async def _set_power(self, power_w: float):
        await set_number(self.power_entity, round(power_w / 230))

    async def shutdown(self):
        await turn_off(self.switch_entity)
        self._current_power_w = 0
        self._active = False

    def status_dict(self) -> dict:
        return {
            **self._base_status(),
            "power_w": round(self._current_power_w),
            "power_min": self.power_min,
            "power_max": self.power_max,
            "power_pct": round((self._current_power_w - self.power_min) /
                               max(1, self.power_max - self.power_min) * 100)
                         if self._active else 0,
        }
