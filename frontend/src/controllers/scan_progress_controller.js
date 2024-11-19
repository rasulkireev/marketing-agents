import { Controller } from "@hotwired/stimulus";

export default class extends Controller {
  static targets = [
    "progress",
    "error",
    "detailsSpinner",
    "detailsCheck",
    "suggestionsSpinner",
    "suggestionsCheck",
    "resultsButton",
    "projectsList"
  ];

  async handleSubmit(event) {
    event.preventDefault();

    // Reset UI state
    if (this.hasErrorTarget) {
      this.errorTarget.classList.add('hidden');
    }
    this.progressTarget.classList.remove('hidden');

    const form = event.target;
    const formData = new FormData(form);

    try {
      // Initial scan
      const response = await fetch('/api/scan', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.getCSRFToken(),
        },
        body: JSON.stringify({
          url: formData.get('url')
        })
      });

      if (!response.ok) {
        throw new Error('Failed to scan URL');
      }

      const scanData = await response.json();
      console.log('Scan response:', scanData);

      // Update UI for project details
      this.detailsSpinnerTarget.classList.add('hidden');
      this.detailsCheckTarget.classList.remove('hidden');

      // Start suggestions spinner animation
      this.suggestionsSpinnerTarget.classList.add('animate-spin', 'border-t-pink-600');

      // Generate title suggestions
      const suggestionsResponse = await fetch('/api/generate-title-suggestions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.getCSRFToken(),
        },
        body: JSON.stringify({
          project_id: scanData.project_id
        })
      });

      if (!suggestionsResponse.ok) {
        throw new Error('Failed to generate title suggestions');
      }

      // Update UI for suggestions
      this.suggestionsSpinnerTarget.classList.add('hidden');
      this.suggestionsCheckTarget.classList.remove('hidden');

      // Add new project to the list with animation after both API calls succeed
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

      // Show results button
      this.resultsButtonTarget.href = `/project/${scanData.project_id}/`;
      this.resultsButtonTarget.classList.remove('hidden');

    } catch (error) {
      console.error('Error:', error);
      this.progressTarget.classList.add('hidden');

      if (!this.hasErrorTarget) {
        const errorDiv = document.createElement('div');
        errorDiv.setAttribute('data-scan-progress-target', 'error');
        errorDiv.className = 'mt-2 text-sm text-red-600';
        this.element.appendChild(errorDiv);
      }

      this.errorTarget.classList.remove('hidden');
      this.errorTarget.textContent = error.message;
    }
  }

  getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
  }

  createProjectElement(data) {
    const element = document.createElement('div');
    element.className = 'flex justify-between items-center p-5 bg-white rounded-lg border shadow-sm opacity-0 transition-all duration-500 ease-out transform translate-x-full';
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
           class="px-2.5 py-1.5 text-sm font-semibold text-gray-900 bg-white rounded-md ring-1 ring-inset ring-gray-300 shadow-sm hover:bg-gray-50">
          View details
        </a>
      </div>
    `;
    return element;
  }
}
