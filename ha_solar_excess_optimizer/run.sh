#!/usr/bin/with-contenv bashio
export HA_TOKEN="${SUPERVISOR_TOKEN}"
export HA_URL="http://supervisor/core"
export LOG_LEVEL=$(bashio::config 'log_level')
bashio::log.info "HA Solar Excess Optimizer v2 startet..."
python3 /app/main.py
