"""
ha_publisher.py
Schreibt den Add-on Zustand als virtuelle Sensor-Entities in HA zurück.
Nutzt den /api/states POST Endpunkt (kein Helper nötig, kein Neustart).

Erstellte Entities (alle mit Präfix sensor.seo_*):
  sensor.seo_surplus_w          – aktueller PV-Überschuss in W
  sensor.seo_consuming_w        – Summe aller aktiven Verbraucher
  sensor.seo_remaining_w        – verbleibender Überschuss nach Regelung
  sensor.seo_active_devices     – Anzahl aktiver Geräte
  sensor.seo_device_<name>_w    – Leistung pro Gerät
  sensor.seo_device_<name>_status – Status-Objekt pro Gerät (als JSON-Attribut)
"""

import logging
import re
import aiohttp
import os
import json

logger = logging.getLogger(__name__)

HA_URL = os.environ.get("HA_URL", "http://supervisor/core")
HA_TOKEN = os.environ.get("HA_TOKEN", "")


def _headers():
    return {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }


def _slug(name: str) -> str:
    """Gerätenamen in gültigen Entity-Slug umwandeln."""
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


async def publish(status: dict):
    """
    Wird nach jedem Regelzyklus aufgerufen.
    status = das dict das auch /api/status zurückgibt.
    """
    if not status:
        return

    entities = []

    # Globale Sensoren
    entities += [
        ("sensor.seo_surplus_w", status.get("surplus_w", 0), {
            "friendly_name": "SEO – PV Überschuss",
            "unit_of_measurement": "W",
            "device_class": "power",
            "icon": "mdi:transmission-tower-export",
            "state_class": "measurement",
        }),
        ("sensor.seo_remaining_w", status.get("remaining_w", 0), {
            "friendly_name": "SEO – Verbleibend",
            "unit_of_measurement": "W",
            "device_class": "power",
            "icon": "mdi:gauge",
            "state_class": "measurement",
        }),
    ]

    devices = status.get("devices", [])
    active = [d for d in devices if d.get("active")]
    consuming = sum(d.get("power_w", 0) for d in devices)

    entities += [
        ("sensor.seo_consuming_w", consuming, {
            "friendly_name": "SEO – Verbraucher gesamt",
            "unit_of_measurement": "W",
            "device_class": "power",
            "icon": "mdi:lightning-bolt",
            "state_class": "measurement",
        }),
        ("sensor.seo_active_devices", len(active), {
            "friendly_name": "SEO – Aktive Geräte",
            "icon": "mdi:devices",
            "active_names": [d["name"] for d in active],
        }),
    ]

    # Pro-Gerät Sensoren
    for dev in devices:
        slug = _slug(dev["name"])

        # Leistungs-Sensor
        entities.append((
            f"sensor.seo_device_{slug}_w",
            dev.get("power_w", 0),
            {
                "friendly_name": f"SEO – {dev['name']} Leistung",
                "unit_of_measurement": "W",
                "device_class": "power",
                "state_class": "measurement",
                "icon": "mdi:lightning-bolt-circle",
                "device_type": dev.get("type"),
                "priority": dev.get("priority"),
                "active": dev.get("active", False),
            }
        ))

        # Typ-spezifische Zusatzsensoren
        if dev.get("type") == "timed":
            entities.append((
                f"sensor.seo_device_{slug}_runtime",
                dev.get("runtime_today_min", 0),
                {
                    "friendly_name": f"SEO – {dev['name']} Laufzeit heute",
                    "unit_of_measurement": "min",
                    "icon": "mdi:timer",
                }
            ))
            entities.append((
                f"sensor.seo_device_{slug}_target",
                dev.get("runtime_target_min", 0),
                {
                    "friendly_name": f"SEO – {dev['name']} Laufzeitziel",
                    "unit_of_measurement": "min",
                    "icon": "mdi:timer-check",
                }
            ))

        if dev.get("type") == "stepped":
            entities.append((
                f"sensor.seo_device_{slug}_step",
                dev.get("current_step", 0),
                {
                    "friendly_name": f"SEO – {dev['name']} Stufe",
                    "icon": "mdi:stairs",
                    "total_steps": dev.get("total_steps", 0),
                }
            ))

        if dev.get("type") == "variable":
            entities.append((
                f"sensor.seo_device_{slug}_pct",
                dev.get("power_pct", 0),
                {
                    "friendly_name": f"SEO – {dev['name']} Auslastung",
                    "unit_of_measurement": "%",
                    "icon": "mdi:percent",
                }
            ))

    # Alle Entities an HA pushen
    async with aiohttp.ClientSession() as session:
        for entity_id, state, attrs in entities:
            try:
                await session.post(
                    f"{HA_URL}/api/states/{entity_id}",
                    headers=_headers(),
                    json={"state": str(state), "attributes": attrs},
                )
            except Exception as e:
                logger.warning(f"publish({entity_id}): {e}")
