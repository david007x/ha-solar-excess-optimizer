"""
register_panel.py
Trägt panel_custom für den Solar Excess Optimizer in die HA configuration.yaml ein
und triggert anschließend einen HA Core-Reload via REST API.
Wird beim Add-on-Start einmalig ausgeführt.
"""
import os
import sys
import re
import json
import urllib.request
import urllib.error

HA_URL   = os.environ.get("HA_URL", "http://supervisor/core")
HA_TOKEN = os.environ.get("HA_TOKEN", "")
CONFIG_PATH = "/config/configuration.yaml"

PANEL_BLOCK = """\
# >>> Solar Excess Optimizer Panel (automatisch eingetragen) <<<
panel_custom:
  solar_excess_optimizer:
    name: solar-optimizer-panel
    sidebar_title: Solar Optimizer
    sidebar_icon: mdi:solar-power
    url_path: solar-optimizer
    module_url: /local/solar_excess_optimizer.html
# <<< Solar Excess Optimizer Panel Ende >>>
"""

MARKER_START = "# >>> Solar Excess Optimizer Panel"
MARKER_END   = "# <<< Solar Excess Optimizer Panel Ende >>>"


def read_config() -> str:
    if not os.path.exists(CONFIG_PATH):
        print(f"WARN: {CONFIG_PATH} nicht gefunden – kann Panel nicht registrieren.")
        sys.exit(1)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return f.read()


def write_config(content: str):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        f.write(content)


def panel_already_registered(content: str) -> bool:
    return MARKER_START in content


def remove_old_block(content: str) -> str:
    """Entfernt einen eventuell veralteten Block (für Updates)."""
    if MARKER_START not in content:
        return content
    pattern = re.compile(
        re.escape(MARKER_START) + r".*?" + re.escape(MARKER_END) + r"\n?",
        re.DOTALL
    )
    return pattern.sub("", content)


def ha_request(method: str, path: str, payload: dict = None) -> int:
    url = f"{HA_URL}{path}"
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {HA_TOKEN}",
            "Content-Type": "application/json",
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception as e:
        print(f"WARN: HA API Fehler ({path}): {e}")
        return 0


def trigger_reload():
    """Fordert HA auf, die configuration.yaml neu zu laden."""
    # Zuerst config check
    status = ha_request("POST", "/api/config/core/check_config")
    print(f"Config-Check: HTTP {status}")

    # Dann reload (nur frontend/panel relevant)
    status = ha_request("POST", "/api/services/homeassistant/reload_core_config")
    print(f"Core-Reload: HTTP {status}")
    if status in (200, 201):
        print("HA Core-Reload erfolgreich.")
    else:
        print(f"WARN: Reload HTTP {status} – HA manuell neu starten um Panel zu aktivieren.")


def main():
    content = read_config()

    # Alten Block entfernen (idempotent bei Updates)
    content = remove_old_block(content)

    # Neu eintragen
    content = content.rstrip("\n") + "\n\n" + PANEL_BLOCK
    write_config(content)
    print(f"panel_custom in {CONFIG_PATH} eingetragen.")

    # HA reload triggern
    trigger_reload()


if __name__ == "__main__":
    main()
