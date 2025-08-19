import { Controller } from "@hotwired/stimulus";

export default class extends Controller {
  static targets = ["list", "icon"];
  static values = { name: String };

  connect() {
    this.boundMove = this.move.bind(this);
    window.addEventListener("suggestion:move", this.boundMove);
  }

  disconnect() {
    window.removeEventListener("suggestion:move", this.boundMove);
  }

  toggle() {
    this.listTarget.classList.toggle("hidden");

    // Rotate the chevron icon if it exists
    if (this.hasIconTarget) {
      if (this.listTarget.classList.contains("hidden")) {
        // Collapsed state - no rotation
        this.iconTarget.classList.remove("rotate-180");
      } else {
        // Expanded state - rotate 180 degrees
        this.iconTarget.classList.add("rotate-180");
      }
    }
  }

  add(element) {
    this.listTarget.appendChild(element);
  }

  move(event) {
    const { element, destination } = event.detail;
    if (this.nameValue === destination) {
      this.add(element);
    }
  }
}
