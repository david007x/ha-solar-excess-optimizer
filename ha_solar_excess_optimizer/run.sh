#!/usr/bin/with-contenv bashio

export HA_TOKEN="${SUPERVISOR_TOKEN}"
export HA_URL="http://supervisor/core"
export LOG_LEVEL=$(bashio::config 'log_level')

bashio::log.info "HA Solar Excess Optimizer v0.2.6 starting..."

# ── Remove old panel_custom entries (sidebar is now handled by HA Ingress) ────
python3 /app/cleanup_panel.py

# ── Start Python app ──────────────────────────────────────────────────────────
python3 /app/main.py
