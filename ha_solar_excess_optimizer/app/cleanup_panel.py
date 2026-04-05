"""
cleanup_panel.py
Entfernt alte fehlerhafte panel_custom Einträge (Dict-Stil) aus configuration.yaml.
Wird beim Add-on-Start vor register_panel.py ausgeführt.
"""
import os
import re

CONFIG_PATH = "/config/configuration.yaml"


def main():
    if not os.path.exists(CONFIG_PATH):
        print("configuration.yaml nicht gefunden – nichts zu bereinigen.")
        return

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    original = content

    # Entferne unsere alten markierten Blöcke
    content = re.sub(
        r"\n?# >>> Solar Excess Optimizer Panel.*?# <<< Solar Excess Optimizer Panel Ende >>>\n?",
        "\n",
        content,
        flags=re.DOTALL
    )

    # Entferne alten Dict-Stil solar_excess_optimizer Eintrag unter panel_custom
    content = re.sub(
        r"(\npanel_custom:\n(?:[ \t]+.*\n)*?)[ \t]+solar_excess_optimizer:[ \t]*\n(?:[ \t]+.*\n)*",
        r"\1",
        content
    )

    # Entferne leere panel_custom: Blöcke die übrig bleiben
    content = re.sub(r"\npanel_custom:\n(?=\S|\Z)", "\n", content)

    if content != original:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            f.write(content)
        print("Alte panel_custom Einträge entfernt.")
    else:
        print("Keine alten Einträge gefunden – nichts zu tun.")


if __name__ == "__main__":
    main()
