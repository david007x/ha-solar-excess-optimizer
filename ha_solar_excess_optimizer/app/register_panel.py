"""
register_panel.py
Registriert einen iframe-Panel in HA via REST API.
HA hat einen eingebauten iframe-Panel-Typ der direkt per API registriert werden kann –
kein panel_custom / configuration.yaml Edit nötig.
"""
import os
import sys
import json
import urllib.request
import urllib.error

HA_URL   = os.environ.get("HA_URL", "http://supervisor/core")
HA_TOKEN = os.environ.get("HA_TOKEN", "")

PANEL_URL_PATH = "solar_excess_optimizer"
PANEL_TITLE    = "Solar Optimizer"
PANEL_ICON     = "mdi:solar-power"


def ha_request(method: str, path: str, payload: dict = None):
    url = f"{HA_URL}{path}"
    data = json.dumps(payload).encode("utf-8") if payload else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={
            "Authorization": f"Bearer {HA_TOKEN}",
            "Content-Type": "application/json",
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except Exception as e:
        return 0, str(e)


def get_ha_host() -> str:
    """Liest die externe HA URL aus der Supervisor API."""
    status, body = ha_request("GET", "/api/")
    try:
        data = json.loads(body)
        # Supervisor gibt base_url nicht direkt – wir nutzen den Hostnamen
        return "homeassistant.local"
    except Exception:
        return "homeassistant.local"


def register_iframe_panel(iframe_url: str):
    """
    Registriert einen iframe Panel via HA REST API.
    POST /api/panels  →  registriert dauerhaft in HA.
    """
    payload = {
        "component_name": "iframe",
        "sidebar_title": PANEL_TITLE,
        "sidebar_icon": PANEL_ICON,
        "url_path": PANEL_URL_PATH,
        "config": {
            "url": iframe_url
        }
    }
    status, body = ha_request("POST", f"/api/panels/{PANEL_URL_PATH}", payload)
    print(f"Panel registriert: HTTP {status} – {body[:120]}")
    return status in (200, 201)


def main():
    # iframe URL: gleicher Host wie HA, Port 8099
    # Wir nutzen einen relativen Ansatz – der Browser kennt den Hostnamen
    # Für die API brauchen wir eine absolute URL
    # Da wir den externen Hostnamen nicht kennen, nutzen wir einen Platzhalter
    # und schreiben stattdessen ein JS-Panel das den Host dynamisch ermittelt

    print("Registriere Solar Optimizer Panel in HA...")

    # Methode 1: iframe panel via REST API
    iframe_url = "http://homeassistant.local:8099"
    success = register_iframe_panel(iframe_url)

    if success:
        print(f"✅ Panel '{PANEL_TITLE}' erfolgreich registriert.")
        print(f"   Erreichbar unter: http://homeassistant.local:8123/{PANEL_URL_PATH}")
    else:
        print("⚠ REST-Registrierung fehlgeschlagen.")
        print("  Fallback: panel_custom via configuration.yaml (siehe README)")
        sys.exit(1)


if __name__ == "__main__":
    main()
