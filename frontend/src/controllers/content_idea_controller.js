import { Controller } from "@hotwired/stimulus";

export default class extends Controller {
  static targets = ["form", "input"];
  static values = {
    projectId: Number
  };

  toggleForm() {
    this.formTarget.classList.toggle("hidden");
  }

  async generate() {
    const idea = this.inputTarget.value.trim();
    if (!idea) return;

    const button = this.element.querySelector('[data-action="content-idea#generate"]');

    try {
      // Show loading state
      button.disabled = true;
      button.innerHTML = `
        <div class="flex gap-x-2 items-center">
          <div class="w-4 h-4 rounded-full border-2 animate-spin border-white/20 border-t-white"></div>
          <span>Generating...</span>
        </div>
      `;

      const response = await fetch("/api/generate-title-from-idea", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]").value
        },
        body: JSON.stringify({
          project_id: this.projectIdValue,
          user_prompt: idea
        })
      });

      if (!response.ok) {
        throw new Error("Failed to generate title suggestion");
      }

      const data = await response.json();

      // Add the new suggestion to the list
      const suggestionsList = document.querySelector("[data-title-suggestions-target='suggestionsList']");
      const suggestionHtml = this.createSuggestionHTML(data.suggestion);
      suggestionsList.insertAdjacentHTML("beforeend", suggestionHtml);

      // Clear the input and hide the form
      this.inputTarget.value = "";
      this.formTarget.classList.add("hidden");

      // Show the suggestions container if it was hidden
      document.querySelector("[data-title-suggestions-target='suggestionsContainer']")
        .classList.remove("hidden");

    } catch (error) {
      console.error("Error:", error);
      alert("Failed to generate suggestion. Please try again.");
    } finally {
      // Restore button state
      button.disabled = false;
      button.innerHTML = "Generate";
    }
  }

  createSuggestionHTML(suggestion) {
    return `
      <div class="pl-4 border-l-4 border-pink-600 animate-enter"
           data-controller="generate-content"
           data-generate-content-suggestion-id-value="${suggestion.id}">
        <div class="flex justify-between items-start">
          <div class="flex-1">
            <h4 class="text-lg font-semibold text-gray-900">${suggestion.title}</h4>
            <p class="mt-2 text-gray-600">${suggestion.description}</p>
            <span class="mt-1 text-sm text-gray-500">Category: ${suggestion.category}</span>
          </div>

          <div class="flex gap-x-3 items-center">
            <div data-generate-content-target="status"></div>
            <div data-generate-content-target="buttonContainer">
              <button
                data-action="generate-content#generate"
                class="px-3 py-1 text-sm font-semibold text-white bg-pink-600 rounded-md hover:bg-pink-700">
                Generate
              </button>
            </div>
          </div>
        </div>

        <div data-generate-content-target="dropdown" class="hidden mt-4">
          <div data-generate-content-target="content"></div>
        </div>
      </div>
    `;
  }
}
