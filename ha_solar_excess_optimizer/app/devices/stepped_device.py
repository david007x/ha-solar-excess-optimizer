from devices.base import BaseDevice, OVERRIDE_FORCE_ON, OVERRIDE_FORCE_OFF
from ha_client import turn_on, turn_off


class SteppedDevice(BaseDevice):
    """Multiple fixed power levels with time-based hysteresis and override."""

    def __init__(self, cfg: dict, hysteresis_w: int = 150):
        super().__init__(cfg, hysteresis_w)
        self.steps: list[dict] = sorted(cfg["steps"], key=lambda s: s["power_w"])
        self._current_step: int = -1
        self._target_step: int  = -1

    async def apply(self, surplus_w: float) -> float:
        if self._override == OVERRIDE_FORCE_ON:
            await self._activate_step(len(self.steps) - 1)
            return await self.read_consumption(self.steps[-1]["power_w"])

        if self._override == OVERRIDE_FORCE_OFF:
            await self._deactivate()
            return 0

        self._condition_blocked = not await self.check_condition()
        if self._condition_blocked:
            await self._deactivate()
            return 0

        # Bidirektionale Hysterese:
        # - Hochschalten zu Stufe i: surplus >= power_w + hysteresis
        # - Halten / Runterschalten: surplus >= power_w - hysteresis
        new_target = -1
        for i, step in enumerate(self.steps):
            threshold = (
                step["power_w"] - self.hysteresis_w
                if i <= self._current_step
                else step["power_w"] + self.hysteresis_w
            )
            if surplus_w >= threshold:
                new_target = i

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

        if self._current_step < 0:
            return 0
        await self.read_consumption(self.steps[self._current_step]["power_w"])
        return self.steps[self._current_step]["power_w"]

    async def _activate_step(self, step: int):
        was_active = self._active
        for s in self.steps:
            await turn_off(s["switch_entity"])
        if step >= 0:
            await turn_on(self.steps[step]["switch_entity"])
            self._active = True
            self._allocated_w = self.steps[step]["power_w"]
            if not was_active:
                self._record_activation()
            self.log(f"Step {step+1} → {self.steps[step]['power_w']}W")
        else:
            self._active = False
            self._allocated_w = 0
            if was_active:
                self._record_deactivation()
            self.log("OFF")
        self._current_step = step

    async def _deactivate(self):
        await self._activate_step(-1)

    async def shutdown(self):
        await self._deactivate()

    def status_dict(self) -> dict:
        pw = self.steps[self._current_step]["power_w"] if self._current_step >= 0 else 0
        return {**self._base_status(),
                "power_w": self._actual_consumption_w if self._active else 0,
                "config_power_w": pw,
                "current_step": self._current_step + 1,
                "total_steps": len(self.steps),
                "steps": [s["power_w"] for s in self.steps]}
