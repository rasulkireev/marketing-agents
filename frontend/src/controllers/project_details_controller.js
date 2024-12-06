import { Controller } from "@hotwired/stimulus";

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
      console.error("Error updating project details:", error);

      // Show error message
      const errorMessage = document.createElement("div");
      errorMessage.className = "mt-2 text-sm text-red-600";
      errorMessage.textContent = "Failed to update project details";
      form.appendChild(errorMessage);

      // Remove error message after 3 seconds
      setTimeout(() => {
        errorMessage.remove();
      }, 3000);
    }
  }
}
