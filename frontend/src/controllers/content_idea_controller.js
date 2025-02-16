import { Controller } from "@hotwired/stimulus";
import { showMessage } from "../utils/messages";

export default class extends Controller {
  static targets = ["form", "input"];
  static values = {
    projectId: Number
  };

  toggleForm() {
    this.formTarget.classList.toggle("hidden");
  }

  getCurrentTab() {
    // Find the active tab button
    const activeTab = document.querySelector('[data-action="title-suggestions#switchTab"].text-pink-600');
    return activeTab ? activeTab.dataset.tab : "SHARING"; // Default to SHARING if no tab is active
  }

  async generate() {
    const idea = this.inputTarget.value.trim();
    if (!idea) return;

    const button = this.element.querySelector('[data-action="content-idea#generate"]');
    const contentType = this.getCurrentTab();

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
          user_prompt: idea,
          content_type: contentType
        })
      });

      if (!response.ok) {
        throw new Error("Failed to generate title suggestion");
      }

      const data = await response.json();

      if (data.status === "error") {
        throw new Error(data.message);
      }

      // Add the new suggestion to the list
      const suggestionsList = document.querySelector("[data-title-suggestions-target='suggestionsList']");
      const suggestionHtml = this.createSuggestionHTML(data.suggestion, contentType);
      suggestionsList.insertAdjacentHTML("beforeend", suggestionHtml);

      // Clear the input and hide the form
      this.inputTarget.value = "";
      this.formTarget.classList.add("hidden");

      // Show the suggestions container if it was hidden
      document.querySelector("[data-title-suggestions-target='suggestionsContainer']")
        .classList.remove("hidden");

    } catch (error) {
      showMessage(error.message || "Failed to generate suggestion. Please try again later.", 'error');
    } finally {
      // Restore button state
      button.disabled = false;
      button.innerHTML = "Generate";
    }
  }

  createSuggestionHTML(suggestion, contentType) {
    return `
      <div class="pl-4 border-l-4 border-pink-600"
           data-controller="generate-content"
           data-generate-content-suggestion-id-value="${suggestion.id}"
           data-suggestion-type="${contentType}">
        <!-- Header section with toggle -->
        <div class="flex justify-between items-start">
          <div class="flex-1 p-6 bg-white rounded-lg shadow-sm">
            <!-- Title -->
            <h4 class="text-xl font-bold tracking-tight text-gray-900">
              ${suggestion.title}
            </h4>

            <!-- Main Description -->
            <p class="mt-3 leading-relaxed text-gray-700">
              ${suggestion.description}
            </p>

            <!-- Category Badge -->
            <div class="mt-4">
              <span class="inline-flex items-center px-3 py-1 text-sm font-medium text-blue-800 bg-blue-100 rounded-full">
                Category: ${suggestion.category}
              </span>
            </div>

            <!-- Keywords Section -->
            ${suggestion.target_keywords ? `
              <div class="flex flex-wrap gap-2 mt-4">
                ${suggestion.target_keywords.map(keyword => `
                  <span class="px-3 py-1 text-xs font-medium text-gray-600 bg-gray-100 rounded-full">
                    ${keyword}
                  </span>
                `).join('')}
              </div>
            ` : ''}

            <!-- Meta Description Section -->
            ${suggestion.suggested_meta_description ? `
              <div class="p-4 mt-4 bg-gray-50 rounded-md">
                <span class="block mb-2 text-sm font-semibold text-gray-700">
                  Meta Description
                </span>
                <p class="text-sm leading-relaxed text-gray-600">
                  ${suggestion.suggested_meta_description}
                </p>
              </div>
            ` : ''}
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

        <!-- Dropdown content -->
        <div data-generate-content-target="dropdown" class="hidden mt-4">
          <div data-generate-content-target="content"></div>
        </div>
      </div>
    `;
  }

}
