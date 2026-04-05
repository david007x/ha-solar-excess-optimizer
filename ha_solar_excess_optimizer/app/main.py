import asyncio
import json
import logging
import config as cfg_module
from aiohttp import web
from controller import SolarController

# ─── Logging ──────────────────────────────────────────────────────────────────
_cfg = cfg_module.load()
_level = getattr(logging, _cfg.get("log_level", "info").upper(), logging.INFO)
logging.basicConfig(level=_level,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("ha_solar_excess_optimizer")

controller: SolarController | None = None
_last_status: dict = {}

# ─── Web UI HTML ──────────────────────────────────────────────────────────────
HTML = r"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>HA Solar Excess Optimizer</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;600;700&display=swap');
  :root {
    --bg: #080f1a; --surface: #0d1b2e; --surface2: #132238;
    --border: #1e3350; --text: #e8f0fe; --muted: #5a7a9e;
    --solar: #f5c842; --grid: #3b8ef0; --green: #2dde98;
    --red: #ff4d6a; --orange: #ff9a3c;
    --radius: 12px; --mono: 'Space Mono', monospace; --sans: 'DM Sans', sans-serif;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--text); font-family: var(--sans); min-height: 100vh; }

  /* HEADER */
  header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 1rem 1.5rem;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    position: sticky; top: 0; z-index: 100;
  }
  .header-left { display: flex; align-items: center; gap: 0.75rem; }
  .logo { font-family: var(--mono); font-weight: 700; font-size: 1.1rem; color: var(--solar); letter-spacing: -0.02em; }
  .pulse { width: 8px; height: 8px; border-radius: 50%; background: var(--green); animation: pulse 2s infinite; }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.3} }
  .tab-bar { display: flex; gap: 4px; }
  .tab { font-family: var(--mono); font-size: 0.7rem; padding: 6px 14px; border-radius: 6px;
         border: 1px solid var(--border); background: transparent; color: var(--muted);
         cursor: pointer; transition: all .2s; }
  .tab.active, .tab:hover { background: var(--surface2); color: var(--text); border-color: var(--grid); }

  /* PAGES */
  .page { display: none; padding: 1.5rem; max-width: 1100px; margin: 0 auto; }
  .page.active { display: block; }

  /* STAT GRID */
  .stat-grid { display: grid; grid-template-columns: repeat(auto-fit,minmax(160px,1fr)); gap: 1rem; margin-bottom: 1.5rem; }
  .stat { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 1.1rem 1.25rem; }
  .stat-label { font-size: 0.65rem; font-family: var(--mono); text-transform: uppercase; letter-spacing:.08em; color: var(--muted); margin-bottom: .4rem; }
  .stat-value { font-size: 1.8rem; font-weight: 700; font-family: var(--mono); line-height: 1; }
  .stat-value.pos { color: var(--green); }
  .stat-value.neg { color: var(--red); }
  .stat-value.solar { color: var(--solar); }
  .stat-sub { font-size: 0.72rem; color: var(--muted); margin-top: .3rem; }

  /* DEVICE CARDS */
  .device-grid { display: grid; grid-template-columns: repeat(auto-fill,minmax(280px,1fr)); gap: 1rem; }
  .device-card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 1.1rem 1.25rem;
    transition: border-color .3s;
  }
  .device-card.on { border-color: var(--green); }
  .device-card.forced { border-color: var(--orange); }
  .device-top { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: .75rem; }
  .device-name { font-weight: 700; font-size: 1rem; }
  .device-type { font-size: 0.65rem; font-family: var(--mono); color: var(--muted);
                 background: var(--surface2); border: 1px solid var(--border);
                 padding: 2px 8px; border-radius: 99px; margin-top: 2px; }
  .device-badge {
    font-size: 0.65rem; font-family: var(--mono); padding: 3px 10px;
    border-radius: 99px; font-weight: 700; white-space: nowrap;
  }
  .badge-on  { background: #0d3d2a; color: var(--green); border: 1px solid var(--green); }
  .badge-off { background: var(--surface2); color: var(--muted); border: 1px solid var(--border); }
  .badge-forced { background: #3d2500; color: var(--orange); border: 1px solid var(--orange); }
  .device-power { font-family: var(--mono); font-size: 1.4rem; font-weight: 700;
                  color: var(--solar); margin-bottom: .6rem; }
  .progress-bar { height: 4px; background: var(--surface2); border-radius: 99px; overflow: hidden; margin-bottom: .6rem; }
  .progress-fill { height: 100%; background: linear-gradient(90deg, var(--grid), var(--green)); border-radius: 99px; transition: width .5s; }
  .device-log { font-size: 0.7rem; color: var(--muted); font-family: var(--mono); line-height: 1.6; }
  .step-dots { display: flex; gap: 4px; margin-bottom: .6rem; }
  .step-dot { width: 24px; height: 6px; border-radius: 3px; background: var(--surface2); transition: background .3s; }
  .step-dot.active { background: var(--green); }

  /* SECTION HEADERS */
  .section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem; }
  .section-title { font-family: var(--mono); font-size: 0.75rem; text-transform: uppercase;
                   letter-spacing: .1em; color: var(--muted); }

  /* CONFIG PAGE */
  .config-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 1.25rem; margin-bottom: 1rem; }
  .config-title { font-family: var(--mono); font-size: 0.8rem; color: var(--solar); margin-bottom: 1rem; font-weight: 700; }
  .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: .75rem; margin-bottom: .75rem; }
  .form-row.full { grid-template-columns: 1fr; }
  .form-group { display: flex; flex-direction: column; gap: .35rem; }
  label { font-size: 0.7rem; font-family: var(--mono); color: var(--muted); text-transform: uppercase; letter-spacing: .05em; }
  input, select { background: var(--surface2); border: 1px solid var(--border); border-radius: 8px;
                  color: var(--text); font-family: var(--mono); font-size: 0.82rem;
                  padding: .5rem .75rem; outline: none; transition: border-color .2s; }
  input:focus, select:focus { border-color: var(--grid); }
  .btn { font-family: var(--mono); font-size: 0.75rem; padding: .55rem 1.1rem;
         border-radius: 8px; border: none; cursor: pointer; font-weight: 700;
         transition: all .2s; text-transform: uppercase; letter-spacing: .05em; }
  .btn-primary { background: var(--grid); color: #fff; }
  .btn-primary:hover { background: #5fa0ff; }
  .btn-danger { background: transparent; color: var(--red); border: 1px solid var(--red); }
  .btn-danger:hover { background: var(--red); color: #fff; }
  .btn-success { background: var(--green); color: #000; }
  .device-list-item { display: flex; align-items: center; justify-content: space-between;
                      padding: .75rem 1rem; background: var(--surface2);
                      border: 1px solid var(--border); border-radius: 8px; margin-bottom: .5rem; }
  .dli-left { display: flex; flex-direction: column; gap: .2rem; }
  .dli-name { font-weight: 600; font-size: .9rem; }
  .dli-meta { font-size: .7rem; font-family: var(--mono); color: var(--muted); }
  .dli-right { display: flex; align-items: center; gap: .5rem; }
  .toggle { position: relative; width: 36px; height: 20px; }
  .toggle input { opacity: 0; width: 0; height: 0; }
  .slider { position: absolute; inset: 0; background: var(--surface); border: 1px solid var(--border);
            border-radius: 99px; cursor: pointer; transition: .2s; }
  .slider:before { content:''; position: absolute; height: 14px; width: 14px; left: 2px; bottom: 2px;
                   background: var(--muted); border-radius: 50%; transition: .2s; }
  input:checked + .slider { background: var(--green); border-color: var(--green); }
  input:checked + .slider:before { transform: translateX(16px); background: #fff; }

  /* ADD DEVICE FORM */
  #add-device-section { display: none; }
  #add-device-section.open { display: block; }
  .type-pills { display: flex; gap: .5rem; flex-wrap: wrap; margin-bottom: .75rem; }
  .type-pill { font-family: var(--mono); font-size: .7rem; padding: 5px 12px; border-radius: 99px;
               border: 1px solid var(--border); cursor: pointer; background: var(--surface2); color: var(--muted);
               transition: all .2s; }
  .type-pill.selected { border-color: var(--grid); color: var(--text); background: #0d2040; }

  /* LOG TABLE */
  .log-table { width: 100%; border-collapse: collapse; font-family: var(--mono); font-size: .75rem; }
  .log-table th { text-align: left; padding: .5rem .75rem; color: var(--muted);
                  border-bottom: 1px solid var(--border); font-size: .65rem; text-transform: uppercase; letter-spacing: .07em; }
  .log-table td { padding: .45rem .75rem; border-bottom: 1px solid var(--border); }
  .log-table tr:last-child td { border-bottom: none; }

  /* ENTITY PICKER */
  .ep-wrap { position: relative; }
  .ep-input-row { display: flex; gap: 6px; align-items: center; }
  .ep-input { flex: 1; }
  .ep-btn { background: var(--surface2); border: 1px solid var(--border); border-radius: 8px;
            color: var(--muted); font-size: .75rem; padding: .45rem .7rem; cursor: pointer;
            white-space: nowrap; font-family: var(--mono); transition: all .2s; flex-shrink: 0; }
  .ep-btn:hover { border-color: var(--grid); color: var(--text); }
  .ep-dropdown { position: absolute; top: calc(100% + 4px); left: 0; right: 0; z-index: 999;
                 background: var(--surface); border: 1px solid var(--grid); border-radius: 10px;
                 max-height: 260px; overflow: hidden; display: flex; flex-direction: column;
                 box-shadow: 0 8px 32px #000a; }
  .ep-search { padding: .5rem .75rem; background: var(--surface2); border: none;
               border-bottom: 1px solid var(--border); color: var(--text);
               font-family: var(--mono); font-size: .78rem; outline: none; width: 100%; }
  .ep-list { overflow-y: auto; flex: 1; }
  .ep-item { padding: .45rem .75rem; cursor: pointer; font-size: .78rem;
             font-family: var(--mono); border-bottom: 1px solid var(--border); display: flex;
             justify-content: space-between; align-items: center; gap: .5rem; transition: background .15s; }
  .ep-item:hover { background: var(--surface2); }
  .ep-item:last-child { border-bottom: none; }
  .ep-item-id { color: var(--text); }
  .ep-item-meta { color: var(--muted); font-size: .68rem; white-space: nowrap; }
  .ep-state { color: var(--solar); font-size: .68rem; white-space: nowrap; }
  .ep-empty { padding: .75rem; color: var(--muted); font-size: .78rem; font-family: var(--mono); text-align: center; }
  .ep-loading { padding: .75rem; color: var(--muted); font-size: .75rem; font-family: var(--mono); text-align: center; }

  /* OVERRIDE BUTTONS */
  .override-bar { display: flex; gap: 4px; margin-top: .6rem; }
  .ov-btn { flex: 1; font-family: var(--mono); font-size: .6rem; padding: 5px 4px;
            border-radius: 6px; border: 1px solid var(--border); cursor: pointer;
            background: var(--surface2); color: var(--muted); transition: all .2s;
            text-transform: uppercase; letter-spacing: .04em; font-weight: 700; }
  .ov-btn.active-on  { background: #0d3d2a; color: var(--green); border-color: var(--green); }
  .ov-btn.active-off { background: #3d0a15; color: var(--red);   border-color: var(--red);   }
  .ov-btn.active-auto{ background: #0d2040; color: var(--grid);  border-color: var(--grid);  }
  /* BATTERY CARD */
  .battery-bar { height: 6px; background: var(--surface2); border-radius: 99px; overflow: hidden; margin-top: .35rem; }
  .battery-fill { height: 100%; border-radius: 99px; transition: width .5s; }
  .battery-fill.ok  { background: linear-gradient(90deg, var(--grid), var(--green)); }
  .battery-fill.low { background: linear-gradient(90deg, var(--red), var(--orange)); }
  /* TIMER BAR */
  .timer-wrap { display: flex; align-items: center; gap: .4rem; margin-bottom: .4rem; }
  .timer-label { font-size: .6rem; font-family: var(--mono); color: var(--muted); white-space: nowrap; }
  .timer-bar { flex: 1; height: 3px; background: var(--surface2); border-radius: 99px; overflow: hidden; }
  .timer-fill-on  { height: 100%; background: var(--green);  border-radius: 99px; transition: width 1s; }
  .timer-fill-off { height: 100%; background: var(--orange); border-radius: 99px; transition: width 1s; }
  /* MOBILE */
  @media (max-width: 600px) {
    header { padding: .75rem 1rem; }
    .logo { font-size: .9rem; }
    .tab { font-size: .6rem; padding: 5px 8px; }
    .page { padding: 1rem; }
    .stat-grid { grid-template-columns: 1fr 1fr; gap: .6rem; }
    .stat { padding: .85rem 1rem; }
    .stat-value { font-size: 1.4rem; }
    .device-grid { grid-template-columns: 1fr; }
    .form-row { grid-template-columns: 1fr; }
    .ov-btn { font-size: .55rem; padding: 4px 2px; }
    .btn { font-size: .7rem; padding: .5rem .9rem; }
    .ep-btn { font-size: .7rem; padding: .4rem .5rem; }
  }
</style>
</head>
<body>

<header>
  <div class="header-left">
    <div class="pulse"></div>
    <span class="logo">☀ HA SOLAR EXCESS</span>
  </div>
  <div class="tab-bar">
    <button class="tab active" onclick="showPage('dashboard')">Dashboard</button>
    <button class="tab" onclick="showPage('config')">Verbraucher</button>
    <button class="tab" onclick="showPage('log')">Log</button>
  </div>
</header>

<!-- DASHBOARD -->
<div id="page-dashboard" class="page active">
  <div class="stat-grid" id="stat-grid">
    <div class="stat"><div class="stat-label">PV Überschuss</div><div class="stat-value" id="surplus-val">–</div><div class="stat-sub">Netzeinspeisung</div></div>
    <div class="stat"><div class="stat-label">Verteilt an</div><div class="stat-value solar" id="consuming-val">–</div><div class="stat-sub">Aktive Geräte</div></div>
    <div class="stat"><div class="stat-label">Verbleibend</div><div class="stat-value" id="remaining-val">–</div><div class="stat-sub">Nach Regelung</div></div>
    <div class="stat"><div class="stat-label">Geräte aktiv</div><div class="stat-value solar" id="active-count">–</div><div class="stat-sub" id="active-names">–</div></div>
  </div>
  <div class="section-header">
    <span class="section-title">Verbraucher</span>
    <span class="section-title" id="last-update">–</span>
  </div>
  <div class="device-grid" id="device-grid"></div>
</div>

<!-- CONFIG -->
<div id="page-config" class="page">
  <div class="config-card">
    <div class="config-title">// GLOBALE EINSTELLUNGEN</div>
    <div class="form-row">
      <div class="form-group">
        <label>Netzleistung Entity</label>
        <div class="ep-wrap" id="ep-wrap-grid">
          <div class="ep-input-row">
            <input class="ep-input" id="cfg-grid-entity" placeholder="sensor.grid_power" autocomplete="off" readonly>
            <button class="ep-btn" onclick="openPicker('ep-wrap-grid','cfg-grid-entity','sensor,input_number')">⌕ Suchen</button>
          </div>
        </div>
      </div>
      <div class="form-group">
        <label>Hysterese (W)</label>
        <input id="cfg-hysteresis" type="number" value="150">
      </div>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>Regelintervall (Sek)</label>
        <input id="cfg-interval" type="number" value="10">
      </div>
      <div class="form-group">
        <label>Log Level</label>
        <select id="cfg-loglevel">
          <option>debug</option><option selected>info</option><option>warning</option><option>error</option>
        </select>
      </div>
    </div>
  </div>

  <div class="config-card">
    <div class="config-title">// VERBRAUCHER</div>
    <div id="device-list-config"></div>
    <button class="btn btn-primary" onclick="toggleAddDevice()" style="margin-top:.75rem">+ Gerät hinzufügen</button>
  </div>

  <div class="config-card" id="add-device-section">
    <div class="config-title">// NEUES GERÄT</div>

    <div class="form-row">
      <div class="form-group">
        <label>Name</label>
        <input id="new-name" placeholder="z.B. Heizstab">
      </div>
      <div class="form-group">
        <label>Priorität</label>
        <input id="new-priority" type="number" value="3" min="1">
      </div>
    </div>

    <div class="form-group" style="margin-bottom:.75rem">
      <label>Gerätetyp</label>
      <div class="type-pills">
        <div class="type-pill selected" data-type="switch" onclick="selectType(this)">Switch (An/Aus)</div>
        <div class="type-pill" data-type="stepped" onclick="selectType(this)">Stufen (fix)</div>
        <div class="type-pill" data-type="variable" onclick="selectType(this)">Stufenlos</div>
        <div class="type-pill" data-type="timed" onclick="selectType(this)">Zeitgesteuert</div>
        <div class="type-pill" data-type="battery" onclick="selectType(this)">🔋 Batterie</div>
      </div>
    </div>

    <!-- switch -->
    <div id="fields-switch">
      <div class="form-row">
        <div class="form-group">
          <label>Switch Entity</label>
          <div class="ep-wrap" id="ep-wrap-sw-entity">
            <div class="ep-input-row">
              <input class="ep-input" id="sw-entity" placeholder="switch.mein_geraet" autocomplete="off" readonly>
              <button class="ep-btn" onclick="openPicker('ep-wrap-sw-entity','sw-entity','switch')">⌕</button>
            </div>
          </div>
        </div>
        <div class="form-group">
          <label>Leistung (W)</label>
          <input id="sw-power" type="number" placeholder="500">
        </div>
      </div>
    </div>

    <!-- stepped -->
    <div id="fields-stepped" style="display:none">
      <div id="stepped-rows"></div>
      <button class="btn" onclick="addStepRow()" style="background:var(--surface2);color:var(--text);border:1px solid var(--border);margin-bottom:.75rem">+ Stufe hinzufügen</button>
    </div>

    <!-- variable -->
    <div id="fields-variable" style="display:none">
      <div class="form-row">
        <div class="form-group">
          <label>Switch Entity</label>
          <div class="ep-wrap" id="ep-wrap-var-switch">
            <div class="ep-input-row">
              <input class="ep-input" id="var-switch" placeholder="switch.wallbox" autocomplete="off" readonly>
              <button class="ep-btn" onclick="openPicker('ep-wrap-var-switch','var-switch','switch')">⌕</button>
            </div>
          </div>
        </div>
        <div class="form-group">
          <label>Power Entity (number.*)</label>
          <div class="ep-wrap" id="ep-wrap-var-power-entity">
            <div class="ep-input-row">
              <input class="ep-input" id="var-power-entity" placeholder="number.wallbox_current_ampere" autocomplete="off" readonly>
              <button class="ep-btn" onclick="openPicker('ep-wrap-var-power-entity','var-power-entity','number')">⌕</button>
            </div>
          </div>
        </div>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label>Min Leistung (W)</label>
          <input id="var-min" type="number" value="1400">
        </div>
        <div class="form-group">
          <label>Max Leistung (W)</label>
          <input id="var-max" type="number" value="11000">
        </div>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label>Schrittgröße (W)</label>
          <input id="var-step" type="number" value="230">
        </div>
        <div class="form-group">
          <label>Rampen-Intervall (Sek)</label>
          <input id="var-ramp" type="number" value="30">
        </div>
      </div>
    </div>

    <!-- timed -->
    <div id="fields-timed" style="display:none">
      <div class="form-row">
        <div class="form-group">
          <label>Switch Entity</label>
          <div class="ep-wrap" id="ep-wrap-tim-entity">
            <div class="ep-input-row">
              <input class="ep-input" id="tim-entity" placeholder="switch.waschmaschine" autocomplete="off" readonly>
              <button class="ep-btn" onclick="openPicker('ep-wrap-tim-entity','tim-entity','switch')">⌕</button>
            </div>
          </div>
        </div>
        <div class="form-group">
          <label>Leistung (W)</label>
          <input id="tim-power" type="number" placeholder="2000">
        </div>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label>Mindestlaufzeit (Minuten/Tag)</label>
          <input id="tim-runtime" type="number" value="90">
        </div>
      </div>
    </div>

    <div style="display:flex;gap:.5rem;margin-top:.75rem">
      <button class="btn btn-success" onclick="addDevice()">Gerät speichern</button>
      <button class="btn" onclick="toggleAddDevice()" style="background:var(--surface2);border:1px solid var(--border);color:var(--muted)">Abbrechen</button>
    </div>
  </div>

  <div style="display:flex;justify-content:flex-end;margin-top:1rem">
    <button class="btn btn-primary" onclick="saveConfig()">💾 Konfiguration speichern & neu laden</button>
  </div>
</div>

<!-- LOG -->
<div id="page-log" class="page">
  <div class="config-card">
    <div class="config-title">// ZYKLUSPROTOKOLL</div>
    <table class="log-table">
      <thead><tr><th>#</th><th>Überschuss</th><th>Verbleibend</th><th>Geräte</th></tr></thead>
      <tbody id="log-tbody"></tbody>
    </table>
  </div>
</div>

<script>
// ─── Navigation ──────────────────────────────────────────────────────────────
function showPage(id) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.getElementById('page-' + id).classList.add('active');
  event.target.classList.add('active');
  if (id === 'config') loadConfigForm();
}

// ─── Dashboard refresh ───────────────────────────────────────────────────────
let _data = null;
async function refresh() {
  try {
    const r = await fetch('/api/status');
    _data = await r.json();
    renderDashboard(_data);
  } catch(e) {}
}

function renderDashboard(d) {
  const s = d.surplus_w;
  setVal('surplus-val', (s >= 0 ? '+' : '') + s + ' W', s >= 0 ? 'pos' : 'neg');

  const active = d.devices.filter(x => x.active);
  const consumed = d.devices.reduce((a, x) => a + (x.power_w || 0), 0);
  setVal('consuming-val', consumed + ' W', 'solar');
  setVal('remaining-val', (d.remaining_w >= 0 ? '+' : '') + d.remaining_w + ' W',
         d.remaining_w >= 0 ? 'pos' : 'neg');
  document.getElementById('active-count').textContent = active.length + '/' + d.devices.length;
  document.getElementById('active-names').textContent = active.map(x => x.name).join(', ') || 'Keines';
  document.getElementById('last-update').textContent =
    'Aktualisiert ' + new Date().toLocaleTimeString('de-DE');


  const grid = document.getElementById('device-grid');
  grid.innerHTML = d.devices.map(dev => renderDeviceCard(dev)).join('');

  // Log
  const tbody = document.getElementById('log-tbody');
  if (tbody && d.cycle_log) {
    tbody.innerHTML = d.cycle_log.map((e, i) => `
      <tr>
        <td style="color:var(--muted)">${i+1}</td>
        <td style="color:${e.surplus_w>=0?'var(--green)':'var(--red)'}">${e.surplus_w > 0 ? '+' : ''}${e.surplus_w} W</td>
        <td style="color:var(--muted)">${e.remaining_w} W</td>
        <td>${e.devices.map(d => `${d.name}: ${d.consumed_w}W`).join(' · ')}</td>
      </tr>
    `).join('');
  }
}

function setVal(id, text, cls) {
  const el = document.getElementById(id);
  el.textContent = text;
  el.className = 'stat-value ' + (cls || '');
}

function renderDeviceCard(dev) {
  const badgeCls = dev.forced ? 'badge-forced' : (dev.active ? 'badge-on' : 'badge-off');
  const badgeText = dev.forced ? '⚡ ZWANG' : (dev.active ? '● AN' : '○ AUS');
  const cardCls = dev.forced ? 'forced' : (dev.active ? 'on' : '');
  const ov = dev.override || 'auto';
  let extra = '';
  // Timer bars
  if (dev.on_timer_pct > 0 && !dev.active) {
    extra += `<div class="timer-wrap"><span class="timer-label">EIN in…</span>
      <div class="timer-bar"><div class="timer-fill-on" style="width:${dev.on_timer_pct}%"></div></div>
      <span class="timer-label">${dev.on_timer_pct}%</span></div>`;
  }
  if (dev.off_timer_pct > 0 && dev.active) {
    extra += `<div class="timer-wrap"><span class="timer-label">AUS in…</span>
      <div class="timer-bar"><div class="timer-fill-off" style="width:${dev.off_timer_pct}%"></div></div>
      <span class="timer-label">${dev.off_timer_pct}%</span></div>`;
  }

  if (dev.type === 'variable' && dev.active) {
    extra = `<div class="progress-bar"><div class="progress-fill" style="width:${dev.power_pct||0}%"></div></div>
             <div class="device-log" style="color:var(--muted);font-size:.68rem">${dev.power_min}W → ${dev.power_max}W</div>`;
  }
  if (dev.type === 'stepped') {
    const dots = Array.from({length: dev.total_steps || 3}, (_, i) =>
      `<div class="step-dot ${i < (dev.current_step||0) ? 'active' : ''}"></div>`
    ).join('');
    extra = `<div class="step-dots">${dots}</div>`;
  }
  if (dev.type === 'timed') {
    extra = `<div class="progress-bar"><div class="progress-fill" style="width:${dev.runtime_pct||0}%"></div></div>
             <div class="device-log">${dev.runtime_today_min||0} / ${dev.runtime_target_min} min heute</div>`;
  }
  if (dev.type === 'battery') {
    const soc = dev.soc_pct || 0;
    const tgt = dev.target_pct || 100;
    extra = `<div class="progress-bar"><div class="progress-fill" style="width:${soc}%;background:linear-gradient(90deg,#3b8ef0,#2dde98)"></div></div>
             <div class="device-log">SOC: ${soc}% → Ziel: ${tgt}% | Max: ${dev.max_charge_power_w||0}W</div>`;
  }

  const log = (dev.log || []).slice(0, 2).join('<br>');
  const n = encodeURIComponent(dev.name);
  return `
    <div class="device-card ${cardCls}">
      <div class="device-top">
        <div>
          <div class="device-name">${dev.name}</div>
          <div class="device-type">${dev.type} · P${dev.priority}</div>
        </div>
        <span class="device-badge ${badgeCls}">${badgeText}</span>
      </div>
      <div class="device-power">${dev.power_w || 0} W</div>
      ${extra}
      <div class="device-log">${log}</div>
      <div class="override-bar">
        <button class="ov-btn ${ov==='force_on'?'active-on':''}"
          onclick="setOverride('${n}','force_on')">⬆ Zwang AN</button>
        <button class="ov-btn ${ov==='auto'?'active-auto':''}"
          onclick="setOverride('${n}','auto')">⟳ Auto</button>
        <button class="ov-btn ${ov==='force_off'?'active-off':''}"
          onclick="setOverride('${n}','force_off')">⬇ Zwang AUS</button>
      </div>
    </div>`;
}

// ─── Config Form ─────────────────────────────────────────────────────────────
let _localDevices = [];

async function loadConfigForm() {
  const r = await fetch('/api/config');
  const cfg = await r.json();
  document.getElementById('cfg-grid-entity').value = cfg.grid_power_entity || '';
  document.getElementById('cfg-hysteresis').value = cfg.hysteresis_w || 150;
  document.getElementById('cfg-interval').value = cfg.update_interval_sec || 10;
  document.getElementById('cfg-loglevel').value = cfg.log_level || 'info';
  _localDevices = JSON.parse(JSON.stringify(cfg.devices || []));
  renderDeviceList();
}

function renderDeviceList() {
  const el = document.getElementById('device-list-config');
  if (!_localDevices.length) { el.innerHTML = '<p style="color:var(--muted);font-size:.8rem">Noch keine Geräte konfiguriert.</p>'; return; }
  el.innerHTML = _localDevices.map((d, i) => `
    <div class="device-list-item">
      <div class="dli-left">
        <span class="dli-name">${d.name}</span>
        <span class="dli-meta">${d.type} · Priorität ${d.priority} · ${getPowerLabel(d)}</span>
      </div>
      <div class="dli-right">
        <label class="toggle">
          <input type="checkbox" ${d.enabled ? 'checked' : ''} onchange="toggleDevice(${i},this.checked)">
          <span class="slider"></span>
        </label>
        <button class="btn btn-danger" style="padding:4px 10px;font-size:.65rem" onclick="removeDevice(${i})">✕</button>
      </div>
    </div>`).join('');
}

function getPowerLabel(d) {
  if (d.type === 'battery') return `SOC → ${d.target_soc || 100}%`;
  if (d.type === 'stepped') return d.steps?.map(s => s.power_w + 'W').join('/') || '–';
  if (d.type === 'variable') return `${d.power_min}–${d.power_max}W`;
  return (d.power_w || '?') + 'W';
}

function toggleDevice(i, val) { _localDevices[i].enabled = val; }
function removeDevice(i) { _localDevices.splice(i, 1); renderDeviceList(); }

async function saveConfig() {
  const cfg = {
    grid_power_entity: document.getElementById('cfg-grid-entity').value,
    hysteresis_w: parseInt(document.getElementById('cfg-hysteresis').value),
    update_interval_sec: parseInt(document.getElementById('cfg-interval').value),
    log_level: document.getElementById('cfg-loglevel').value,
    devices: _localDevices,
  };
  await fetch('/api/config', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(cfg) });
  alert('Gespeichert! HA Solar Excess Optimizer lädt die Konfiguration neu.');
  loadConfigForm();
}

// ─── Add Device ───────────────────────────────────────────────────────────────
let _selectedType = 'switch';
let _stepRows = [];

function toggleAddDevice() {
  const el = document.getElementById('add-device-section');
  el.classList.toggle('open');
}

function selectType(el) {
  document.querySelectorAll('.type-pill').forEach(p => p.classList.remove('selected'));
  el.classList.add('selected');
  _selectedType = el.dataset.type;
  ['switch','stepped','variable','timed','battery'].forEach(t =>
    document.getElementById('fields-' + t).style.display = t === _selectedType ? 'block' : 'none');
}

function addStepRow() {
  const id = Date.now();
  _stepRows.push(id);
  const stepNum = _stepRows.length;
  const wrapId = 'ep-wrap-step-' + id;
  const inputId = 'step-sw-' + id;
  const row = document.createElement('div');
  row.id = 'step-' + id;
  row.className = 'form-row';
  row.style.marginBottom = '.5rem';
  row.innerHTML = `
    <div class="form-group">
      <label>Switch Entity Stufe ${stepNum}</label>
      <div class="ep-wrap" id="${wrapId}">
        <div class="ep-input-row">
          <input class="ep-input" id="${inputId}" placeholder="switch.heizstab_stufe${stepNum}" autocomplete="off" readonly>
          <button class="ep-btn" onclick="openPicker('${wrapId}','${inputId}','switch')">⌕</button>
        </div>
      </div>
    </div>
    <div class="form-group">
      <label>Leistung (W)</label>
      <input class="step-power-input" type="number" placeholder="${stepNum * 1000}">
    </div>`;
  document.getElementById('stepped-rows').appendChild(row);
}

function addDevice() {
  const name = document.getElementById('new-name').value.trim();
  const priority = parseInt(document.getElementById('new-priority').value) || 99;
  if (!name) { alert('Bitte einen Namen eingeben.'); return; }

  let dev = { name, type: _selectedType, priority, enabled: true };

  if (_selectedType === 'switch') {
    dev.switch_entity = document.getElementById('sw-entity').value;
    dev.power_w = parseInt(document.getElementById('sw-power').value) || 0;
  } else if (_selectedType === 'stepped') {
    const rows = document.querySelectorAll('#stepped-rows .form-row');
    dev.steps = Array.from(rows).map(r => {
      const swInput = r.querySelector('.ep-input');
      const pwInput = r.querySelector('.step-power-input');
      return { switch_entity: swInput ? swInput.value : '', power_w: pwInput ? (parseInt(pwInput.value) || 0) : 0 };
    });
  } else if (_selectedType === 'variable') {
    dev.switch_entity = document.getElementById('var-switch').value;
    dev.power_entity = document.getElementById('var-power-entity').value;
    dev.power_min = parseInt(document.getElementById('var-min').value) || 1400;
    dev.power_max = parseInt(document.getElementById('var-max').value) || 11000;
    dev.power_step = parseInt(document.getElementById('var-step').value) || 230;
    dev.ramp_interval_sec = parseInt(document.getElementById('var-ramp').value) || 30;
  } else if (_selectedType === 'timed') {
    dev.switch_entity = document.getElementById('tim-entity').value;
    dev.power_w = parseInt(document.getElementById('tim-power').value) || 0;
    dev.min_runtime_minutes = parseInt(document.getElementById('tim-runtime').value) || 60;
  } else if (_selectedType === 'battery') {
    dev.soc_entity = document.getElementById('bat-soc-entity').value;
    dev.power_entity = document.getElementById('bat-power-entity').value || null;
    dev.target_soc = parseInt(document.getElementById('bat-target-soc').value) || 100;
    dev.max_charge_power_w = parseInt(document.getElementById('bat-max-power').value) || 5000;
  }

  _localDevices.push(dev);
  _localDevices.sort((a, b) => a.priority - b.priority);
  renderDeviceList();
  document.getElementById('add-device-section').classList.remove('open');
  _stepRows = [];
  document.getElementById('stepped-rows').innerHTML = '';
  document.getElementById('bat-soc-entity').value = '';
  document.getElementById('bat-power-entity').value = '';
}

// ─── Config API ───────────────────────────────────────────────────────────────
// Start
refresh();
setInterval(refresh, 10000);

// ─── Entity Picker ────────────────────────────────────────────────────────────
let _entities = null;   // cached after first load
let _activePicker = null;

async function loadEntities(domains) {
  const qs = domains ? '?domain=' + domains : '';
  const r = await fetch('/api/entities' + qs);
  return await r.json();
}

async function openPicker(wrapId, inputId, domains) {
  // Close any open picker
  document.querySelectorAll('.ep-dropdown').forEach(d => d.remove());
  _activePicker = null;

  const wrap = document.getElementById(wrapId);
  const inputEl = document.getElementById(inputId);

  const dropdown = document.createElement('div');
  dropdown.className = 'ep-dropdown';
  dropdown.innerHTML = '<div class="ep-loading">⟳ Entities laden...</div>';
  wrap.appendChild(dropdown);
  _activePicker = { wrapId, inputId, dropdown };

  // Close on outside click
  setTimeout(() => {
    document.addEventListener('click', _outsideClick, { once: true });
  }, 10);

  let entities;
  try {
    entities = await loadEntities(domains);
  } catch(e) {
    dropdown.innerHTML = '<div class="ep-empty">⚠ HA API nicht erreichbar</div>';
    return;
  }

  renderDropdown(dropdown, inputEl, entities);
}

function renderDropdown(dropdown, inputEl, entities) {
  dropdown.innerHTML = `
    <input class="ep-search" placeholder="Suchen..." oninput="filterEntities(this)" autofocus>
    <div class="ep-list" id="ep-list-inner"></div>`;
  const list = dropdown.querySelector('#ep-list-inner');
  renderEntityList(list, entities, inputEl, dropdown);

  // Autofocus search
  setTimeout(() => dropdown.querySelector('.ep-search')?.focus(), 30);
  dropdown._allEntities = entities;
  dropdown._inputEl = inputEl;
}

function filterEntities(searchEl) {
  const q = searchEl.value.toLowerCase();
  const dropdown = searchEl.closest('.ep-dropdown');
  const filtered = dropdown._allEntities.filter(e =>
    e.entity_id.toLowerCase().includes(q) ||
    e.friendly_name.toLowerCase().includes(q)
  );
  const list = dropdown.querySelector('#ep-list-inner');
  renderEntityList(list, filtered, dropdown._inputEl, dropdown);
}

function renderEntityList(list, entities, inputEl, dropdown) {
  if (!entities.length) {
    list.innerHTML = '<div class="ep-empty">Keine Entities gefunden</div>';
    return;
  }
  list.innerHTML = entities.slice(0, 150).map(e => `
    <div class="ep-item" onclick="selectEntity('${e.entity_id}', '${inputEl.id}')">
      <div>
        <div class="ep-item-id">${e.entity_id}</div>
        <div class="ep-item-meta">${e.friendly_name !== e.entity_id ? e.friendly_name : ''}</div>
      </div>
      <span class="ep-state">${e.state}${e.unit ? ' ' + e.unit : ''}</span>
    </div>`).join('');
}

function selectEntity(entityId, inputId) {
  document.getElementById(inputId).value = entityId;
  document.querySelectorAll('.ep-dropdown').forEach(d => d.remove());
  _activePicker = null;
}

function _outsideClick(e) {
  if (!e.target.closest('.ep-wrap')) {
    document.querySelectorAll('.ep-dropdown').forEach(d => d.remove());
    _activePicker = null;
  }
}

// Also allow manual typing (remove readonly if user double-clicks)
document.addEventListener('dblclick', e => {
  if (e.target.classList.contains('ep-input')) {
    e.target.removeAttribute('readonly');
    e.target.focus();
  }
});


// ─── Override ─────────────────────────────────────────────────────────────────
async function setOverride(deviceName, mode) {
  await fetch('/api/override', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({name: decodeURIComponent(deviceName), mode})
  });
  await refresh();
}

// ─── Entity Picker Cache ──────────────────────────────────────────────────────
const _epCache = {};
const _EP_TTL_MS = 5 * 60 * 1000; // 5 Minuten Cache

async function loadEntities(domains) {
  const key = domains || '_all';
  const now = Date.now();
  if (_epCache[key] && (now - _epCache[key].ts) < _EP_TTL_MS) {
    return _epCache[key].data;
  }
  const qs = domains ? '?domain=' + domains : '';
  const r = await fetch('/api/entities' + qs);
  const data = await r.json();
  _epCache[key] = { data, ts: now };
  return data;
}
</script>
</body>
</html>"""


# ─── API Routes ───────────────────────────────────────────────────────────────

async def handle_index(request):
    # Allow embedding in HA iframe (no X-Frame-Options restriction)
    return web.Response(
        text=HTML,
        content_type="text/html",
        headers={"X-Frame-Options": "SAMEORIGIN", "Content-Security-Policy": "frame-ancestors *"}
    )


async def handle_status(request):
    return web.Response(
        text=json.dumps(_last_status, ensure_ascii=False),
        content_type="application/json"
    )


async def handle_get_config(request):
    cfg = cfg_module.load()
    return web.Response(
        text=json.dumps(cfg, ensure_ascii=False),
        content_type="application/json"
    )


async def handle_post_config(request):
    """Konfiguration aus Web UI speichern und Controller neu laden."""
    global controller
    try:
        new_cfg = await request.json()
        cfg_module.save(new_cfg)
        controller.reload(new_cfg)
        return web.Response(text='{"ok":true}', content_type="application/json")
    except Exception as e:
        logger.error(f"Config save error: {e}")
        return web.Response(status=500, text=json.dumps({"error": str(e)}))


# ─── Regelschleife ────────────────────────────────────────────────────────────

async def control_loop(cfg: dict):
    global _last_status
    interval = cfg.get("update_interval_sec", 10)
    logger.info(f"Regelschleife aktiv (Intervall: {interval}s)")
    while True:
        try:
            result = await controller.run_cycle()
            _last_status = result
            await ha_publisher.publish(result)
        except Exception as e:
            logger.error(f"Regelzyklus Fehler: {e}", exc_info=True)
        await asyncio.sleep(interval)


# ─── Start ────────────────────────────────────────────────────────────────────


async def handle_favicon(request):
    svg = b"""<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'>
      <circle cx='16' cy='16' r='8' fill='#f5c842'/>
      <g stroke='#f5c842' stroke-width='2.5' stroke-linecap='round'>
        <line x1='16' y1='2' x2='16' y2='6'/>
        <line x1='16' y1='26' x2='16' y2='30'/>
        <line x1='2' y1='16' x2='6' y2='16'/>
        <line x1='26' y1='16' x2='30' y2='16'/>
        <line x1='6.3' y1='6.3' x2='9.2' y2='9.2'/>
        <line x1='22.8' y1='22.8' x2='25.7' y2='25.7'/>
        <line x1='25.7' y1='6.3' x2='22.8' y2='9.2'/>
        <line x1='9.2' y1='22.8' x2='6.3' y2='25.7'/>
      </g>
    </svg>"""
    return web.Response(body=svg, content_type='image/svg+xml',
                        headers={'Cache-Control': 'max-age=86400'})


async def handle_override(request):
    """POST /api/override  { name: str, mode: auto|force_on|force_off }"""
    try:
        body = await request.json()
        name = body.get("name", "")
        mode = body.get("mode", "auto")
        device = controller.get_device(name)
        if device is None:
            return web.Response(status=404,
                text=json.dumps({"error": f"Gerät '{name}' nicht gefunden"}))
        device.set_override(mode)
        logger.info(f"Override gesetzt: {name} → {mode}")
        return web.Response(text=json.dumps({"ok": True, "name": name, "mode": mode}),
                            content_type="application/json")
    except Exception as e:
        return web.Response(status=400, text=json.dumps({"error": str(e)}))

async def handle_entities(request):
    """
    Gibt alle HA Entities zurück, optional gefiltert nach ?domain=sensor,switch,number
    Wird vom Web UI Entity-Picker genutzt.
    """
    domain_filter = request.rel_url.query.get("domain", "")
    domains = [d.strip() for d in domain_filter.split(",") if d.strip()]
    try:
        import aiohttp as _aiohttp
        import os as _os
        ha_url = _os.environ.get("HA_URL", "http://supervisor/core")
        ha_token = _os.environ.get("HA_TOKEN", "")
        headers = {"Authorization": f"Bearer {ha_token}"}
        async with _aiohttp.ClientSession() as session:
            async with session.get(f"{ha_url}/api/states", headers=headers) as resp:
                if resp.status != 200:
                    return web.Response(status=502, text='{"error":"HA nicht erreichbar"}')
                states = await resp.json()

        entities = []
        for s in states:
            eid = s.get("entity_id", "")
            dom = eid.split(".")[0]
            if domains and dom not in domains:
                continue
            attrs = s.get("attributes", {})
            entities.append({
                "entity_id": eid,
                "friendly_name": attrs.get("friendly_name", eid),
                "state": s.get("state", ""),
                "unit": attrs.get("unit_of_measurement", ""),
                "domain": dom,
            })

        entities.sort(key=lambda e: e["entity_id"])
        return web.Response(
            text=json.dumps(entities, ensure_ascii=False),
            content_type="application/json"
        )
    except Exception as e:
        logger.error(f"handle_entities: {e}")
        return web.Response(status=500, text=json.dumps({"error": str(e)}))


async def main():
    global controller
    cfg = cfg_module.load()
    controller = SolarController(cfg)

    app = web.Application()
    app.router.add_get("/", handle_index)
    app.router.add_get("/api/status", handle_status)
    app.router.add_get("/api/config", handle_get_config)
    app.router.add_post("/api/config", handle_post_config)
    app.router.add_get("/favicon.ico", handle_favicon)
    app.router.add_post("/api/override", handle_override)
    app.router.add_get("/api/entities", handle_entities)

    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", 8099).start()
    logger.info("Web UI: http://0.0.0.0:8099")

    await control_loop(cfg)


if __name__ == "__main__":
    asyncio.run(main())
