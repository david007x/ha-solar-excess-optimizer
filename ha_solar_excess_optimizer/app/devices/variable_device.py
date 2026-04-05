import asyncio
import time
from devices.base import BaseDevice
from ha_client import turn_on, turn_off, is_on, set_number, get_numeric_state


class VariableDevice(BaseDevice):
    """
    Stufenlose Leistungsregelung via HA number.* Entity (z.B. Wallbox Ampere).
    Passt die Leistung schrittweise an den verfügbaren Überschuss an.
    """

    def __init__(self, cfg: dict, hysteresis_w: int = 150):
        super().__init__(cfg)
        self.switch_entity: str = cfg["switch_entity"]
        self.power_entity: str = cfg["power_entity"]       # z.B. number.wallbox_current_ampere
        self.power_min: int = cfg.get("power_min", 1400)
        self.power_max: int = cfg.get("power_max", 11000)
        self.power_step: int = cfg.get("power_step", 230)  # Schrittgröße in W
        self.ramp_interval: int = cfg.get("ramp_interval_sec", 30)
        self.hysteresis_w = hysteresis_w
        self._current_power_w: float = 0
        self._last_ramp_time: float = 0

    async def apply(self, surplus_w: float) -> float:
        self._active = await is_on(self.switch_entity)
        now = time.time()
        ramp_ready = (now - self._last_ramp_time) >= self.ramp_interval

        # Einschalten wenn genug Überschuss
        if not self._active:
            if surplus_w >= self.power_min + self.hysteresis_w:
                await turn_on(self.switch_entity)
                self._active = True
                self._current_power_w = self.power_min
                await self._set_power(self.power_min)
                self.log(f"EIN – starte mit {self.power_min}W")
                self._last_ramp_time = now
            return 0

        # Ausschalten wenn zu wenig Überschuss für Minimum
        if surplus_w < -self.hysteresis_w and self._current_power_w <= self.power_min:
            await turn_off(self.switch_entity)
            self._active = False
            self._current_power_w = 0
            self.log(f"AUS – Überschuss {surplus_w:.0f}W zu gering")
            return 0

        # Leistung anpassen (Rate-Limit via ramp_interval)
        if ramp_ready:
            target = self._current_power_w + surplus_w
            target = max(self.power_min, min(self.power_max, target))
            # Auf Schrittgröße runden
            target = round(target / self.power_step) * self.power_step
            target = max(self.power_min, min(self.power_max, target))

            if abs(target - self._current_power_w) >= self.power_step:
                self.log(f"Regelung: {self._current_power_w:.0f}W → {target:.0f}W (Δ{surplus_w:+.0f}W)")
                self._current_power_w = target
                await self._set_power(target)
                self._last_ramp_time = now

        return self._current_power_w

    async def _set_power(self, power_w: float):
        """Konvertiert Watt → Ampere und setzt number Entity."""
        ampere = round(power_w / 230)
        await set_number(self.power_entity, ampere)

    async def shutdown(self):
        await turn_off(self.switch_entity)
        self._current_power_w = 0
        self._active = False

    def status_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.device_type,
            "priority": self.priority,
            "enabled": self.enabled,
            "active": self._active,
            "power_w": round(self._current_power_w),
            "power_min": self.power_min,
            "power_max": self.power_max,
            "power_pct": round((self._current_power_w - self.power_min) /
                               max(1, self.power_max - self.power_min) * 100),
            "log": self._log,
        }
