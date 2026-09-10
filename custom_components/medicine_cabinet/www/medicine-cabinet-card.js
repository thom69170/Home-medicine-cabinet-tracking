/*
 * Medicine Cabinet card — a Grocy-style visual overview of tracked
 * medications (name, purpose, quantity, expiration) for Home Assistant.
 *
 * Auto-loaded by the Medicine Cabinet integration (no manual Lovelace
 * "resources:" entry needed). Add it to a dashboard with:
 *
 *   type: custom:medicine-cabinet-card
 *
 * Optional config:
 *   title: "Armoire salle de bain"
 *   device_id: <device id of one specific cabinet>   # to isolate one cabinet
 *   entities: [sensor.doliprane, ...]                # manual override
 */

const CARD_TAG = "medicine-cabinet-card";

const STATUS = {
  EXPIRED: "expired",
  EXPIRING: "expiring",
  LOW_STOCK: "low_stock",
  OK: "ok",
};

const STATUS_LABEL = {
  [STATUS.EXPIRED]: "Périmé",
  [STATUS.EXPIRING]: "Bientôt périmé",
  [STATUS.LOW_STOCK]: "Stock bas",
  [STATUS.OK]: "OK",
};

function formatDate(iso) {
  if (!iso) return null;
  try {
    return new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, {
      day: "numeric",
      month: "long",
      year: "numeric",
    });
  } catch (err) {
    return iso;
  }
}

function relativeDays(days) {
  if (days === null || days === undefined) return null;
  if (days < 0) return `Périmé depuis ${Math.abs(days)} j`;
  if (days === 0) return "Périme aujourd'hui";
  return `Dans ${days} j`;
}

function computeStatus(attrs) {
  if (attrs.is_expired) return STATUS.EXPIRED;
  if (attrs.is_expiring_soon) return STATUS.EXPIRING;
  if (attrs.is_low_stock) return STATUS.LOW_STOCK;
  return STATUS.OK;
}

function getConfigEntryId(hass, entityId) {
  try {
    const entry = hass.entities?.[entityId];
    if (entry?.config_entry_id) return entry.config_entry_id;
    const deviceId = entry?.device_id;
    if (deviceId) {
      const device = hass.devices?.[deviceId];
      if (device?.config_entries?.length) return device.config_entries[0];
    }
  } catch (err) {
    /* older frontends without entity/device registries on hass: degrade gracefully */
  }
  return null;
}

