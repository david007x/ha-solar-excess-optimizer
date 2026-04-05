import json
import os
import logging

logger = logging.getLogger(__name__)

OPTIONS_PATH = "/data/options.json"

_DEFAULTS = {
    "grid_power_entity": "sensor.grid_power",
    "update_interval_sec": 10,
    "hysteresis_w": 150,
    "log_level": "info",
    "devices": [],
}


def load() -> dict:
    if os.path.exists(OPTIONS_PATH):
        with open(OPTIONS_PATH) as f:
            cfg = json.load(f)
            logger.info("Konfiguration geladen.")
            return cfg
    logger.warning("options.json nicht gefunden – nutze Defaults.")
    return dict(_DEFAULTS)


def save(cfg: dict):
    """Schreibt Konfiguration zurück (für Web UI Änderungen)."""
    with open(OPTIONS_PATH, "w") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    logger.info("Konfiguration gespeichert.")
