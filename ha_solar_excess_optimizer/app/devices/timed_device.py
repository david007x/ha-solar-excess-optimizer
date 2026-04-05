import time
from datetime import datetime
from devices.base import BaseDevice
from ha_client import turn_on, turn_off, is_on


class TimedDevice(BaseDevice):
    """
    Zeitgesteuert: Gerät läuft täglich mindestens N Minuten.
    Nutzt PV-Überschuss bevorzugt, schaltet aber notfalls auch
    ohne Überschuss ein um die Mindestlaufzeit zu erreichen.
    """

    def __init__(self, cfg: dict, hysteresis_w: int = 150):
        super().__init__(cfg)
        self.switch_entity: str = cfg["switch_entity"]
        self.power_w: int = cfg["power_w"]
        self.min_runtime_min: int = cfg.get("min_runtime_minutes", 60)
        self.hysteresis_w = hysteresis_w

        self._runtime_today_sec: float = 0
        self._session_start: float | None = None
        self._last_reset_day: int = -1
        self._forced: bool = False   # läuft zwangsweise (kein Überschuss mehr)

    def _reset_if_new_day(self):
        today = datetime.now().day
        if today != self._last_reset_day:
            self._runtime_today_sec = 0
            self._last_reset_day = today
            self._forced = False
            self.log("Neuer Tag – Laufzeit zurückgesetzt")

    @property
    def runtime_done(self) -> bool:
        return self._runtime_today_sec >= self.min_runtime_min * 60

    @property
    def runtime_remaining_min(self) -> float:
        remaining = (self.min_runtime_min * 60 - self._runtime_today_sec) / 60
        return max(0, remaining)

    async def apply(self, surplus_w: float) -> float:
        self._reset_if_new_day()
        self._active = await is_on(self.switch_entity)
        now = time.time()

        # Laufzeit akkumulieren
        if self._active and self._session_start:
            self._runtime_today_sec += now - self._session_start
        self._session_start = now if self._active else None

        # Ziel bereits erreicht → ausschalten
        if self.runtime_done and self._active:
            await turn_off(self.switch_entity)
            self._active = False
            self._forced = False
            self.log(f"Ziel erreicht ({self.min_runtime_min} min) → AUS")
            return 0

        # Überschuss vorhanden → einschalten
        if not self._active and not self.runtime_done:
            if surplus_w >= self.power_w + self.hysteresis_w:
                await turn_on(self.switch_entity)
                self._active = True
                self._session_start = now
                self.log(f"EIN via Überschuss (noch {self.runtime_remaining_min:.0f} min nötig)")
                return self.power_w

        # Kein Überschuss aber Ziel noch nicht erreicht + wenig Zeit → Zwang
        hour = datetime.now().hour
        if not self._active and not self.runtime_done and hour >= 20:
            await turn_on(self.switch_entity)
            self._active = True
            self._forced = True
            self._session_start = now
            self.log(f"EIN (Zwang – Abend, noch {self.runtime_remaining_min:.0f} min fehlen)")
            return self.power_w

        # Läuft gerade via Überschuss, aber Überschuss bricht weg
        if self._active and not self._forced and surplus_w < -self.hysteresis_w:
            await turn_off(self.switch_entity)
            self._active = False
            self.log(f"AUS – kein Überschuss mehr (gelaufen: {self._runtime_today_sec/60:.0f} min)")
            return 0

        return self.power_w if self._active else 0

    async def shutdown(self):
        await turn_off(self.switch_entity)
        self._active = False

    def status_dict(self) -> dict:
        self._reset_if_new_day()
        return {
            "name": self.name,
            "type": self.device_type,
            "priority": self.priority,
            "enabled": self.enabled,
            "active": self._active,
            "forced": self._forced,
            "power_w": self.power_w if self._active else 0,
            "runtime_today_min": round(self._runtime_today_sec / 60, 1),
            "runtime_target_min": self.min_runtime_min,
            "runtime_remaining_min": round(self.runtime_remaining_min, 1),
            "runtime_pct": round(min(100, self._runtime_today_sec / max(1, self.min_runtime_min * 60) * 100)),
            "log": self._log,
        }
