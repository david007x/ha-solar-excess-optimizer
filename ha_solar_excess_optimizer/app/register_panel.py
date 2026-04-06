"""
register_panel.py
1. Copies solar_optimizer_panel.js to /config/www/
2. Writes panel_custom (correct list format with JS module_url) to configuration.yaml
3. Triggers HA core reload
"""
import os, re, sys, shutil, urllib.request, urllib.error

HA_URL      = os.environ.get("HA_URL", "http://supervisor/core")
HA_TOKEN    = os.environ.get("HA_TOKEN", "")
CONFIG_PATH = "/config/configuration.yaml"
JS_SRC      = "/panel/solar_optimizer_panel.js"
JS_DEST     = "/config/www/solar_optimizer_panel.js"

PANEL_BLOCK = """
# >>> HA Solar Excess Optimizer Panel <<<
panel_custom:
  - name: solar-optimizer-panel
    sidebar_title: Solar Optimizer
    sidebar_icon: mdi:solar-power
    url_path: solar-optimizer
    module_url: /local/solar_optimizer_panel.js
# <<< HA Solar Excess Optimizer Panel End >>>
"""


def copy_js():
    os.makedirs("/config/www", exist_ok=True)
    if os.path.exists(JS_SRC):
        shutil.copy2(JS_SRC, JS_DEST)
        print(f"✅ JS panel copied to {JS_DEST}")
    else:
        print(f"❌ JS file not found: {JS_SRC}")
        sys.exit(1)


def read_config():
    if not os.path.exists(CONFIG_PATH):
        print(f"❌ {CONFIG_PATH} not found.")
        sys.exit(1)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return f.read()


def write_config(content):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        f.write(content)


def already_registered(content):
    return "- name: solar-optimizer-panel" in content and "solar_optimizer_panel.js" in content


def clean_old_entries(content):
    content = re.sub(
        r"\n?# >>> HA Solar Excess Optimizer Panel.*?# <<< HA Solar Excess Optimizer Panel End[e]? >>>\n?",
        "\n", content, flags=re.DOTALL)
    content = re.sub(
        r"\n?# >>> Solar Excess Optimizer Panel.*?# <<< Solar Excess Optimizer Panel Ende >>>\n?",
        "\n", content, flags=re.DOTALL)
    content = re.sub(
        r"(panel_custom:.*?)  solar_excess_optimizer:.*?(?=\n\S|\Z)",
        r"\1", content, flags=re.DOTALL)
    content = re.sub(r"  - name: solar-optimizer-panel\n(?:    .*\n)*", "", content)
    content = re.sub(r"\npanel_custom:\s*\n(?=\S|\Z)", "\n", content)
    return content


def ha_reload():
    url = f"{HA_URL}/api/services/homeassistant/reload_core_config"
    req = urllib.request.Request(url, data=b"{}", method="POST",
        headers={"Authorization": f"Bearer {HA_TOKEN}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            print(f"✅ HA core reload: HTTP {r.status}")
    except urllib.error.HTTPError as e:
        print(f"⚠ Reload HTTP {e.code} – please restart HA manually.")
    except Exception as e:
        print(f"⚠ Reload error: {e}")


def main():
    copy_js()
    content = read_config()
    content = clean_old_entries(content)

    if already_registered(content):
        print("✅ Panel already registered correctly.")
        ha_reload()
        return

    content = content.rstrip("\n") + PANEL_BLOCK
    write_config(content)
    print(f"✅ panel_custom (list format + JS) written to {CONFIG_PATH}")
    ha_reload()
    print("✅ Done – panel will appear in sidebar after browser reload.")


if __name__ == "__main__":
    main()
