import { Controller } from "@hotwired/stimulus";

export default class extends Controller {
  static targets = ["rows", "jsonInput"];
  static values = { initial: String };

  connect() {
    // Populate from initial value if present, else one row
    let initial = {};
    try {
      if (this.hasInitialValue && this.initialValue) {
        initial = JSON.parse(this.initialValue);
      }
    } catch (e) {
      initial = {};
    }
    const keys = Object.keys(initial);
    if (keys.length > 0) {
      keys.forEach(key => {
        this.addRow(key, initial[key]);
      });
    } else {
      this.addRow();
    }
    // On form submit, serialize to JSON
    const form = this.element.closest("form");
    if (form) {
      form.addEventListener("submit", () => {
        this.serializeRows();
      });
    }
  }

  addRow(key = "", value = "") {
    if (key instanceof Event || (key && key.constructor && key.constructor.name.endsWith("Event"))) {
      key = "";
      value = "";
    }
    if (!this.hasRowsTarget) {
      return;
    }
    const row = document.createElement("div");
    row.className = "flex gap-2 items-center";
    row.innerHTML = `
      <input type="text" placeholder="Key" class="flex-1 px-2 py-1 rounded border border-gray-300 focus:ring-pink-500 focus:border-pink-500 sm:text-sm" data-auto-submit-header-target="key" value="${key}" />
      <input type="text" placeholder="Value" class="flex-1 px-2 py-1 rounded border border-gray-300 focus:ring-pink-500 focus:border-pink-500 sm:text-sm" data-auto-submit-header-target="value" value="${value}" />
      <button type="button" class="text-xs text-gray-400 hover:text-pink-600" data-action="auto-submit-header#removeRow" title="Remove"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg></button>
    `;
    this.rowsTarget.appendChild(row);
  }

  removeRow(event) {
    event.target.closest(".flex").remove();
    this.serializeRows();
  }

  serializeRows() {
    if (!this.hasRowsTarget) {
      return;
    }
    const rows = this.rowsTarget.querySelectorAll(".flex");
    const obj = {};
    rows.forEach(row => {
      const key = row.querySelector('[data-auto-submit-header-target="key"]').value.trim();
      const value = row.querySelector('[data-auto-submit-header-target="value"]').value.trim();
      if (key) {
        obj[key] = value;
      }
    });
    this.jsonInputTarget.value = JSON.stringify(obj);
  }
}
