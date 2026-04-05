from abc import ABC, abstractmethod
import time
import logging

logger = logging.getLogger(__name__)

# Override-Modi
OVERRIDE_AUTO     = "auto"      # Automatische Regelung
OVERRIDE_FORCE_ON = "force_on"  # Immer ein, egal ob Überschuss
OVERRIDE_FORCE_OFF = "force_off" # Immer aus, egal ob Überschuss


class BaseDevice(ABC):
    """
    Basisklasse für alle Verbraucher.
    Features:
      - Zeitbasierte Hysterese (Ein- und Ausschaltverzögerung)
      - Manueller Override (force_on / force_off / auto)
      - Einheitliches status_dict() Interface
    """

    def __init__(self, cfg: dict, hysteresis_w: int = 150):
        self.name: str          = cfg["name"]
        self.priority: int      = cfg.get("priority", 99)
        self.enabled: bool      = cfg.get("enabled", True)
        self.device_type: str   = cfg["type"]
        self.hysteresis_w: int  = hysteresis_w

        # Zeitbasierte Hysterese (Sekunden bis zum Schalten)
        self.on_delay_sec: int  = cfg.get("on_delay_sec", 30)   # Einschaltverzögerung
        self.off_delay_sec: int = cfg.get("off_delay_sec", 20)  # Ausschaltverzögerung

        # Interner Zustand
        self._active: bool      = False
        self._log: list[str]    = []
        self._override: str     = OVERRIDE_AUTO

        # Zeitstempel wann Bedingung erstmals erfüllt war
        self._on_condition_since: float | None  = None
        self._off_condition_since: float | None = None

    # ── Override ──────────────────────────────────────────────────────────────

    def set_override(self, mode: str):
        if mode not in (OVERRIDE_AUTO, OVERRIDE_FORCE_ON, OVERRIDE_FORCE_OFF):
            raise ValueError(f"Ungültiger Override-Modus: {mode}")
        self._override = mode
        self._on_condition_since = None
        self._off_condition_since = None
        self.log(f"Override gesetzt: {mode}")

    @property
    def override(self) -> str:
        return self._override

    # ── Zeitbasierte Hysterese Helfer ─────────────────────────────────────────

    def _check_on_delay(self, condition_met: bool) -> bool:
        """
        Gibt True zurück wenn Einschaltbedingung seit on_delay_sec erfüllt ist.
        Setzt Timer zurück wenn Bedingung nicht mehr erfüllt.
        """
        now = time.time()
        if condition_met:
            if self._on_condition_since is None:
                self._on_condition_since = now
                self.log(f"Einschalt-Timer gestartet ({self.on_delay_sec}s)")
            elapsed = now - self._on_condition_since
            return elapsed >= self.on_delay_sec
        else:
            if self._on_condition_since is not None:
                self._on_condition_since = None
            return False

    def _check_off_delay(self, condition_met: bool) -> bool:
        """
        Gibt True zurück wenn Ausschaltbedingung seit off_delay_sec erfüllt ist.
        """
        now = time.time()
        if condition_met:
            if self._off_condition_since is None:
                self._off_condition_since = now
                self.log(f"Ausschalt-Timer gestartet ({self.off_delay_sec}s)")
            elapsed = now - self._off_condition_since
            return elapsed >= self.off_delay_sec
        else:
            if self._off_condition_since is not None:
                self._off_condition_since = None
            return False

    def _on_timer_progress(self) -> float:
        """Fortschritt des Einschalt-Timers in % (0-100)."""
        if self._on_condition_since is None:
            return 0
        elapsed = time.time() - self._on_condition_since
        return min(100, round(elapsed / max(1, self.on_delay_sec) * 100))

    def _off_timer_progress(self) -> float:
        """Fortschritt des Ausschalt-Timers in % (0-100)."""
        if self._off_condition_since is None:
            return 0
        elapsed = time.time() - self._off_condition_since
        return min(100, round(elapsed / max(1, self.off_delay_sec) * 100))

    # ── Abstrakte Methoden ────────────────────────────────────────────────────

    @abstractmethod
    async def apply(self, surplus_w: float) -> float:
        """Regelschritt. Gibt tatsächlich verbrauchte Watt zurück."""
        ...

    @abstractmethod
    async def shutdown(self):
        """Gerät sicher ausschalten."""
        ...

    @abstractmethod
    def status_dict(self) -> dict:
        """Aktueller Zustand als serialisierbares Dict."""
        ...

    # ── Logging ───────────────────────────────────────────────────────────────

    def log(self, msg: str):
        logger.info(f"[{self.name}] {msg}")
        self._log.insert(0, msg)
        self._log = self._log[:5]

    def _base_status(self) -> dict:
        """Gemeinsame Felder für alle status_dict() Implementierungen."""
        return {
            "name": self.name,
            "type": self.device_type,
            "priority": self.priority,
            "enabled": self.enabled,
            "active": self._active,
            "override": self._override,
            "on_timer_pct": self._on_timer_progress(),
            "off_timer_pct": self._off_timer_progress(),
            "log": self._log,
        }
