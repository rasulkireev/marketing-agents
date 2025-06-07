import { Controller } from "@hotwired/stimulus";
import { showMessage } from "../utils/messages";

export default class extends Controller {
  static values = {
    generatedPostId: Number,
    projectId: Number,
  };

  connect() {
    this.boundApplySettings = this.applySettings.bind(this);
    this.applySettings(); // Check storage immediately
    window.addEventListener("settings:loaded", this.boundApplySettings);
  }

  disconnect() {
    window.removeEventListener("settings:loaded", this.boundApplySettings);
  }

  applySettings(event) {
    // If an event is passed, check if it's for the correct project
    if (event && event.detail.projectId !== this.projectIdValue) {
      return;
    }

    const settingsJSON = localStorage.getItem(`userSettings:${this.projectIdValue}`);
    if (settingsJSON) {
      const settings = JSON.parse(settingsJSON);
      if (settings.project && settings.project.has_auto_submission_setting) {
        this.element.disabled = true;
        this.element.innerText = "Auto-posting enabled";
        this.element.className = "inline-flex gap-x-2 items-center px-4 py-2 text-sm font-medium text-gray-400 bg-gray-200 rounded-md border-2 border-gray-200 transition-colors duration-200 cursor-not-allowed";
      }
    }
  }

  async post(event) {
    event.preventDefault();
    const button = event.currentTarget;
    button.disabled = true;
    button.innerText = "Posting...";

    if (!this.hasGeneratedPostIdValue || this.generatedPostIdValue === null) {
      showMessage("Could not determine generated post ID.", "error");
      button.innerText = "Post";
      button.disabled = false;
      return;
    }

    try {
      const response = await fetch("/api/post-generated-blog-post", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        },
        body: JSON.stringify({ id: this.generatedPostIdValue })
      });

      const data = await response.json();
      if (response.ok && data.status === "success") {
        showMessage("Blog post published!", "success");
        button.innerText = "Posted";
        // Consider making these classes a static value or target if they need to be consistent
        button.className = "inline-flex gap-x-2 items-center px-4 py-2 text-sm font-medium text-gray-400 bg-gray-200 rounded-md border-2 border border-gray-200 transition-colors duration-200 cursor-not-allowed";
        button.disabled = true; // Redundant due to class change but good for clarity
        const suggestionElement = this.element.closest('[data-controller~="archive-suggestion"]');
        if (suggestionElement) {
          const moveEvent = new CustomEvent("suggestion:move", {
            bubbles: true,
            detail: { element: suggestionElement, destination: "posted" },
          });
          suggestionElement.dispatchEvent(moveEvent);
        }
      } else {
        showMessage(data.message || "Failed to post blog.", "error");
        button.innerText = "Post";
        button.disabled = false;
      }
    } catch (error) {
      showMessage(error.message || "Failed to post blog.", "error");
      button.innerText = "Post";
      button.disabled = false;
    }
  }
}
