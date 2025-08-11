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
    const activeTab = document.querySelector('[data-action="title-suggestions#switchTab"].text-gray-900');
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

      // Add the new suggestion to the active suggestions list
      const activeSuggestionsList = document.querySelector("[data-title-suggestions-target='activeSuggestionsList']");
      const suggestionHtml = this.createSuggestionHTML(data.suggestion, contentType);
      activeSuggestionsList.insertAdjacentHTML("beforeend", suggestionHtml);

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
    // Check if target_keywords is an array, a string, or null/undefined
    let keywordsHTML = '';
    if (suggestion.target_keywords) {
      // If it's an array, use it directly
      if (Array.isArray(suggestion.target_keywords)) {
        keywordsHTML = `
          <div class="mb-4">
            <div class="flex flex-wrap gap-2">
              ${suggestion.target_keywords.map(keyword => `
                <span class="inline-flex items-center px-2 py-1 text-xs font-medium text-gray-600 bg-gray-50 border border-gray-200 rounded">
                  ${keyword.trim()}
                </span>
              `).join("")}
            </div>
          </div>
        `;
      }
      // If it's a string, split it
      else if (typeof suggestion.target_keywords === 'string') {
        keywordsHTML = `
          <div class="mb-4">
            <div class="flex flex-wrap gap-2">
              ${suggestion.target_keywords.split(",").map(keyword => `
                <span class="inline-flex items-center px-2 py-1 text-xs font-medium text-gray-600 bg-gray-50 border border-gray-200 rounded">
                  ${keyword.trim()}
                </span>
              `).join("")}
            </div>
          </div>
        `;
      }
    }

    const metaDescriptionHTML = suggestion.suggested_meta_description ? `
      <div class="p-3 bg-gray-50 border border-gray-200 rounded-md mb-4">
        <span class="block text-xs font-medium text-gray-700 mb-1">
          Meta Description
        </span>
        <p class="text-sm text-gray-600">
          ${suggestion.suggested_meta_description}
        </p>
      </div>
    ` : '';

    return `
      <div
        class="border-b border-gray-200 last:border-b-0"
        data-controller="generate-content archive-suggestion"
        data-generate-content-suggestion-id-value="${suggestion.id}"
        data-generate-content-project-id-value="${this.projectIdValue}"
        data-archive-suggestion-suggestion-id-value="${suggestion.id}"
        data-archive-suggestion-archived-value="false"
        data-suggestion-type="${contentType}"
      >
        <div class="p-6">
          <!-- Header with title and status -->
          <div class="flex items-start justify-between mb-4">
            <div class="flex-1">
              <h4 class="text-lg font-semibold text-gray-900 mb-2">
                ${suggestion.title}
              </h4>

              <!-- Status indicator -->
              <div class="flex items-center gap-3">
                <div data-generate-content-target="status">
                  <div class="flex items-center gap-1.5">
                    <div class="w-3 h-3 bg-gray-400 rounded-full"></div>
                    <span class="text-sm text-gray-600">Ready to generate</span>
                  </div>
                </div>

                <!-- Category Badge -->
                <span class="inline-flex items-center px-2 py-1 text-xs font-medium text-gray-700 bg-gray-100 rounded-md">
                  ${suggestion.category}
                </span>
              </div>
            </div>

            <!-- Action Button -->
            <div class="ml-4">
              <div data-generate-content-target="buttonContainer">
                <button
                  data-action="generate-content#generate"
                  class="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-gray-900 border border-gray-900 rounded-md hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-gray-500">
                  <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
                  </svg>
                  Generate
                </button>
              </div>
            </div>
          </div>

          <!-- Description -->
          <p class="text-gray-700 leading-relaxed mb-4">
            ${suggestion.description}
          </p>

          <!-- Keywords -->
          ${keywordsHTML}

          <!-- Meta Description -->
          ${metaDescriptionHTML}

          <!-- Actions Row -->
          <div class="flex items-center justify-between pt-4 border-t border-gray-100">
            <!-- Rating Actions -->
            <div class="flex items-center space-x-3"
                 data-controller="title-score"
                 data-title-score-suggestion-id-value="${suggestion.id}"
                 data-current-score="0">

              <button data-title-score-target="likeButton"
                      data-action="title-score#updateScore"
                      class="inline-flex items-center px-3 py-1.5 text-xs font-medium text-gray-600 border border-gray-300 rounded hover:bg-green-50 hover:text-green-700 hover:border-green-300 transition-colors like">
                <svg class="w-3.5 h-3.5 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5" />
                </svg>
                Like
              </button>

              <button data-title-score-target="dislikeButton"
                      data-action="title-score#updateScore"
                      class="inline-flex items-center px-3 py-1.5 text-xs font-medium text-gray-600 border border-gray-300 rounded hover:bg-red-50 hover:text-red-700 hover:border-red-300 transition-colors dislike">
                <svg class="w-3.5 h-3.5 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018c.163 0 .326.02.485.06L17 4m-7 10v2a2 2 0 002 2h.095c.5 0 .905-.405.905-.905 0-.714.211-1.412.608-2.006L17 13V4m-7 10h2m5-10h2a2 2 0 012 2v6a2 2 0 01-2 2h-2.5" />
                </svg>
                Dislike
              </button>
            </div>

            <!-- Archive Action -->
            <div>
              <button data-action="archive-suggestion#archive"
                      data-archive-suggestion-target="archiveButton"
                      class="inline-flex items-center px-3 py-1.5 text-xs font-medium text-gray-600 border border-gray-300 rounded hover:bg-gray-50 transition-colors">
                <svg xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5 mr-1" viewBox="0 0 20 20" fill="currentColor">
                  <path d="M4 3a2 2 0 100 4h12a2 2 0 100-4H4z"></path>
                  <path fill-rule="evenodd" d="M3 8h14v7a2 2 0 01-2 2H5a2 2 0 01-2-2V8zm5 3a1 1 0 011-1h2a1 1 0 110 2H9a1 1 0 01-1-1z" clip-rule="evenodd"></path>
                </svg>
                Archive
              </button>

              <button data-action="archive-suggestion#unarchive"
                      data-archive-suggestion-target="unarchiveButton"
                      class="inline-flex items-center px-3 py-1.5 text-xs font-medium text-gray-600 border border-gray-300 rounded hover:bg-gray-50 transition-colors hidden">
                <svg xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5 mr-1" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M5 2a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V4a2 2 0 00-2-2H5zm3 8a1 1 0 00-1 1v2a1 1 0 102 0v-2a1 1 0 00-1-1zm3 0a1 1 0 00-1 1v2a1 1 0 102 0v-2a1 1 0 00-1-1z" clip-rule="evenodd" />
                </svg>
                Unarchive
              </button>
            </div>

            <!-- Post Button Integration -->
            <div data-generate-content-target="postButtonContainer"
                 data-has-pro-subscription="false"
                 data-has-auto-submission-setting="false"
                 data-pricing-url="/pricing"
                 data-project-settings-url="/project/${this.projectIdValue}/settings/">
            </div>
          </div>

          <!-- Hidden targets for Stimulus controller compatibility -->
          <div data-generate-content-target="dropdown" class="hidden">
            <div data-generate-content-target="content"></div>
          </div>
        </div>
      </div>
    `;
  }

}
