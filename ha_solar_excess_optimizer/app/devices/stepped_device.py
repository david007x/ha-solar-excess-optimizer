from devices.base import BaseDevice
from ha_client import turn_on, turn_off, is_on


class SteppedDevice(BaseDevice):
    """
    Gerät mit mehreren fixen Leistungsstufen (z.B. Heizstab 1/2/3 kW).
    Jede Stufe hat einen eigenen Switch-Entity.
    Es ist immer max. eine Stufe aktiv.
    """

    def __init__(self, cfg: dict, hysteresis_w: int = 150):
        super().__init__(cfg)
        self.hysteresis_w = hysteresis_w
        # Stufen nach Leistung sortieren
        self.steps: list[dict] = sorted(cfg["steps"], key=lambda s: s["power_w"])
        self._current_step: int = -1  # -1 = aus

    async def apply(self, surplus_w: float) -> float:
        # Höchste Stufe finden, die der Überschuss noch deckt
        target_step = -1
        for i, step in enumerate(self.steps):
            if surplus_w >= step["power_w"] + self.hysteresis_w:
                target_step = i

        if target_step == self._current_step:
            # Keine Änderung
            return self.steps[self._current_step]["power_w"] if self._current_step >= 0 else 0

        # Alle Stufen ausschalten
        for step in self.steps:
            await turn_off(step["switch_entity"])

        if target_step >= 0:
            step = self.steps[target_step]
            await turn_on(step["switch_entity"])
            self._active = True
            self.log(f"Stufe {target_step + 1} EIN → {step['power_w']}W")
        else:
            self._active = False
            self.log(f"AUS – kein Überschuss für Mindeststufe ({self.steps[0]['power_w']}W)")

        self._current_step = target_step
        return self.steps[target_step]["power_w"] if target_step >= 0 else 0

    async def shutdown(self):
        for step in self.steps:
            await turn_off(step["switch_entity"])
        self._current_step = -1
        self._active = False

    def status_dict(self) -> dict:
        current_power = self.steps[self._current_step]["power_w"] if self._current_step >= 0 else 0
        return {
            "name": self.name,
            "type": self.device_type,
            "priority": self.priority,
            "enabled": self.enabled,
            "active": self._active,
            "power_w": current_power,
            "current_step": self._current_step + 1,
            "total_steps": len(self.steps),
            "steps": [s["power_w"] for s in self.steps],
            "log": self._log,
        }
