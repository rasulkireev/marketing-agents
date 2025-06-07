import { Controller } from "@hotwired/stimulus";

export default class extends Controller {
  static targets = ["list"];
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
