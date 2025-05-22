import { Controller } from "@hotwired/stimulus";

export default class extends Controller {
  static values = { message: String };

  connect() {
    this.tooltipElement = document.createElement("div");
    this.tooltipElement.className = "hidden absolute z-10 px-3 py-2 text-sm font-medium text-white bg-gray-900 rounded-lg shadow-sm dark:bg-gray-700";
    this.tooltipElement.textContent = this.messageValue;
    document.body.appendChild(this.tooltipElement);
  }

  disconnect() {
    this.tooltipElement.remove();
  }

  show() {
    this.tooltipElement.classList.remove("hidden");
    this._positionTooltip();
  }

  hide() {
    this.tooltipElement.classList.add("hidden");
  }

  _positionTooltip() {
    const rect = this.element.getBoundingClientRect();
    this.tooltipElement.style.left = `${rect.left + window.scrollX}px`;
    this.tooltipElement.style.top = `${rect.bottom + window.scrollY + 5}px`; // 5px offset
  }
}
