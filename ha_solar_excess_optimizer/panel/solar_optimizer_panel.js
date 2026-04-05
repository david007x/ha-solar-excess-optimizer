class SolarOptimizerPanel extends HTMLElement {
  connectedCallback() {
    this.style.cssText = 'display:block;width:100%;height:100%;';
    const host = window.location.hostname;
    this.innerHTML = `
      <iframe
        src="http://${host}:8099"
        style="width:100%;height:100%;border:none;display:block;"
        allow="fullscreen">
      </iframe>`;
  }
}
customElements.define('solar-optimizer-panel', SolarOptimizerPanel);
