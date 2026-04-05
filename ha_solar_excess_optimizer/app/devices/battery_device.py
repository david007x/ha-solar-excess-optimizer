from devices.base import BaseDevice, OVERRIDE_FORCE_ON, OVERRIDE_FORCE_OFF
from ha_client import get_numeric_state


class BatteryDevice(BaseDevice):
    """
    Batterie als modularer Gerätetyp.

    Logik:
    - Liest aktuellen SOC via soc_entity
    - Solange SOC < target_soc: reserviert Überschuss für Batterie
      (bis max_charge_power_w) → weniger bleibt für nachfolgende Geräte
    - Sobald SOC >= target_soc: gibt den vollen Überschuss weiter
    - Keine direkte Schaltung – Batterie lädt automatisch via Wechselrichter
      wir modellieren nur den Verbrauch im Leistungsbudget

    Optionale Felder:
    - power_entity: aktuell fließende Ladeleistung (W) – für Anzeige
    - discharge_entity: Entladeleistung (W) – für Anzeige
    """

    def __init__(self, cfg: dict, hysteresis_w: int = 150):
        super().__init__(cfg, hysteresis_w)
        self.soc_entity: str            = cfg["soc_entity"]
        self.power_entity: str | None   = cfg.get("power_entity")
        self.target_soc: int            = cfg.get("target_soc", 100)
        self.max_charge_power_w: int    = cfg.get("max_charge_power_w", 5000)

        self._soc: float        = 0.0
        self._charge_power: float = 0.0

    async def apply(self, surplus_w: float) -> float:
        # SOC lesen
        self._soc = await get_numeric_state(self.soc_entity)

        # Aktuelle Ladeleistung lesen (optional, nur für Anzeige)
        if self.power_entity:
            self._charge_power = await get_numeric_state(self.power_entity)

        # Override
        if self._override == OVERRIDE_FORCE_OFF:
            self._active = False
            self.log("Batterie-Reservierung deaktiviert (Override: force_off)")
            return 0

        # Ziel bereits erreicht → kein Überschuss reservieren
        if self._soc >= self.target_soc:
            if self._active:
                self._active = False
                self.log(f"Ziel-SOC {self.target_soc}% erreicht – Überschuss freigegeben")
            return 0

        # Noch nicht voll → Überschuss für Batterie reservieren
        remaining_capacity_pct = self.target_soc - self._soc
        # Je weniger Kapazität fehlt, desto weniger Leistung reservieren (linear)
        scale = min(1.0, remaining_capacity_pct / 20.0)  # volle Leistung bis 20% unter Ziel
        reserved = min(surplus_w, self.max_charge_power_w * scale)
        reserved = max(0, reserved)

        if reserved > 0:
            self._active = True
            self.log(
                f"Lädt – SOC {self._soc:.0f}% → Ziel {self.target_soc}% | "
                f"Reserviert {reserved:.0f}W von {surplus_w:.0f}W"
            )
        else:
            self._active = False

        return reserved

    async def shutdown(self):
        # Keine Hardware-Aktion nötig
        self._active = False

    def status_dict(self) -> dict:
        return {
            **self._base_status(),
            "power_w": round(self._charge_power) if self._charge_power else 0,
            "soc": round(self._soc, 1),
            "target_soc": self.target_soc,
            "max_charge_power_w": self.max_charge_power_w,
            "soc_pct": round(self._soc),
            "target_pct": self.target_soc,
        }
