#!/usr/bin/with-contenv bashio

export HA_TOKEN="${SUPERVISOR_TOKEN}"
export HA_URL="http://supervisor/core"
export LOG_LEVEL=$(bashio::config 'log_level')

bashio::log.info "HA Solar Excess Optimizer startet..."

# ── Panel HTML in /config/www kopieren ───────────────────────────────────────
mkdir -p /config/www
if cp /panel/solar_excess_optimizer.html /config/www/solar_excess_optimizer.html 2>/dev/null; then
    bashio::log.info "Panel HTML nach /config/www kopiert."
else
    bashio::log.warning "Konnte Panel HTML nicht kopieren (Pfad: /panel/solar_excess_optimizer.html)"
fi

# ── panel_custom in configuration.yaml eintragen ─────────────────────────────
python3 /app/register_panel.py && \
    bashio::log.info "Panel in configuration.yaml eingetragen." || \
    bashio::log.warning "Panel-Registrierung fehlgeschlagen – siehe Log."

# ── Python App starten ────────────────────────────────────────────────────────
python3 /app/main.py
