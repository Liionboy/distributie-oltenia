class DistributieOlteniaCard extends HTMLElement {
  setConfig(config) {
    this._config = { title: "Distribuție Oltenia", ...config };
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() { return 4; }

  _render() {
    if (!this._hass) return;
    const sensors = Object.entries(this._hass.states || {})
      .filter(([id]) => id.startsWith("sensor.deo_"))
      .map(([id, st]) => ({
        id,
        name: st.attributes?.friendly_name || id,
        value: st.state,
        unit: st.attributes?.unit_of_measurement || "",
        consumption: st.attributes?.consumption,
        date: st.attributes?.reading_date,
      }));

    this.shadowRoot.innerHTML = `
      <ha-card>
        <div class="wrap">
          <div class="title">${this._config.title}</div>
          ${sensors.length ? sensors.map((s) => `
            <div class="row">
              <div class="name">${s.name}</div>
              <div class="val">${s.value} ${s.unit}</div>
              <div class="meta">Consum: ${s.consumption ?? "-"} · Citire: ${s.date ?? "-"}</div>
            </div>
          `).join("") : `<div class="empty">Nu există senzori DEO</div>`}
        </div>
      </ha-card>
      <style>
        .wrap{padding:14px}.title{font-weight:700;font-size:16px;margin-bottom:8px}
        .row{padding:8px;border-radius:10px;background:var(--secondary-background-color);margin-bottom:8px}
        .name{font-size:13px}.val{font-weight:700;margin-top:3px}.meta{font-size:11px;color:var(--secondary-text-color);margin-top:2px}
        .empty{color:var(--secondary-text-color);font-size:13px}
      </style>
    `;
  }
}
customElements.define("distributie-oltenia-card", DistributieOlteniaCard);
window.customCards = window.customCards || [];
window.customCards.push({type:"distributie-oltenia-card",name:"Distribuție Oltenia Card",description:"Card pentru senzori DEO"});
