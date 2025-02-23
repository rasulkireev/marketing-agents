import { Controller } from "@hotwired/stimulus";
import { showMessage } from "../utils/messages";

export default class extends Controller {
  static values = {
    projectId: Number,
    currentTab: String
  };

  static targets = ["suggestionsList", "suggestionsContainer"];

  connect() {
    // Get the last selected tab from localStorage, default to "SHARING" if none exists
    this.currentTabValue = localStorage.getItem("selectedTab") || "SHARING";

    // Update initial tab UI
    const tabs = this.element.querySelectorAll("[data-action='title-suggestions#switchTab']");
    tabs.forEach(t => {
      if (t.dataset.tab === this.currentTabValue) {
        t.classList.add("text-pink-600", "border-b-2", "border-pink-600");
        t.classList.remove("text-gray-500", "hover:text-gray-700", "hover:border-gray-300");
      } else {
        t.classList.remove("text-pink-600", "border-b-2", "border-pink-600");
        t.classList.add("text-gray-500", "hover:text-gray-700", "hover:border-gray-300");
      }
    });

    // Filter suggestions based on initial tab
    this.filterSuggestions();
  }

  switchTab(event) {
    const selectedTab = event.currentTarget.dataset.tab;
    this.currentTabValue = selectedTab;
    localStorage.setItem("selectedTab", selectedTab);

    // Update tab UI
    const tabs = this.element.querySelectorAll("[data-action='title-suggestions#switchTab']");
    tabs.forEach(t => {
      if (t.dataset.tab === selectedTab) {
        t.classList.add("text-pink-600", "border-b-2", "border-pink-600");
        t.classList.remove("text-gray-500", "hover:text-gray-700", "hover:border-gray-300");
      } else {
        t.classList.remove("text-pink-600", "border-b-2", "border-pink-600");
        t.classList.add("text-gray-500", "hover:text-gray-700", "hover:border-gray-300");
      }
    });

    this.filterSuggestions();
  }

  filterSuggestions() {
    const suggestions = this.suggestionsListTarget.querySelectorAll("[data-suggestion-type]");

    suggestions.forEach(suggestion => {
      if (suggestion.dataset.suggestionType === this.currentTabValue) {
        suggestion.classList.remove("hidden");
      } else {
        suggestion.classList.add("hidden");
      }
    });
  }

  createSuggestionHTML(suggestion, contentType) {
    return `
      <div
        class="pl-4 border-l-4 border-pink-600"
        data-controller="generate-content"
        data-generate-content-suggestion-id-value="${suggestion.id}"
        data-suggestion-type="${contentType}"
      >
        <div class="flex gap-x-4 justify-between items-start">
          <div class="flex-1 p-6 bg-white rounded-lg shadow-sm">
            <div class="space-y-4">
              <h4 class="text-xl font-bold tracking-tight text-gray-900">
                ${suggestion.title}
              </h4>

              <div class="flex items-center space-x-2"
                   data-title-score-suggestion-id-value="${suggestion.id}"
                   data-current-score="0">

                <button data-title-score-target="likeButton"
                        data-action="title-score#updateScore"
                        class="inline-flex gap-x-1 items-center px-2 py-1.5 text-sm font-medium rounded-md transition-colors duration-200 like hover:bg-green-50">
                  <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5" />
                  </svg>
                  <span>Like</span>
                </button>

                <button data-title-score-target="dislikeButton"
                        data-action="title-score#updateScore"
                        class="inline-flex gap-x-1 items-center px-2 py-1.5 text-sm font-medium rounded-md transition-colors duration-200 dislike hover:bg-red-50">
                  <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018c.163 0 .326.02.485.06L17 4m-7 10v2a2 2 0 002 2h.095c.5 0 .905-.405.905-.905 0-.714.211-1.412.608-2.006L17 13V4m-7 10h2m5-10h2a2 2 0 012 2v6a2 2 0 01-2 2h-2.5" />
                  </svg>
                  <span>Dislike</span>
                </button>
              </div>
            </div>

            <p class="mt-3 leading-relaxed text-gray-700">
              ${suggestion.description}
            </p>

            <div class="mt-4">
              <span class="inline-flex items-center px-3 py-1 text-sm font-medium text-blue-800 bg-blue-100 rounded-full">
                Category: ${suggestion.category}
              </span>
            </div>

            ${suggestion.target_keywords ? `
              <div class="mt-4">
                <h5 class="text-sm font-medium text-gray-700">Target Keywords:</h5>
                <div class="flex flex-wrap gap-2 mt-2">
                  ${suggestion.target_keywords.split(",").map(keyword => `
                    <span class="inline-flex items-center px-2.5 py-0.5 text-xs font-medium text-gray-800 bg-gray-100 rounded-full">
                      ${keyword.trim()}
                    </span>
                  `).join("")}
                </div>
              </div>
            ` : ""}

            <div data-generate-content-target="buttonContainer" class="mt-4">
              <button
                data-action="generate-content#generate"
                class="px-3 py-1 text-sm font-semibold text-white bg-pink-600 rounded-md hover:bg-pink-700">
                Generate
              </button>
            </div>
          </div>
        </div>
      </div>
    `;
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

      showMessage("Triggered Content Generation, shouldn't take too long 😄", 'success');

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
        const suggestionHtml = this.createSuggestionHTML(suggestion, this.currentTabValue);
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
}