class MedicineCabinetCard extends HTMLElement {
  setConfig(config) {
    this._config = config || {};
    this._filter = "";
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
    }
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._renderBody();
  }

  getCardSize() {
    return 4;
  }

  static getStubConfig() {
    return {};
  }

  connectedCallback() {
    this._render();
  }

  _matchesScope(entityId, state) {
    const cfg = this._config;
    if (Array.isArray(cfg.entities) && cfg.entities.length) {
      return cfg.entities.includes(entityId);
    }
    if (!entityId.startsWith("sensor.")) return false;
    if (state.attributes.id === undefined) return false; // only medication sensors carry an "id"
    if (cfg.device_id) {
      const entry = this._hass.entities?.[entityId];
      if (!entry || entry.device_id !== cfg.device_id) return false;
    }
    return true;
  }

  _medications() {
    const hass = this._hass;
    if (!hass) return [];
    const meds = [];
    for (const [entityId, state] of Object.entries(hass.states)) {
      if (!this._matchesScope(entityId, state)) continue;
      const attrs = state.attributes;
      meds.push({
        entityId,
        name: attrs.friendly_name || state.attributes.id,
        quantity: state.state,
        unit: attrs.unit_of_measurement || "",
        purpose: attrs.purpose,
        category: attrs.category,
        location: attrs.location,
        expirationDate: attrs.expiration_date,
        daysUntilExpiration: attrs.days_until_expiration,
        status: computeStatus(attrs),
        configEntryId: getConfigEntryId(hass, entityId),
        medicationId: attrs.id,
      });
    }
    const filter = this._filter.trim().toLowerCase();
    const filtered = filter
      ? meds.filter((m) =>
          [m.name, m.purpose, m.category]
            .filter(Boolean)
            .some((value) => value.toLowerCase().includes(filter))
        )
      : meds;
    return filtered.sort((a, b) => {
      const aExp = a.daysUntilExpiration;
      const bExp = b.daysUntilExpiration;
      if (aExp === null || aExp === undefined) return 1;
      if (bExp === null || bExp === undefined) return -1;
      return aExp - bExp;
    });
  }

  _callService(domain, service, data) {
    this._hass.callService(domain, service, data);
  }

  _adjust(med, delta) {
    if (!med.configEntryId) return;
    this._callService("medicine_cabinet", delta > 0 ? "restock" : "consume", {
      config_entry_id: med.configEntryId,
      medication_id: med.medicationId,
      amount: Math.abs(delta),
    });
  }

  _openMoreInfo(entityId) {
    const event = new CustomEvent("hass-more-info", {
      bubbles: true,
      composed: true,
      detail: { entityId },
    });
    this.shadowRoot.dispatchEvent(event);
  }

  _render() {
    if (!this.shadowRoot) return;
    this.shadowRoot.innerHTML = `
      <style>${MedicineCabinetCard.styles}</style>
      <ha-card>
        <div class="header">
          <div class="title">${this._config.title || "Armoire à pharmacie"}</div>
          <div class="counts" id="counts"></div>
        </div>
        <div class="search-row">
          <input id="search" type="text" placeholder="Rechercher un médicament..." />
        </div>
        <div class="grid" id="grid"></div>
        <div class="empty" id="empty" hidden>
          Aucun médicament trouvé. Ajoutez-en un via l'action
          <code>medicine_cabinet.add_medication</code>.
        </div>
      </ha-card>
    `;
    this.shadowRoot.getElementById("search").addEventListener("input", (ev) => {
      this._filter = ev.target.value;
      this._renderBody();
    });
    this._renderBody();
  }

  _renderBody() {
    if (!this.shadowRoot || !this._hass) return;
    const grid = this.shadowRoot.getElementById("grid");
    const empty = this.shadowRoot.getElementById("empty");
    const counts = this.shadowRoot.getElementById("counts");
    if (!grid) return;

    const meds = this._medications();

    const summary = { expired: 0, expiring: 0, low_stock: 0 };
    meds.forEach((m) => {
      if (m.status === STATUS.EXPIRED) summary.expired += 1;
      else if (m.status === STATUS.EXPIRING) summary.expiring += 1;
      if (m.status === STATUS.LOW_STOCK) summary.low_stock += 1;
    });

    counts.innerHTML = `
      <span class="chip total">${meds.length} au total</span>
      ${summary.expired ? `<span class="chip expired">${summary.expired} périmé(s)</span>` : ""}
      ${summary.expiring ? `<span class="chip expiring">${summary.expiring} bientôt périmé(s)</span>` : ""}
      ${summary.low_stock ? `<span class="chip low_stock">${summary.low_stock} stock bas</span>` : ""}
    `;

    empty.hidden = meds.length !== 0;
    grid.innerHTML = "";

    meds.forEach((med) => {
      const card = document.createElement("div");
      card.className = `med-card status-${med.status}`;

      const relative = relativeDays(med.daysUntilExpiration);
      const canAdjust = Boolean(med.configEntryId);

      card.innerHTML = `
        <div class="med-main">
          <div class="med-name">${med.name}</div>
          ${med.category ? `<span class="badge">${med.category}</span>` : ""}
        </div>
        ${med.purpose ? `<div class="med-purpose">${med.purpose}</div>` : ""}
        <div class="med-row quantity-row">
          <button class="qty-btn minus" ${canAdjust ? "" : "disabled"} title="Retirer 1">−</button>
          <div class="qty-value">${med.quantity}<span class="unit">${med.unit ? " " + med.unit : ""}</span></div>
          <button class="qty-btn plus" ${canAdjust ? "" : "disabled"} title="Ajouter 1">+</button>
        </div>
        ${
          med.expirationDate
            ? `<div class="med-row expiry-row">
                 <ha-icon icon="mdi:calendar"></ha-icon>
                 <span>${formatDate(med.expirationDate)}</span>
                 ${relative ? `<span class="relative">(${relative})</span>` : ""}
               </div>`
            : `<div class="med-row expiry-row muted">Pas de date de péremption</div>`
        }
        <div class="status-pill status-${med.status}">${STATUS_LABEL[med.status]}</div>
      `;

      card.querySelector(".med-main").addEventListener("click", () =>
        this._openMoreInfo(med.entityId)
      );
      const minusBtn = card.querySelector(".qty-btn.minus");
      const plusBtn = card.querySelector(".qty-btn.plus");
      minusBtn.addEventListener("click", (ev) => {
        ev.stopPropagation();
        this._adjust(med, -1);
      });
      plusBtn.addEventListener("click", (ev) => {
        ev.stopPropagation();
        this._adjust(med, 1);
      });

      grid.appendChild(card);
    });
  }
}

