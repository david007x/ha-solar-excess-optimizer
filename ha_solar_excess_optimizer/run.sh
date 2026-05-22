#!/usr/bin/with-contenv bashio

bashio::log.info "Solar Excess Optimizer v0.2.8 starting..."

# Cleanup any leftover panel entries from old versions
python3 /app/cleanup_panel.py || true

exec python3 /app/main.py
