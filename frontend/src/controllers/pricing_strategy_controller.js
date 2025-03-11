import { Controller } from "@hotwired/stimulus";
import { showMessage } from "../utils/messages";

export default class extends Controller {
  static targets = ["createButton"];

  async createStrategy(event) {
    event.preventDefault();
    const button = this.createButtonTarget;
    const projectId = window.location.pathname.split("/")[2]; // Get project ID from URL
    const csrfToken = document.querySelector("[name='csrfmiddlewaretoken']").value;

    // Disable button and show loading state
    button.disabled = true;
    const originalContent = button.innerHTML;
    button.innerHTML = `
      <svg class="mr-2 -ml-1 w-4 h-4 text-white animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
      Generating...
    `;

    try {
      const response = await fetch("/api/create-pricing-strategy", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken
        },
        body: JSON.stringify({
          project_id: projectId,
          strategy_name: "Alex Hormozi", // Using default strategy
          user_prompt: "" // Using default empty prompt
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.message || "Failed to create strategy");
      }

      // Reload the page to show the new strategy
      window.location.reload();

    } catch (error) {
      console.error("Error:", error);
      showMessage(error.message || "Error creating strategy. Please try again.", "error");

      // Reset button state
      button.disabled = false;
      button.innerHTML = originalContent;
    }
  }
}
