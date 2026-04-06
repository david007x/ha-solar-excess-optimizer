import json
import os
import logging

logger = logging.getLogger(__name__)

OPTIONS_PATH = "/data/options.json"

_DEFAULTS = {
    "grid_power_entity": "sensor.grid_power",
    "update_interval_sec": 10,
    "hysteresis_w": 150,
    "on_delay_sec": 30,
    "off_delay_sec": 20,
    "log_level": "info",
    "devices": [],
}


def load() -> dict:
    if os.path.exists(OPTIONS_PATH):
        with open(OPTIONS_PATH) as f:
            cfg = json.load(f)
            logger.info("Configuration loaded.")
            return cfg
    logger.warning("options.json not found – using defaults.")
    return dict(_DEFAULTS)


def save(cfg: dict):
    """Write configuration back (for Web UI changes)."""
    with open(OPTIONS_PATH, "w") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    logger.info("Configuration saved.")
