from abc import ABC, abstractmethod
import time
import logging

logger = logging.getLogger(__name__)

OVERRIDE_AUTO      = "auto"
OVERRIDE_FORCE_ON  = "force_on"
OVERRIDE_FORCE_OFF = "force_off"


class BaseDevice(ABC):
    """
    Abstract base class for all devices.
    Features:
      - Time-based hysteresis (on/off delay)
      - Manual override (force_on / force_off / auto)
      - condition_entity: only activate when entity = 'on'
      - consumption_entity: read actual power from HA instead of using estimate
    """

    def __init__(self, cfg: dict, hysteresis_w: int = 150):
        self.name: str         = cfg["name"]
        self.priority: int     = cfg.get("priority", 99)
        self.enabled: bool     = cfg.get("enabled", True)
        self.device_type: str  = cfg["type"]
        self.hysteresis_w: int = hysteresis_w

        self.on_delay_sec: int  = cfg.get("on_delay_sec", 30)
        self.off_delay_sec: int = cfg.get("off_delay_sec", 20)

        _ce = cfg.get("condition_entity", "")
        self.condition_entity: str | None = _ce if _ce else None

        # condition_states: welche Sensor-Zustände als "erfüllt" gelten
        # Eingabe als String "charged,available" oder Liste ["charged","available"]
        # Leer = Standard on/off Logik
        raw_cs = cfg.get("condition_states", "")
        if isinstance(raw_cs, list):
            self.condition_states: list[str] = [s.strip() for s in raw_cs if str(s).strip()]
        elif raw_cs:
            self.condition_states: list[str] = [s.strip() for s in str(raw_cs).split(",") if s.strip()]
        else:
            self.condition_states: list[str] = []

        _coe = cfg.get("consumption_entity", "")
        self.consumption_entity: str | None = _coe if _coe else None

        self._active: bool   = False
        self._log: list[str] = []
        self._override: str  = OVERRIDE_AUTO

        self._on_condition_since: float | None  = None
        self._off_condition_since: float | None = None
        self._condition_blocked: bool = False
        self._actual_consumption_w: float = 0.0
        self._allocated_w: float = 0.0  # intern zugeteilte Leistung (stabil, kein Sensor-Lag)

        # Mindestlaufzeit nach Einschalten (verhindert Flapping)
        self.min_runtime_sec: int = cfg.get("min_runtime_sec", 60)
        self._active_since: float = 0.0

    # ── Override ──────────────────────────────────────────────────────────────

    def set_override(self, mode: str):
        if mode not in (OVERRIDE_AUTO, OVERRIDE_FORCE_ON, OVERRIDE_FORCE_OFF):
            raise ValueError(f"Invalid override mode: {mode}")
        self._override = mode
        self._on_condition_since = None
        self._off_condition_since = None
        self.log(f"Override set: {mode}")

    @property
    def override(self) -> str:
        return self._override

    # ── condition_entity ──────────────────────────────────────────────────────

    async def check_condition(self) -> bool:
        """
        Returns True if condition_entity is met (or not configured).

        Two modes:
        1. condition_states set → True if sensor value is in the list (case-insensitive, whitespace-stripped)
           e.g. condition_states: "charged,available,connected"
        2. No condition_states → Standard: on/true/1/yes or numeric > 0
        """
        if not self.condition_entity:
            return True
        from ha_client import get_state
        state = await get_state(self.condition_entity)
        if state is None:
            self.log(f"⚠ condition_entity '{self.condition_entity}' not found")
            return False

        val = str(state.get("state", "")).strip()

        # Mode 1: condition_states list (case-insensitive)
        if self.condition_states:
            val_lower = val.lower()
            states_lower = [s.lower() for s in self.condition_states]
            result = val_lower in states_lower
            if not result:
                self.log(f"⛔ '{val}' not in {self.condition_states}")
            else:
                self.log(f"✅ '{val}' matches condition")
            return result

        # Mode 2: Standard on/off/numeric
        val_lower = val.lower()
        if val_lower in ("on", "true", "1", "yes"):
            return True
        if val_lower in ("off", "false", "0", "no", "unavailable", "unknown", "none"):
            return False
        try:
            return float(val) > 0
        except ValueError:
            return False

    # ── consumption_entity ────────────────────────────────────────────────────

    async def read_consumption(self, fallback_w: float) -> float:
        """Read actual power from consumption_entity, or use fallback."""
        if not self.consumption_entity:
            self._actual_consumption_w = fallback_w
            return fallback_w
        from ha_client import get_numeric_state
        val = await get_numeric_state(self.consumption_entity)
        self._actual_consumption_w = val
        return val

    # ── Time-based hysteresis ─────────────────────────────────────────────────

    def _check_on_delay(self, condition_met: bool) -> bool:
        now = time.time()
        if condition_met:
            if self._on_condition_since is None:
                self._on_condition_since = now
                self.log(f"On-timer started ({self.on_delay_sec}s)")
            return (now - self._on_condition_since) >= self.on_delay_sec
        else:
            self._on_condition_since = None
            return False

    def _check_off_delay(self, condition_met: bool) -> bool:
        now = time.time()
        if condition_met:
            if self._off_condition_since is None:
                self._off_condition_since = now
                self.log(f"Off-timer started ({self.off_delay_sec}s)")
            return (now - self._off_condition_since) >= self.off_delay_sec
        else:
            self._off_condition_since = None
            return False

    def _on_timer_progress(self) -> float:
        if self._on_condition_since is None:
            return 0
        return min(100, round((time.time() - self._on_condition_since) / max(1, self.on_delay_sec) * 100))

    def _off_timer_progress(self) -> float:
        if self._off_condition_since is None:
            return 0
        return min(100, round((time.time() - self._off_condition_since) / max(1, self.off_delay_sec) * 100))

    # ── Abstract methods ──────────────────────────────────────────────────────

    @abstractmethod
    async def apply(self, surplus_w: float) -> float:
        """Control step. Returns actual watts consumed."""
        ...

    @abstractmethod
    async def shutdown(self):
        """Safely turn off device."""
        ...

    @abstractmethod
    def status_dict(self) -> dict:
        """Current state as serializable dict."""
        ...

    def log(self, msg: str):
        logger.info(f"[{self.name}] {msg}")
        self._log.insert(0, msg)
        self._log = self._log[:5]

    def _base_status(self) -> dict:
        return {
            "name":               self.name,
            "type":               self.device_type,
            "priority":           self.priority,
            "enabled":            self.enabled,
            "active":             self._active,
            "override":           self._override,
            "condition_ok":       not self._condition_blocked,
            "condition_entity":   self.condition_entity,
            "consumption_entity": self.consumption_entity,
            "actual_consumption_w": round(self._actual_consumption_w),
            "on_timer_pct":       self._on_timer_progress(),
            "off_timer_pct":      self._off_timer_progress(),
            "log":                self._log,
        }
