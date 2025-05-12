import { Controller } from "@hotwired/stimulus";
import { showMessage } from "../utils/messages";

export default class extends Controller {
  static targets = [
    "progress",
    "error",
    "detailsSpinner",
    "detailsCheck",
    "detailsCross",
    "suggestionsSpinner",
    "suggestionsCheck",
    "suggestionsCross",
    "resultsButton",
    "projectsList",
    "backgroundTasks"
  ];

  async handleSubmit(event) {
    event.preventDefault();
    this.initializeUI();

    const formData = new FormData(event.target);
    const url = formData.get('url');

    try {
      // Perform scan first
      const scanData = await this.performScan(url);

      // Add project to list and update results button immediately after successful scan
      this.addProjectToList(scanData);
      this.updateResultsButton(scanData.project_id);
    } catch (scanError) {
      this.handleScanError(scanError);
    }
  }

  initializeUI() {
    if (this.hasErrorTarget) {
      this.errorTarget.classList.add('hidden');
    }
    this.progressTarget.classList.remove('hidden');
  }

  async performScan(url) {
    const scanResponse = await fetch('/api/scan', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': this.getCSRFToken(),
      },
      body: JSON.stringify({ url })
    });

    if (!scanResponse.ok) {
      throw new Error('Failed to scan URL');
    }

    const scanData = await scanResponse.json();
    if (scanData.status === 'error') {
      throw new Error(scanData.message);
    }

    // Update UI after successful scan
    this.detailsSpinnerTarget.classList.add('hidden');
    this.detailsCheckTarget.classList.remove('hidden');
    // Show background tasks message
    if (this.hasBackgroundTasksTarget) {
      const el = this.backgroundTasksTarget;
      el.classList.remove('hidden');
      // Force reflow to ensure transition
      void el.offsetWidth;
      el.classList.remove('translate-x-full', 'opacity-0', 'pointer-events-none');
      el.classList.add('translate-x-0', 'opacity-100', 'pointer-events-auto');
    }

    return scanData;
  }

  async generateSuggestions(projectId, contentType="SHARING") {
    const suggestionsResponse = await fetch('/api/generate-title-suggestions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': this.getCSRFToken(),
      },
      body: JSON.stringify({
        project_id: projectId,
        content_type: contentType
      })
    });

    if (!suggestionsResponse.ok) {
      throw new Error('Failed to generate title suggestions');
    }

    const suggestionsData = await suggestionsResponse.json();
    if (suggestionsData.status === "error") {
      throw new Error(suggestionsData.message);
    }

    return suggestionsData;
  }

  handleScanError(error) {
    this.detailsSpinnerTarget.classList.add('hidden');
    this.detailsCheckTarget.classList.add('hidden');
    this.detailsCrossTarget.classList.remove('hidden');
    showMessage(error.message || "Failed to scan URL", 'error');
  }

  handleSuggestionsError(error) {
    this.suggestionsCheckTarget.classList.add('hidden');
    this.suggestionsSpinnerTarget.classList.add('hidden');
    this.suggestionsCrossTarget.classList.remove('hidden');
    showMessage(error.message || "Failed to generate suggestions", 'error');
  }

  addProjectToList(scanData) {
    const projectElement = this.createProjectElement(scanData);
    if (this.hasProjectsListTarget) {
      this.projectsListTarget.insertBefore(projectElement, this.projectsListTarget.firstChild);
    } else {
      this.projectsListTarget.appendChild(projectElement);
    }

    const emptyState = document.querySelector('[data-empty-state]');
    if (emptyState) {
      emptyState.remove();
    }

    setTimeout(() => {
      projectElement.classList.remove('translate-x-full', 'opacity-0');
    }, 100);
  }

  updateResultsButton(projectId) {
    this.resultsButtonTarget.href = `/project/${projectId}/`;
    this.resultsButtonTarget.classList.remove('hidden');
  }

  getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
  }

  createProjectElement(data) {
    const element = document.createElement('div');
    element.className = 'overflow-hidden p-4 rounded-xl border border-pink-100 shadow-lg backdrop-blur-sm transition-all duration-300 transform md:p-8 bg-white/90 hover:shadow-xl hover:border-pink-200 hover:-translate-y-1';

    element.innerHTML = `
      <div class="flex flex-col h-full">
        <!-- Header -->
        <div class="flex gap-x-3 items-center space-y-2">
          <h3 class="text-2xl font-bold text-gray-900">
            ${data.name || data.url}
          </h3>
          <span class="px-2.5 py-1 text-xs font-semibold text-pink-700 bg-pink-50 rounded-full ring-1 ring-inset ring-pink-600/20">
            ${data.type}
          </span>
        </div>

        ${data.summary ? `<p class="mt-4 text-sm text-left text-gray-600 line-clamp-4">${data.summary}</p>` : ''}

        <!-- View Details Button -->
        <div class="flex justify-center pt-6 mt-auto md:justify-end">
          <a href="/project/${data.project_id}/"
             class="px-4 py-2 text-sm font-semibold text-white bg-gradient-to-r from-pink-500 to-purple-600 rounded-lg shadow-sm transition-all duration-300 hover:from-pink-600 hover:to-purple-700">
            View details →
          </a>
        </div>
      </div>
    `;
    return element;
  }
}
