import { Controller } from "@hotwired/stimulus";
import { showMessage } from "../utils/messages";

export default class extends Controller {
  static targets = ["form", "url", "submitButton"];

  connect() {
    console.log("Pricing analysis controller connected");
  }

  async analyze(event) {
    event.preventDefault();

    const url = this.urlTarget.value;
    const projectId = this.formTarget.dataset.projectId;
    const csrfToken = document.querySelector("[name='csrfmiddlewaretoken']").value;

    // Disable submit button and show loading state
    this.submitButtonTarget.disabled = true;
    this.submitButtonTarget.innerHTML = `
      <svg class="mr-2 -ml-1 w-4 h-4 text-white animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
      Analyzing...
    `;

    try {
      const response = await fetch(`/api/add-pricing-page`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken
        },
        body: JSON.stringify({ url, project_id: projectId })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.message || "Network response was not ok");
      }

      // Replace form with success view and Use Agent button
      this.formTarget.innerHTML = `
        <div class="space-y-4">
          <div class="flex justify-end">
            <a href="/pricing-agent/${projectId}/"
               class="inline-flex items-center px-4 py-2 text-sm font-semibold text-white bg-pink-600 rounded-lg shadow-sm hover:bg-pink-700 focus:outline-none focus:ring-2 focus:ring-pink-500 focus:ring-offset-2">
              <svg class="mr-2 w-4 h-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              Use Agent
            </a>
          </div>
        </div>
      `;

    } catch (error) {
      console.error("Error:", error);
      showMessage(error.message || "Error analyzing pricing page. Please try again.", "error");
    } finally {
      if (this.submitButtonTarget) {  // Only reset if we haven't replaced the form
        this.submitButtonTarget.disabled = false;
        this.submitButtonTarget.innerHTML = `
          <svg class="mr-2 w-4 h-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          Analyze Pricing Page
        `;
      }
    }
  }
}
