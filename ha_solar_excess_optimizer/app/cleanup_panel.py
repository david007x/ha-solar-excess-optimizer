"""
cleanup_panel.py
Removes all old solar optimizer panel_custom entries from configuration.yaml.
Called on startup; register_panel.py is no longer used (HA Ingress handles sidebar).
"""
import os
import re

CONFIG_PATH = "/config/configuration.yaml"


def main():
    if not os.path.exists(CONFIG_PATH):
        print("configuration.yaml not found – nothing to clean.")
        return

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    original = content

    # Remove marked blocks (both "End" and "Ende" variants)
    content = re.sub(
        r"\n?# >>> HA Solar Excess Optimizer Panel.*?# <<< HA Solar Excess Optimizer Panel End[e]? >>>\n?",
        "\n", content, flags=re.DOTALL
    )
    content = re.sub(
        r"\n?# >>> Solar Excess Optimizer Panel.*?# <<< Solar Excess Optimizer Panel End[e]? >>>\n?",
        "\n", content, flags=re.DOTALL
    )

    # Remove any remaining list-style solar-optimizer-panel entry
    content = re.sub(
        r"  - name: solar-optimizer-panel\n(?:    .*\n)*",
        "", content
    )

    # Remove old dict-style solar_excess_optimizer entry under panel_custom
    content = re.sub(
        r"[ \t]+solar_excess_optimizer:[ \t]*\n(?:[ \t]+\S[^\n]*\n)+",
        "", content
    )

    # Remove empty panel_custom blocks left behind
    content = re.sub(r"\npanel_custom:[ \t]*\n(?=\S|\Z)", "\n", content)

    if content != original:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            f.write(content)
        print("✅ Old panel_custom entries removed from configuration.yaml.")
    else:
        print("No old panel entries found – nothing to do.")


if __name__ == "__main__":
    main()
