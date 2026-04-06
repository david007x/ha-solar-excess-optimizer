#!/usr/bin/with-contenv bashio

export HA_TOKEN="${SUPERVISOR_TOKEN}"
export HA_URL="http://supervisor/core"
export LOG_LEVEL=$(bashio::config 'log_level')

bashio::log.info "HA Solar Excess Optimizer v0.1.2 starting..."

# ── Clean up old panel entries + register sidebar panel ───────────────────────
python3 /app/cleanup_panel.py
python3 /app/register_panel.py && \
    bashio::log.info "Sidebar panel registered successfully." || \
    bashio::log.warning "Panel registration failed – check log for details."

# ── Start Python app ──────────────────────────────────────────────────────────
python3 /app/main.py
