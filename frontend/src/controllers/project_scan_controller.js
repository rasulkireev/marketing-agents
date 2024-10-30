import { Controller } from "@hotwired/stimulus";

export default class extends Controller {
  static targets = [
    "form",
    "result",
    "spinner",
    "submitButton",
    "progressTemplate",
    "checkmarkTemplate",
    "analysisStep",
    "generationStep",
    "urlDisplay"
  ];

  connect() {
    console.log("Project scan controller connected");
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

    // Start polling for status
    this.startPolling(project.id);
  }

  startPolling(projectId) {
    this.stopPolling(); // Clear any existing interval

    this.pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`/project/${projectId}/status/`);
        if (!response.ok) throw new Error('Status check failed');

        const data = await response.json();

        if (data.completed) {
          this.updateProgressComplete();
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

    // Start spinning wheel for generation step
    const generationStep = this.generationStepTarget;
    generationStep.querySelector('svg').classList.add('animate-spin');
    generationStep.querySelector('svg').classList.remove('text-gray-300');
    generationStep.querySelector('svg').classList.add('text-blue-500');
    generationStep.querySelector('span').classList.remove('text-gray-400');
    generationStep.querySelector('span').classList.add('text-gray-600');
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
  }
}
