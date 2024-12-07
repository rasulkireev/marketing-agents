import { Controller } from "@hotwired/stimulus";

export default class extends Controller {
  static targets = ["content", "chevron"];

  connect() {
    this.expanded = true;
  }

  toggle() {
    this.expanded = !this.expanded;

    if (this.hasContentTarget) {
      this.contentTarget.classList.toggle("hidden");
    }

    if (this.hasChevronTarget) {
      this.chevronTarget.classList.toggle("rotate-180");
    }
  }
}
