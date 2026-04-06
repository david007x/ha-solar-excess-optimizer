"""
wallbox_device.py

Spezieller Gerätetyp für portable Wallboxen die:
- Nur fixe Ladestufen unterstützen (z.B. 6/8/10/13/16A)
- Den Ladestrom NUR im ausgeschalteten Zustand ändern können
- Via Tuya number.* Entity den Ampere-Wert setzen

Ablauf bei Stufenwechsel:
  1. Wallbox ausschalten
  2. Kurz warten (power_cycle_delay_sec)
  3. Neuen Ampere-Wert setzen
  4. Wallbox einschalten
"""
import time
import asyncio
from devices.base import BaseDevice, OVERRIDE_FORCE_ON, OVERRIDE_FORCE_OFF
from ha_client import turn_on, turn_off, is_on, set_number

# Standard Ladestufen für portable Wallboxen (A → W bei 230V)
DEFAULT_STEPS_A = [6, 8, 10, 13, 16]


class WallboxDevice(BaseDevice):

    def __init__(self, cfg: dict, hysteresis_w: int = 150):
        super().__init__(cfg, hysteresis_w)
        self.switch_entity: str  = cfg["switch_entity"]
        self.power_entity: str   = cfg["power_entity"]   # number.* für Ampere
        self.voltage: int        = cfg.get("voltage", 230)
        self.power_cycle_delay: int = cfg.get("power_cycle_delay_sec", 3)
        self.ramp_interval: int  = cfg.get("ramp_interval_sec", 30)

        # Ladestufen: aus Config oder Standard 6/8/10/13/16A
        # Akzeptiert Liste [6,8,10] oder String "6,8,10" (HA Supervisor kompatibel)
        raw = cfg.get("steps_a", DEFAULT_STEPS_A)
        if isinstance(raw, str):
            steps_a = [int(x.strip()) for x in raw.split(",") if x.strip().isdigit()]
        else:
            steps_a = list(raw) if raw else DEFAULT_STEPS_A
        # Sortiert, als (ampere, watt) Paare
        self._steps: list[tuple[int, int]] = sorted(
            [(a, a * self.voltage) for a in steps_a]
        )

        self._current_step: int  = -1   # Index in _steps, -1 = aus
        self._target_step: int   = -1
        self._last_change_time: float = 0
        self._start_time: float  = 0     # Zeitpunkt des Einschaltens
        self._cycling: bool      = False  # True während Ein/Aus-Zyklus läuft
        # Mindestlaufzeit nach dem Einschalten bevor ausgeschaltet werden darf
        # Verhindert Flapping: Wallbox verbraucht Strom → Überschuss sinkt → sofort AUS
        self.min_runtime_sec: int = cfg.get("min_runtime_sec", 120)

    def _watts_to_step(self, surplus_w: float) -> int:
        """Findet die höchste Stufe die der Überschuss deckt. -1 = keine."""
        target = -1
        for i, (_, watts) in enumerate(self._steps):
            if surplus_w >= watts + self.hysteresis_w:
                target = i
        return target

    async def _power_cycle_and_set(self, step: int):
        """
        Schaltet aus, setzt Ampere, schaltet ein.
        Wird als separater Task ausgeführt damit die Regelschleife nicht blockiert.
        """
        self._cycling = True
        try:
            ampere, watts = self._steps[step]
            self.log(f"Zyklus: AUS → {ampere}A ({watts}W) → EIN")

            await turn_off(self.switch_entity)
            await asyncio.sleep(self.power_cycle_delay)
            await set_number(self.power_entity, ampere)
            await asyncio.sleep(0.5)
            await turn_on(self.switch_entity)

            self._current_step = step
            self._active = True
            self._last_change_time = time.time()
            if self._start_time == 0:
                self._start_time = time.time()
            self._record_activation()
            self.log(f"✅ Ladestrom gesetzt: {ampere}A = {watts}W")
        except Exception as e:
            self.log(f"❌ Zyklus-Fehler: {e}")
        finally:
            self._cycling = False

    async def _shutdown_wallbox(self):
        self._cycling = True
        try:
            await turn_off(self.switch_entity)
            self._current_step = -1
            self._active = False
            self._start_time = 0
            self._record_deactivation()
            self._last_change_time = time.time()
            self.log("AUS")
        finally:
            self._cycling = False

    async def apply(self, surplus_w: float) -> float:
        # Während Zyklus läuft: aktuellen Verbrauch zurückgeben, nichts tun
        if self._cycling:
            if self._current_step >= 0:
                return await self.read_consumption(self._steps[self._current_step][1])
            return 0

        self._active = await is_on(self.switch_entity)
        now = time.time()
        ramp_ready = (now - self._last_change_time) >= self.ramp_interval

        # Override
        if self._override == OVERRIDE_FORCE_ON:
            if not self._active or self._current_step < 0:
                asyncio.ensure_future(self._power_cycle_and_set(len(self._steps) - 1))
            return await self.read_consumption(
                self._steps[self._current_step][1] if self._current_step >= 0 else self._steps[-1][1]
            )

        if self._override == OVERRIDE_FORCE_OFF:
            if self._active:
                asyncio.ensure_future(self._shutdown_wallbox())
            return 0

        # Condition prüfen
        self._condition_blocked = not await self.check_condition()
        if self._condition_blocked:
            if self._active:
                asyncio.ensure_future(self._shutdown_wallbox())
            self.log(f"⛔ Bedingung nicht erfüllt: {self.condition_entity}")
            return 0
        else:
            if self.condition_entity:
                self.log(f"✅ Bedingung OK: {self.condition_entity}")

        # Ziel-Stufe berechnen
        new_target = self._watts_to_step(surplus_w)
        min_w = self._steps[0][1] if self._steps else 0
        self.log(
            f"Zyklus │ Überschuss: {surplus_w:.0f}W │ Aktiv: {self._active} │ "
            f"Ziel-Stufe: {new_target} │ Min: {min_w}W+{self.hysteresis_w}W Hysterese"
        )

        # Ausschalten wenn kein Überschuss für Mindeststufe
        if new_target == -1 and self._active:
            _runtime_ok = True
            if hasattr(self, '_min_runtime_ok'):
                _runtime_ok = self._min_runtime_ok()
            elif hasattr(self, '_active_since') and self._active_since > 0:
                _runtime_ok = (time.time() - self._active_since) >= getattr(self, 'min_runtime_sec', 60)
            if self._check_off_delay(True) and ramp_ready and _runtime_ok:
                asyncio.ensure_future(self._shutdown_wallbox())
                self._off_condition_since = None
            return await self.read_consumption(
                self._steps[self._current_step][1] if self._current_step >= 0 else 0
            )
        elif new_target >= 0:
            self._check_off_delay(False)

        # Einschalten wenn genug Überschuss
        if not self._active and new_target >= 0:
            ready = self._check_on_delay(True)
            self.log(
                f"⏳ Einschalt-Timer: {self._on_timer_progress()}% │ "
                f"Timer-bereit: {ready} │ Ramp-bereit: {ramp_ready}"
            )
            if ready and ramp_ready:
                self._on_condition_since = None
                asyncio.ensure_future(self._power_cycle_and_set(new_target))
            return 0
        elif self._active:
            self._check_on_delay(False)

        # Stufenwechsel (nur wenn Wallbox läuft + Ramp-Intervall abgelaufen)
        if self._active and new_target != self._current_step and ramp_ready:
            direction = "▲" if new_target > self._current_step else "▼"
            a_new, w_new = self._steps[new_target] if new_target >= 0 else (0, 0)
            self.log(f"{direction} Stufenwechsel → {a_new}A ({w_new}W)")
            asyncio.ensure_future(self._power_cycle_and_set(new_target))

        # Aktuellen Verbrauch zurückgeben
        if not self._active or self._current_step < 0:
            return 0
        return await self.read_consumption(self._steps[self._current_step][1])

    async def shutdown(self):
        await turn_off(self.switch_entity)
        self._active = False
        self._current_step = -1

    def status_dict(self) -> dict:
        current_a = self._steps[self._current_step][0] if self._current_step >= 0 else 0
        current_w = self._steps[self._current_step][1] if self._current_step >= 0 else 0
        return {
            **self._base_status(),
            "power_w": round(self._actual_consumption_w) if self._active else 0,
            "current_ampere": current_a,
            "current_step": self._current_step + 1,
            "total_steps": len(self._steps),
            "steps": [{"ampere": a, "watt": w} for a, w in self._steps],
            "cycling": self._cycling,
            "runtime_sec": round(time.time() - self._start_time) if self._start_time > 0 else 0,
            "min_runtime_sec": self.min_runtime_sec,
            "power_pct": round(self._current_step / max(1, len(self._steps) - 1) * 100)
                         if self._current_step >= 0 else 0,
        }
