#!/usr/bin/with-contenv bashio

export HA_TOKEN="${SUPERVISOR_TOKEN}"
export HA_URL="http://supervisor/core"
export LOG_LEVEL=$(bashio::config 'log_level')

bashio::log.info "HA Solar Excess Optimizer v4 startet..."

# ── Alten fehlerhaften panel_custom Eintrag aus configuration.yaml entfernen ─
python3 /app/cleanup_panel.py && \
    bashio::log.info "panel_custom Einträge bereinigt." || true

# ── iframe Panel via HA REST API registrieren ─────────────────────────────────
bashio::log.info "Registriere iframe Panel in HA Sidebar..."
python3 /app/register_panel.py && \
    bashio::log.info "Panel erfolgreich registriert." || \
    bashio::log.warning "Panel-Registrierung fehlgeschlagen – Add-on manuell neu starten."

# ── Python App starten ────────────────────────────────────────────────────────
python3 /app/main.py
