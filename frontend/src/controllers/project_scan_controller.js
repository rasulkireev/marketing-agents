import { Controller } from "@hotwired/stimulus";

export default class extends Controller {
  static targets = [
    "form",
    "result",
    "spinner",
    "submitButton",
    "progressTemplate",
    "checkmarkTemplate",
    "projectDetailsTemplate",
    "titleSuggestionsTemplate",
    "suggestionTemplate",
    "analysisStep",
    "generationStep",
    "urlDisplay",
    "projectName",
    "projectSummary",
    "suggestionsList",
    "nameDisplay",
    "descriptionDisplay",
    "projectInfo"
  ];

  connect() {
    this.hasUpdatedUI = false;
    this.loadStoredProject();
    this.pollInterval = null;
  }

  disconnect() {
    this.stopPolling();
  }

  loadStoredProject() {
    const storedProject = localStorage.getItem('currentProject');
    if (storedProject) {
      const project = JSON.parse(storedProject);
      this.startProgress(project);
    }
  }

  startProgress(project) {
    // Clone and insert progress template
    const progressContent = this.progressTemplateTarget.content.cloneNode(true);
    this.resultTarget.innerHTML = '';
    this.resultTarget.appendChild(progressContent);

    // Update URL display
    this.urlDisplayTarget.textContent = project.url;

    // Hide project info initially
    this.projectInfoTarget.style.display = 'none';

    // Start polling for status
    this.startPolling(project.id);
  }


  startPolling(projectId) {
    this.stopPolling(); // Clear any existing interval
    this.hasUpdatedUI = false; // Add a flag to track if UI has been updated

    this.pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`/project/${projectId}/status/`);
        if (!response.ok) throw new Error('Status check failed');

        const data = await response.json();

        // Update stored project data with latest from server
        if (data.status === 'success') {
          localStorage.setItem('currentProject', JSON.stringify(data.project));

          // Only update UI if we haven't done so already and have suggestions
          const project = data.project;
          if (!this.hasUpdatedUI && project.title_suggestions && project.title_suggestions.length > 0) {
            this.updateProgressComplete();
            this.hasUpdatedUI = true; // Mark UI as updated
            this.stopPolling();
            return;
          }
        }

        if (data.completed && !this.hasUpdatedUI) {
          this.updateProgressComplete();
          this.hasUpdatedUI = true;
          this.stopPolling();
        }
      } catch (error) {
        console.error('Status check error:', error);
      }
    }, 2000); // Poll every 2 seconds
  }

  stopPolling() {
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
      this.pollInterval = null;
    }
  }

  updateProgressComplete() {
    // Replace spinning wheel with checkmark for analysis step
    const analysisSpinner = this.analysisStepTarget.querySelector('svg');
    const checkmark = this.checkmarkTemplateTarget.content.cloneNode(true);
    analysisSpinner.replaceWith(checkmark);

    // Show project info
    const storedProject = JSON.parse(localStorage.getItem('currentProject'));
    if (storedProject) {
      this.nameDisplayTarget.textContent = storedProject.name;
      this.descriptionDisplayTarget.textContent = storedProject.summary;
      this.projectInfoTarget.style.display = 'block';
    }

    // Update generation step
    const generationStep = this.generationStepTarget;
    const generationSpinner = generationStep.querySelector('svg');
    const generationCheckmark = this.checkmarkTemplateTarget.content.cloneNode(true);
    generationSpinner.replaceWith(generationCheckmark);

    // Update generation step text color
    generationStep.querySelector('span').classList.remove('text-gray-400');
    generationStep.querySelector('span').classList.add('text-gray-600');

    // Show project details
    this.showProjectDetails();
  }

  showProjectDetails() {
    const storedProject = JSON.parse(localStorage.getItem('currentProject'));
    if (!storedProject) return;

    // Add project details
    const detailsContent = this.projectDetailsTemplateTarget.content.cloneNode(true);
    this.resultTarget.appendChild(detailsContent);

    this.projectNameTarget.textContent = storedProject.name;
    this.projectSummaryTarget.textContent = storedProject.summary;

    // Add title suggestions
    if (storedProject.title_suggestions && storedProject.title_suggestions.length > 0) {
      const suggestionsContent = this.titleSuggestionsTemplateTarget.content.cloneNode(true);
      this.resultTarget.appendChild(suggestionsContent);

      this.renderSuggestions(storedProject.title_suggestions);
    }
  }

  renderSuggestions(suggestions) {
    this.suggestionsListTarget.innerHTML = '';

    suggestions.forEach((suggestion, index) => {
      const suggestionElement = this.suggestionTemplateTarget.content.cloneNode(true);
      const container = suggestionElement.querySelector('div');

      const [titleSpan, descSpan, catSpan] = container.querySelectorAll('.font-medium');
      titleSpan.textContent = suggestion.title;
      descSpan.textContent = suggestion.description;
      catSpan.textContent = suggestion.category;

      // Blur all suggestions except first two
      if (index >= 2) {
        container.classList.add('blur-sm', 'pointer-events-none');
      }

      this.suggestionsListTarget.appendChild(container);
    });
  }

  showAllSuggestions(event) {
    const suggestions = this.suggestionsListTarget.querySelectorAll('div');
    suggestions.forEach(suggestion => {
      suggestion.classList.remove('blur-sm', 'pointer-events-none');
    });

    // Hide the "Show All" button
    event.target.style.display = 'none';
  }

  async scan(event) {
    event.preventDefault();

    try {
      const formData = new FormData(this.formTarget);
      const response = await fetch('/scan/', {
        method: "POST",
        body: formData,
        headers: {
          "X-CSRFToken": formData.get("csrfmiddlewaretoken"),
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      if (data.status === 'success') {
        // Store project data in localStorage
        localStorage.setItem('currentProject', JSON.stringify(data.project));
        this.startProgress(data.project);

        // Clear form
        this.formTarget.reset();
      } else {
        throw new Error(data.message || 'Something went wrong');
      }

    } catch (error) {
      console.error("Error:", error);
      this.resultTarget.innerHTML = `
        <div class="p-4 mt-4 bg-red-50 rounded-lg">
          <p class="text-sm text-red-600">
            ${error.message || 'Something went wrong. Please try again.'}
          </p>
        </div>
      `;
    }
  }

  clearStoredProject() {
    localStorage.removeItem('currentProject');
    this.resultTarget.innerHTML = '';
    this.stopPolling();
    this.hasUpdatedUI = false;
  }
}
