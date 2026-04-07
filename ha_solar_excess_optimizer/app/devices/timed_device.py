import time
from datetime import datetime
from devices.base import BaseDevice, OVERRIDE_FORCE_ON, OVERRIDE_FORCE_OFF
from ha_client import turn_on, turn_off, is_on


class TimedDevice(BaseDevice):
    """Timed device: minimum runtime per day, using PV surplus preferably."""

    def __init__(self, cfg: dict, hysteresis_w: int = 150):
        super().__init__(cfg, hysteresis_w)
        self.switch_entity: str   = cfg["switch_entity"]
        self.power_w: int         = cfg["power_w"]
        self.min_runtime_min: int = cfg.get("min_runtime_minutes", 60)
        self._runtime_today_sec: float    = 0
        self._session_start: float | None = None
        self._last_reset_day: int         = -1
        self._forced: bool                = False

    def _reset_if_new_day(self):
        today = datetime.now().day
        if today != self._last_reset_day:
            self._runtime_today_sec = 0
            self._last_reset_day = today
            self._forced = False

    @property
    def runtime_done(self) -> bool:
        return self._runtime_today_sec >= self.min_runtime_min * 60

    @property
    def runtime_remaining_min(self) -> float:
        return max(0, (self.min_runtime_min * 60 - self._runtime_today_sec) / 60)

    async def apply(self, surplus_w: float) -> float:
        self._reset_if_new_day()
        self._active = await is_on(self.switch_entity)
        now = time.time()
        if self._active and self._session_start:
            self._runtime_today_sec += now - self._session_start
        self._session_start = now if self._active else None

        if self._override == OVERRIDE_FORCE_ON:
            if not self._active:
                await turn_on(self.switch_entity)
                self._active = True
                self._session_start = now
                self.log("ON (override)")
            return await self.read_consumption(self.power_w)

        if self._override == OVERRIDE_FORCE_OFF:
            if self._active:
                await turn_off(self.switch_entity)
                self._active = False
                self.log("OFF (override)")
            return 0

        self._condition_blocked = not await self.check_condition()
        if self._condition_blocked:
            if self._active:
                await turn_off(self.switch_entity)
                self._active = False
                self.log("OFF – condition not met")
            return 0

        if self.runtime_done and self._active:
            await turn_off(self.switch_entity)
            self._active = False
            self._forced = False
            self.log(f"Daily target reached ({self.min_runtime_min} min)")
            return 0

        if not self._active and not self.runtime_done:
            if self._check_on_delay(surplus_w >= self.power_w + self.hysteresis_w):
                await turn_on(self.switch_entity)
                self._active = True
                self._session_start = now
                self._on_condition_since = None
                self.log(f"ON via surplus ({self.runtime_remaining_min:.0f} min remaining)")
                return await self.read_consumption(self.power_w)

        if not self._active and not self.runtime_done and datetime.now().hour >= 20:
            await turn_on(self.switch_entity)
            self._active = True
            self._forced = True
            self._session_start = now
            self.log(f"ON forced ({self.runtime_remaining_min:.0f} min missing)")
            return await self.read_consumption(self.power_w)

        if self._active and not self._forced:
            if self._check_off_delay(surplus_w < -self.hysteresis_w):
                await turn_off(self.switch_entity)
                self._active = False
                self._off_condition_since = None
                self.log("OFF – no surplus")
                return 0

        if not self._active:
            return 0
        await self.read_consumption(self.power_w)  # nur Anzeige
        return self.power_w

    async def shutdown(self):
        await turn_off(self.switch_entity)
        self._active = False

    def status_dict(self) -> dict:
        self._reset_if_new_day()
        return {
            **self._base_status(),
            "forced":               self._forced,
            "power_w":              round(self._actual_consumption_w) if self._active else 0,
            "config_power_w":       self.power_w,
            "runtime_today_min":    round(self._runtime_today_sec / 60, 1),
            "runtime_target_min":   self.min_runtime_min,
            "runtime_remaining_min": round(self.runtime_remaining_min, 1),
            "runtime_pct":          round(min(100, self._runtime_today_sec /
                                          max(1, self.min_runtime_min * 60) * 100)),
        }
