from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class BaseDevice(ABC):
    """
    Basisklasse für alle Verbraucher.
    Jeder Gerätetyp erbt von hier und implementiert:
      - current_power_w  → aktuell zugewiesene Leistung
      - apply(surplus_w) → Gerät regeln, gibt tatsächlich verbrauchte Leistung zurück
      - shutdown()       → Gerät sicher ausschalten
      - status_dict()    → Zustand als Dict für Web UI / API
    """

    def __init__(self, cfg: dict):
        self.name: str = cfg["name"]
        self.priority: int = cfg.get("priority", 99)
        self.enabled: bool = cfg.get("enabled", True)
        self.device_type: str = cfg["type"]
        self._active: bool = False
        self._log: list[str] = []

    @abstractmethod
    async def apply(self, surplus_w: float) -> float:
        """
        Regelschritt: Gerät an verfügbaren Überschuss anpassen.
        Gibt zurück wie viel Watt dieses Gerät tatsächlich verbraucht.
        """
        ...

    @abstractmethod
    async def shutdown(self):
        """Gerät ausschalten."""
        ...

    @abstractmethod
    def status_dict(self) -> dict:
        """Aktueller Zustand als serialisierbares Dict."""
        ...

    def log(self, msg: str):
        logger.info(f"[{self.name}] {msg}")
        self._log.insert(0, msg)
        self._log = self._log[:5]
