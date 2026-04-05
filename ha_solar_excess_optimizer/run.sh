#!/usr/bin/with-contenv bashio

export HA_TOKEN="${SUPERVISOR_TOKEN}"
export HA_URL="http://supervisor/core"
export LOG_LEVEL=$(bashio::config 'log_level')

bashio::log.info "HA Solar Excess Optimizer v4 startet..."

# ── Alte Einträge bereinigen + Panel registrieren ─────────────────────────────
python3 /app/cleanup_panel.py
python3 /app/register_panel.py && \
    bashio::log.info "Panel registriert – erscheint nach Browser-Reload in Sidebar." || \
    bashio::log.warning "Panel-Registrierung fehlgeschlagen – siehe Log."

# ── Python App starten ────────────────────────────────────────────────────────
python3 /app/main.py
