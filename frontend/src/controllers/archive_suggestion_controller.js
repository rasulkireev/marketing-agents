import { Controller } from "@hotwired/stimulus";
import { showMessage } from "../utils/messages";

export default class extends Controller {
  static values = {
    suggestionId: Number,
  };
  static targets = ["archiveButton", "unarchiveButton"];

  archive(event) {
    event.preventDefault();
    this.updateArchiveStatus(true);
  }

  unarchive(event) {
    event.preventDefault();
    this.updateArchiveStatus(false);
  }

  updateArchiveStatus(archived) {
    const action = archived ? "archive" : "unarchive";
    const url = `/api/suggestions/${this.suggestionIdValue}/archive-status`;
    const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]").value;

    fetch(url, {
      method: "POST",
      headers: {
        "X-CSRFToken": csrfToken,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ archived: archived }),
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.status === "success") {
          const message = archived
            ? "Suggestion archived successfully."
            : "Suggestion unarchived successfully.";
          showMessage(message, "success");

          this.archiveButtonTarget.classList.toggle("hidden", archived);
          this.unarchiveButtonTarget.classList.toggle("hidden", !archived);

          const destination = archived ? "archived" : "active";
          const moveEvent = new CustomEvent("suggestion:move", {
            bubbles: true,
            detail: { element: this.element, destination: destination },
          });
          this.element.dispatchEvent(moveEvent);
        } else {
          throw new Error(data.message || `Failed to ${action} suggestion.`);
        }
      })
      .catch((error) => {
        console.error("Error:", error);
        showMessage(
          error.message || `Failed to ${action} suggestion.`,
          "error"
        );
      });
  }
}