MedicineCabinetCard.styles = `
  ha-card {
    padding: 16px;
  }
  .header {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    margin-bottom: 12px;
  }
  .title {
    font-size: 1.2rem;
    font-weight: 500;
    color: var(--primary-text-color);
  }
  .counts {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }
  .chip {
    font-size: 0.75rem;
    padding: 3px 10px;
    border-radius: 999px;
    background: var(--secondary-background-color);
    color: var(--secondary-text-color);
  }
  .chip.expired {
    background: rgba(var(--rgb-error-color, 219, 68, 55), 0.15);
    color: var(--error-color, #db4437);
  }
  .chip.expiring, .chip.low_stock {
    background: rgba(var(--rgb-warning-color, 255, 152, 0), 0.15);
    color: var(--warning-color, #ff9800);
  }
  .search-row {
    margin-bottom: 12px;
  }
  #search {
    width: 100%;
    box-sizing: border-box;
    padding: 8px 12px;
    border-radius: 8px;
    border: 1px solid var(--divider-color);
    background: var(--card-background-color);
    color: var(--primary-text-color);
    font-size: 0.9rem;
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 12px;
  }
  .empty {
    padding: 24px 8px;
    text-align: center;
    color: var(--secondary-text-color);
  }
  .med-card {
    border-radius: 10px;
    border: 1px solid var(--divider-color);
    border-left: 4px solid var(--success-color, #4caf50);
    padding: 12px;
    background: var(--card-background-color);
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .med-card.status-expired {
    border-left-color: var(--error-color, #db4437);
  }
  .med-card.status-expiring,
  .med-card.status-low_stock {
    border-left-color: var(--warning-color, #ff9800);
  }
  .med-main {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 6px;
    cursor: pointer;
  }
  .med-name {
    font-weight: 600;
    color: var(--primary-text-color);
  }
  .badge {
    font-size: 0.7rem;
    padding: 2px 8px;
    border-radius: 999px;
    background: var(--secondary-background-color);
    color: var(--secondary-text-color);
    white-space: nowrap;
  }
  .med-purpose {
    font-size: 0.8rem;
    color: var(--secondary-text-color);
  }
  .med-row {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.85rem;
    color: var(--primary-text-color);
  }
  .med-row.muted {
    color: var(--secondary-text-color);
    font-style: italic;
  }
  .med-row ha-icon {
    --mdc-icon-size: 16px;
    color: var(--secondary-text-color);
  }
  .relative {
    color: var(--secondary-text-color);
  }
  .quantity-row {
    justify-content: center;
    gap: 12px;
    margin: 4px 0;
  }
  .qty-value {
    font-size: 1.3rem;
    font-weight: 600;
    min-width: 3ch;
    text-align: center;
  }
  .unit {
    font-size: 0.75rem;
    font-weight: 400;
    color: var(--secondary-text-color);
  }
  .qty-btn {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    border: 1px solid var(--divider-color);
    background: var(--secondary-background-color);
    color: var(--primary-text-color);
    font-size: 1rem;
    line-height: 1;
    cursor: pointer;
  }
  .qty-btn:disabled {
    opacity: 0.35;
    cursor: default;
  }
  .status-pill {
    align-self: flex-start;
    font-size: 0.7rem;
    padding: 2px 8px;
    border-radius: 999px;
    background: rgba(var(--rgb-success-color, 76, 175, 80), 0.15);
    color: var(--success-color, #4caf50);
  }
  .status-pill.status-expired {
    background: rgba(var(--rgb-error-color, 219, 68, 55), 0.15);
    color: var(--error-color, #db4437);
  }
  .status-pill.status-expiring, .status-pill.status-low_stock {
    background: rgba(var(--rgb-warning-color, 255, 152, 0), 0.15);
    color: var(--warning-color, #ff9800);
  }
`;

customElements.define(CARD_TAG, MedicineCabinetCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: CARD_TAG,
  name: "Medicine Cabinet",
  description: "Vue façon Grocy de votre armoire à pharmacie (quantités, péremptions, utilité).",
});
