import { Controller } from "@hotwired/stimulus";
import { showMessage } from "../utils/messages";


export default class extends Controller {
  static values = {
    projectId: Number
  };

  static targets = ["suggestionsList", "suggestionsContainer"];

  async generate(event) {
    event.preventDefault();
    const button = event.currentTarget;

    try {
      // Show loading state
      button.disabled = true;
      button.innerHTML = `
        <div class="flex gap-x-2 items-center">
          <div class="w-4 h-4 rounded-full border-2 animate-spin border-white/20 border-t-white"></div>
          <span>Generating...</span>
        </div>
      `;

      // Make API call
      const response = await fetch('/api/generate-title-suggestions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': document.querySelector("[name=csrfmiddlewaretoken]").value
        },
        body: JSON.stringify({
          project_id: this.projectIdValue
        })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || "Failed to generate suggestions");
      }

      this.suggestionsContainerTarget.classList.remove('hidden');
      const { suggestions, status, message } = await response.json();

      if (status === "error") {
        console.log(message);
        throw new Error(message || "Failed to generate suggestions");
      }

      // Insert new suggestions
      suggestions.forEach(suggestion => {
        const suggestionHtml = this.createSuggestionHTML(suggestion);
        this.suggestionsListTarget.insertAdjacentHTML('beforeend', suggestionHtml);
      });

      // Restore button state
      button.disabled = false;
      button.innerHTML = "Generate More";

    } catch (error) {
      button.disabled = false;
      button.innerHTML = `Generate ${this.suggestionsListTarget.children.length ? 'More' : 'Post'} Suggestions`;

      showMessage(error.message, 'error');
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
