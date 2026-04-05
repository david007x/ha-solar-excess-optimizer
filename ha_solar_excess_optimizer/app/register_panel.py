"""
register_panel.py
Trägt panel_custom korrekt als Listen-Eintrag in die HA configuration.yaml ein.
Korrekte HA-Syntax (List-Format):

panel_custom:
  - name: solar-optimizer-panel
    sidebar_title: Solar Optimizer
    sidebar_icon: mdi:solar-power
    url_path: solar-optimizer
    module_url: /local/solar_excess_optimizer.html
"""
import os
import sys
import re
import json
import urllib.request
import urllib.error

HA_URL      = os.environ.get("HA_URL", "http://supervisor/core")
HA_TOKEN    = os.environ.get("HA_TOKEN", "")
CONFIG_PATH = "/config/configuration.yaml"

# Korrekte HA panel_custom Syntax: Liste mit - name: ...
PANEL_ENTRY = """\
  - name: solar-optimizer-panel
    sidebar_title: Solar Optimizer
    sidebar_icon: mdi:solar-power
    url_path: solar-optimizer
    module_url: /local/solar_excess_optimizer.html"""

MARKER = "# solar-optimizer-panel (Solar Excess Optimizer)"

STANDALONE_BLOCK = f"""\
# >>> Solar Excess Optimizer Panel <<<
panel_custom:
{PANEL_ENTRY}
{MARKER}
# <<< Solar Excess Optimizer Panel Ende >>>
"""


def read_config() -> str:
    if not os.path.exists(CONFIG_PATH):
        print(f"WARN: {CONFIG_PATH} nicht gefunden.")
        sys.exit(1)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return f.read()


def write_config(content: str):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        f.write(content)


def already_registered(content: str) -> bool:
    """Prüft ob unser Block bereits korrekt (als Liste) eingetragen ist."""
    return ("- name: solar-optimizer-panel" in content or
            "-name: solar-optimizer-panel" in content)


def remove_old_block(content: str) -> str:
    """Entfernt alten (fehlerhaften) Dict-Stil Eintrag falls vorhanden."""
    # Entfernt den alten benannten Dict-Block den wir früher geschrieben haben
    pattern = re.compile(
        r"# >>> Solar Excess Optimizer Panel.*?# <<< Solar Excess Optimizer Panel Ende >>>\n?",
        re.DOTALL
    )
    cleaned = pattern.sub("", content)

    # Auch alten solar_excess_optimizer: Dict-Eintrag unter panel_custom entfernen
    pattern2 = re.compile(
        r"(\npanel_custom:.*?)\s+solar_excess_optimizer:\s*\n(\s+\S.*?\n)+",
        re.DOTALL
    )
    cleaned = pattern2.sub(r"\1\n", cleaned)

    return cleaned


def panel_custom_exists(content: str) -> bool:
    return bool(re.search(r"^panel_custom\s*:", content, re.MULTILINE))


def append_to_existing_panel_custom(content: str) -> str:
    """Hängt den neuen Listen-Eintrag an einen bestehenden panel_custom: Block an."""
    # Finde Ende des panel_custom Blocks (nächste Zeile auf Ebene 0 oder EOF)
    pattern = re.compile(r"(^panel_custom\s*:.*?)(\n(?=\S)|\Z)", re.DOTALL | re.MULTILINE)
    def replacer(m):
        block = m.group(1).rstrip()
        rest  = m.group(2)
        return f"{block}\n{PANEL_ENTRY}\n  {MARKER}{rest}"
    return pattern.sub(replacer, content, count=1)


def main():
    content = read_config()

    # Alten fehlerhaften Block entfernen (idempotent)
    content = remove_old_block(content)

    if already_registered(content):
        print("Panel bereits korrekt registriert – nichts zu tun.")
        trigger_reload()
        return

    if panel_custom_exists(content):
        print("Bestehender panel_custom: Block gefunden – Eintrag wird ergänzt.")
        content = append_to_existing_panel_custom(content)
    else:
        print("Kein panel_custom: Block gefunden – neuen Block anlegen.")
        content = content.rstrip("\n") + "\n\n" + STANDALONE_BLOCK

    write_config(content)
    print(f"panel_custom Eintrag in {CONFIG_PATH} geschrieben.")
    trigger_reload()


def trigger_reload():
    print("Triggere HA Core-Reload...")
    status = ha_request("POST", "/api/services/homeassistant/reload_core_config")
    if status in (200, 201):
        print("HA Core-Reload erfolgreich – Panel erscheint nach Browser-Reload.")
    else:
        print(f"WARN: Reload HTTP {status} – HA bitte manuell neu starten.")


def ha_request(method: str, path: str) -> int:
    url = f"{HA_URL}{path}"
    req = urllib.request.Request(
        url, method=method,
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
        print(f"WARN: HA API Fehler: {e}")
        return 0


if __name__ == "__main__":
    main()
