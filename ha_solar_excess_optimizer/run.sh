#!/usr/bin/with-contenv bashio

export HA_TOKEN="${SUPERVISOR_TOKEN}"
export HA_URL="http://supervisor/core"
export LOG_LEVEL=$(bashio::config 'log_level')

bashio::log.info "HA Solar Excess Optimizer startet..."

# ── Custom Panel in HA registrieren ──────────────────────────────────────────
PANEL_SOURCE="/app/../panel/solar_excess_optimizer.html"
PANEL_DEST="/config/www/solar_excess_optimizer.html"

mkdir -p /config/www

if cp "$PANEL_SOURCE" "$PANEL_DEST" 2>/dev/null; then
    bashio::log.info "Panel HTML nach /config/www kopiert."
else
    bashio::log.warning "Konnte Panel HTML nicht kopieren."
fi

# Panel registrieren via panel_custom REST call
bashio::log.info "Registriere Custom Panel in HA Sidebar..."
HTTP=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST \
    -H "Authorization: Bearer ${HA_TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{"icon":"mdi:solar-power","title":"Solar Optimizer"}' \
    "${HA_URL}/api/panels/solar_excess_optimizer")

bashio::log.info "Panel Registrierung: HTTP ${HTTP}"

if [ "$HTTP" != "200" ] && [ "$HTTP" != "201" ]; then
    bashio::log.warning "Automatische Registrierung fehlgeschlagen – manuellen Fallback nutzen:"
    bashio::log.warning "  panel_custom:"
    bashio::log.warning "    solar_excess_optimizer:"
    bashio::log.warning "      name: solar-optimizer-panel"
    bashio::log.warning "      sidebar_title: Solar Optimizer"
    bashio::log.warning "      sidebar_icon: mdi:solar-power"
    bashio::log.warning "      url_path: solar-optimizer"
    bashio::log.warning "      module_url: /local/solar_excess_optimizer.html"
fi

# ── Python App starten ────────────────────────────────────────────────────────
python3 /app/main.py
