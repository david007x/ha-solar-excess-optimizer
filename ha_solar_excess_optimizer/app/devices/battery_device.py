from devices.base import BaseDevice, OVERRIDE_FORCE_ON, OVERRIDE_FORCE_OFF
from ha_client import get_numeric_state


class BatteryDevice(BaseDevice):
    """
    Battery as a modular device type.

    Logic:
    - Reads current SOC via soc_entity
    - While SOC < target_soc: reserves surplus for battery charging
      (up to max_charge_power_w) → less available for lower-priority devices
    - Once SOC >= target_soc: passes full surplus downstream
    - No direct switching – battery charges automatically via inverter
      we only model the power budget consumption
    """

    def __init__(self, cfg: dict, hysteresis_w: int = 150):
        super().__init__(cfg, hysteresis_w)
        self.soc_entity: str            = cfg["soc_entity"]
        self.power_entity: str | None   = cfg.get("power_entity")
        self.target_soc: int            = cfg.get("target_soc", 100)
        self.max_charge_power_w: int    = cfg.get("max_charge_power_w", 5000)

        self._soc: float          = 0.0
        self._charge_power: float = 0.0

    async def apply(self, surplus_w: float) -> float:
        self._soc = await get_numeric_state(self.soc_entity)

        if self.power_entity:
            self._charge_power = await get_numeric_state(self.power_entity)

        if self._override == OVERRIDE_FORCE_OFF:
            self._active = False
            self.log("Battery reservation disabled (override: force_off)")
            return 0

        if self._soc >= self.target_soc:
            if self._active:
                self._active = False
                self.log(f"Target SOC {self.target_soc}% reached – surplus released")
            return 0

        # Reserve surplus proportionally (full power until 20% below target)
        remaining_pct = self.target_soc - self._soc
        scale = min(1.0, remaining_pct / 20.0)
        reserved = min(surplus_w, self.max_charge_power_w * scale)
        reserved = max(0, reserved)

        if reserved > 0:
            self._active = True
            self.log(f"Charging – SOC {self._soc:.0f}% → target {self.target_soc}% | reserved {reserved:.0f}W")
        else:
            self._active = False

        self._actual_consumption_w = reserved
        return reserved

    async def shutdown(self):
        self._active = False

    def status_dict(self) -> dict:
        return {
            **self._base_status(),
            "power_w":           round(self._charge_power) if self._charge_power else 0,
            "soc":               round(self._soc, 1),
            "target_soc":        self.target_soc,
            "max_charge_power_w": self.max_charge_power_w,
            "soc_pct":           round(self._soc),
            "target_pct":        self.target_soc,
        }
