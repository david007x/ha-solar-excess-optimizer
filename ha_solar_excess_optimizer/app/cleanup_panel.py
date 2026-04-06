"""
cleanup_panel.py
Removes old/broken panel_custom entries from configuration.yaml.
Run on add-on startup before register_panel.py.
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

    # Remove our marked blocks
    content = re.sub(
        r"\n?# >>> HA Solar Excess Optimizer Panel.*?# <<< HA Solar Excess Optimizer Panel Ende >>>\n?",
        "\n", content, flags=re.DOTALL
    )
    content = re.sub(
        r"\n?# >>> Solar Excess Optimizer Panel.*?# <<< Solar Excess Optimizer Panel Ende >>>\n?",
        "\n", content, flags=re.DOTALL
    )

    # Remove old dict-style solar_excess_optimizer entry under panel_custom
    content = re.sub(
        r"[ \t]+solar_excess_optimizer:[ \t]*\n(?:[ \t]+\S[^\n]*\n)+",
        "", content
    )

    # Remove empty panel_custom blocks
    content = re.sub(r"\npanel_custom:[ \t]*\n(?=\S|\Z)", "\n", content)

    if content != original:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            f.write(content)
        print("Old panel_custom entries removed.")
    else:
        print("No old entries found – nothing to do.")


if __name__ == "__main__":
    main()
