import { Controller } from "@hotwired/stimulus";

export default class extends Controller {
  static targets = ["source", "button"];

  async copy() {
    const text = this.sourceTarget.value;
    await navigator.clipboard.writeText(text);

    // Update button
    const button = this.buttonTarget;
    button.textContent = "Copied!";
    button.classList.remove(
      "bg-pink-600",
      "hover:bg-pink-700"
    );
    button.classList.add(
      "bg-green-600",
      "hover:bg-green-700",
      "text-white",  // Add this line
      "z-10"
    );

    setTimeout(() => {
      button.textContent = "Copy";
      button.classList.remove(
        "bg-green-600",
        "hover:bg-green-700"
      );
      button.classList.add(
        "bg-pink-600",
        "hover:bg-pink-700"
      );
    }, 2000);
  }
}
