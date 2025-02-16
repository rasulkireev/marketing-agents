import { Controller } from "@hotwired/stimulus";
import { showMessage } from "../utils/messages";

export default class extends Controller {
  static values = {
    projectId: Number,
    currentTab: String
  };

  static targets = ["suggestionsList", "suggestionsContainer"];

  connect() {
    this.currentTabValue = "SHARING";
  }

  async switchTab(event) {
    const tab = event.currentTarget.dataset.tab;
    this.currentTabValue = tab;

    // Update tab styles
    const tabs = this.element.querySelectorAll("[data-action='title-suggestions#switchTab']");
    tabs.forEach(t => {
      if (t.dataset.tab === tab) {
        t.classList.add("text-pink-600", "border-b-2", "border-pink-600");
        t.classList.remove("text-gray-500", "hover:text-gray-700", "hover:border-gray-300");
      } else {
        t.classList.remove("text-pink-600", "border-b-2", "border-pink-600");
        t.classList.add("text-gray-500", "hover:text-gray-700", "hover:border-gray-300");
      }
    });

    // Filter suggestions based on type
    const suggestions = this.suggestionsListTarget.querySelectorAll("[data-suggestion-type]");
    suggestions.forEach(suggestion => {
      if (suggestion.dataset.suggestionType === tab) {
        suggestion.classList.remove("hidden");
      } else {
        suggestion.classList.add("hidden");
      }
    });
  }

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
          project_id: this.projectIdValue,
          content_type: this.currentTabValue
        })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || "Failed to generate suggestions");
      }

      const { suggestions, status, message } = await response.json();

      if (status === "error") {
        console.log(message);
        throw new Error(message || "Failed to generate suggestions");
      }

      this.suggestionsContainerTarget.classList.remove('hidden');
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
    const isSEO = this.currentTabValue === "SEO";

    let detailsHTML = isSEO ? `
      <div class="mt-2 space-y-2">
        <div class="flex gap-x-2 items-center">
          <span class="text-sm font-medium text-gray-500">Search Intent:</span>
          <span class="px-2 py-0.5 text-xs text-pink-600 bg-pink-50 rounded-full">${suggestion.search_intent}</span>
        </div>
        <div class="flex gap-x-2 items-center">
          <span class="text-sm font-medium text-gray-500">SEO Score:</span>
          <span class="px-2 py-0.5 text-xs text-pink-600 bg-pink-50 rounded-full">${suggestion.seo_score}%</span>
        </div>
        ${suggestion.target_keywords ? `
          <div class="flex flex-wrap gap-2">
            ${suggestion.target_keywords.map(keyword =>
              `<span class="px-2 py-0.5 text-xs text-gray-600 bg-gray-100 rounded-full">${keyword}</span>`
            ).join('')}
          </div>
        ` : ''}
        ${suggestion.suggested_meta_description ? `
          <div class="mt-2">
            <span class="text-sm font-medium text-gray-500">Meta Description:</span>
            <p class="mt-1 text-sm text-gray-600">${suggestion.suggested_meta_description}</p>
          </div>
        ` : ''}
      </div>
    ` : `
      <span class="mt-1 text-sm text-gray-500">Category: ${suggestion.category}</span>
    `;

    return `
      <div class="pl-4 border-l-4 border-pink-600 animate-enter"
           data-controller="generate-content"
           data-generate-content-suggestion-id-value="${suggestion.id}"
           data-suggestion-type="${this.currentTabValue}">
        <div class="flex justify-between items-start">
          <div class="flex-1">
            <h4 class="text-lg font-semibold text-gray-900">${suggestion.title}</h4>
            <p class="mt-2 text-gray-600">${suggestion.description}</p>
            ${detailsHTML}
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
