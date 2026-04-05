from devices.base import BaseDevice, OVERRIDE_FORCE_ON, OVERRIDE_FORCE_OFF
from ha_client import turn_on, turn_off, is_on


class SteppedDevice(BaseDevice):
    """Mehrere fixe Leistungsstufen mit zeitbasierter Hysterese und Override."""

    def __init__(self, cfg: dict, hysteresis_w: int = 150):
        super().__init__(cfg, hysteresis_w)
        self.steps: list[dict] = sorted(cfg["steps"], key=lambda s: s["power_w"])
        self._current_step: int = -1
        self._target_step: int = -1

    async def apply(self, surplus_w: float) -> float:
        # Override
        if self._override == OVERRIDE_FORCE_ON:
            if self._current_step != len(self.steps) - 1:
                await self._activate_step(len(self.steps) - 1)
                self.log("Maximalleistung (Override: force_on)")
            return self.steps[self._current_step]["power_w"] if self._current_step >= 0 else 0

        if self._override == OVERRIDE_FORCE_OFF:
            if self._current_step >= 0:
                await self._deactivate()
                self.log("AUS (Override: force_off)")
            return 0

        # Zielstufe berechnen
        new_target = -1
        for i, step in enumerate(self.steps):
            if surplus_w >= step["power_w"] + self.hysteresis_w:
                new_target = i

        # Stufenwechsel mit Verzögerung
        if new_target != self._target_step:
            self._target_step = new_target
            self._on_condition_since = None
            self._off_condition_since = None

        if new_target > self._current_step:
            if self._check_on_delay(True):
                await self._activate_step(new_target)
                self._on_condition_since = None
        elif new_target < self._current_step:
            if self._check_off_delay(True):
                await self._activate_step(new_target)
                self._off_condition_since = None
        else:
            self._check_on_delay(False)
            self._check_off_delay(False)

        return self.steps[self._current_step]["power_w"] if self._current_step >= 0 else 0

    async def _activate_step(self, step: int):
        for s in self.steps:
            await turn_off(s["switch_entity"])
        if step >= 0:
            await turn_on(self.steps[step]["switch_entity"])
            self._active = True
            self.log(f"Stufe {step + 1} → {self.steps[step]['power_w']}W")
        else:
            self._active = False
            self.log("AUS")
        self._current_step = step

    async def _deactivate(self):
        await self._activate_step(-1)

    async def shutdown(self):
        await self._deactivate()

    def status_dict(self) -> dict:
        current_power = self.steps[self._current_step]["power_w"] if self._current_step >= 0 else 0
        return {
            **self._base_status(),
            "power_w": current_power,
            "current_step": self._current_step + 1,
            "total_steps": len(self.steps),
            "steps": [s["power_w"] for s in self.steps],
        }
