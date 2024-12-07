import { Controller } from "@hotwired/stimulus";
import { showMessage } from "../utils/messages";

export default class extends Controller {
  static values = {
    projectId: Number
  };

  static targets = ["input"];

  async save(event) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData(form);

    try {
      const response = await fetch(`/api/projects/${this.projectIdValue}/update`, {
        method: "POST",
        headers: {
          "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]").value,
        },
        body: formData,
      });

      if (!response.ok) {
        throw new Error("Failed to update project details");
      }

      // Show success message
      const successMessage = document.createElement("div");
      successMessage.className = "mt-2 text-sm text-green-600";
      successMessage.textContent = "Project details updated successfully";
      form.appendChild(successMessage);

      // Remove success message after 3 seconds
      setTimeout(() => {
        successMessage.remove();
      }, 3000);

    } catch (error) {
      showMessage(error.message || "Failed to update project details", 'error');
    }
  }
}
