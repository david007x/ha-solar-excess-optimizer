class SolarOptimizerPanel extends HTMLElement {
  connectedCallback() {
    this.style.cssText = 'display:block;width:100%;height:100%;';
    this.innerHTML = `
      <iframe
        src="/api/hassio/app/ha_solar_excess_optimizer"
        style="width:100%;height:100%;border:none;display:block;"
        allow="fullscreen">
      </iframe>`;
  }
}
customElements.define('solar-optimizer-panel', SolarOptimizerPanel);
