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
    "projectsList"
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

      try {
        // Start suggestions spinner
        this.suggestionsSpinnerTarget.classList.add('animate-spin', 'border-t-pink-600');

        // Generate both types of suggestions
        await this.generateSuggestions(scanData.project_id, "SHARING");
        await this.generateSuggestions(scanData.project_id, "SEO");

        // Show check mark only after both suggestions are complete
        this.suggestionsSpinnerTarget.classList.add('hidden');
        this.suggestionsCheckTarget.classList.remove('hidden');

        this.updateResultsButton(scanData.project_id);
      } catch (suggestionsError) {
        this.handleSuggestionsError(suggestionsError);
      }
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
    element.className = 'flex gap-x-6 justify-between items-center p-6 rounded-xl border border-pink-100 shadow-md backdrop-blur-sm transition-all duration-300 transform bg-white/90 hover:shadow-lg hover:border-pink-200 hover:-translate-y-1';
    element.innerHTML = `
      <div class="min-w-0">
        <div class="flex gap-x-3 items-start">
          <h3 class="font-semibold leading-6 text-gray-900">
            ${data.name || data.url}
          </h3>
          <p class="px-1.5 py-0.5 mt-0.5 text-xs font-medium text-gray-600 whitespace-nowrap bg-gray-50 rounded-md ring-1 ring-inset ring-gray-500/10">
            ${data.type}
          </p>
        </div>
        ${data.summary ? `<p class="mt-1 text-sm leading-5 text-gray-500 truncate">${data.summary}</p>` : ''}
      </div>
      <div class="flex flex-none gap-x-4 items-center">
        <a href="/project/${data.project_id}/"
           class="px-4 py-2 text-sm font-semibold text-gray-900 bg-white rounded-lg ring-2 ring-pink-200 shadow-sm transition-all duration-300 hover:bg-pink-50 hover:ring-pink-300">
          View details →
        </a>
      </div>
    `;
    return element;
  }
}
