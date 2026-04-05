from devices.base import BaseDevice
from devices.switch_device import SwitchDevice
from devices.stepped_device import SteppedDevice
from devices.variable_device import VariableDevice
from devices.timed_device import TimedDevice
from devices.battery_device import BatteryDevice


def create_device(cfg: dict, hysteresis_w: int = 150) -> BaseDevice:
    """
    Factory: Erstellt den richtigen Gerätetyp anhand von cfg['type'].
    Neue Gerätetypen hier einfach registrieren.
    """
    device_type = cfg.get("type", "switch")

    registry = {
        "switch":   SwitchDevice,
        "stepped":  SteppedDevice,
        "variable": VariableDevice,
        "timed":    TimedDevice,
        "battery":  BatteryDevice,
    }

    cls = registry.get(device_type)
    if cls is None:
        raise ValueError(f"Unbekannter Gerätetyp: '{device_type}'. "
                         f"Erlaubt: {list(registry.keys())}")

    return cls(cfg, hysteresis_w=hysteresis_w)
