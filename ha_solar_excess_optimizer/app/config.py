import json
import os
import logging

logger = logging.getLogger(__name__)

OPTIONS_PATH = "/data/options.json"

_DEFAULTS = {
    "grid_power_entity": "",
    "update_interval_sec": 10,
    "hysteresis_w": 150,
    "on_delay_sec": 30,
    "off_delay_sec": 20,
    "log_level": "info",
    "sensor_stabilize_sec": 60,
    "devices": [],
}


def load() -> dict:
    cfg = dict(_DEFAULTS)
    if os.path.exists(OPTIONS_PATH):
        with open(OPTIONS_PATH) as f:
            data = json.load(f)
        cfg.update(data)   # file values override defaults; missing keys keep defaults
        logger.info("Configuration loaded.")
    else:
        logger.warning("options.json not found – using defaults.")
    return cfg


def save(cfg: dict):
    """Write configuration back (for Web UI changes)."""
    with open(OPTIONS_PATH, "w") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    logger.info("Configuration saved.")
