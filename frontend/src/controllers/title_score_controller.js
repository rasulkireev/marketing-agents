import { Controller } from "@hotwired/stimulus";
import { showMessage } from "../utils/messages";

export default class extends Controller {
  static targets = ["likeButton", "dislikeButton"];
  static values = {
    suggestionId: Number
  };

  connect() {
    // Initialize button states based on current score
    this.updateButtonStates();
  }

  async updateScore(event) {
    const button = event.currentTarget;
    const isLike = button.classList.contains("like");
    const newScore = isLike ? 1 : -1;

    try {
      const response = await fetch(`/api/update-title-score/${this.suggestionIdValue}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]").value
        },
        body: JSON.stringify({
          score: newScore
        })
      });

      const data = await response.json();

      if (data.status === "error") {
        throw new Error(data.message);
      }

      // Update button states
      this.likeButtonTarget.classList.toggle("bg-green-100", isLike);
      this.likeButtonTarget.classList.toggle("text-green-700", isLike);
      this.dislikeButtonTarget.classList.toggle("bg-red-100", !isLike);
      this.dislikeButtonTarget.classList.toggle("text-red-700", !isLike);

    } catch (error) {
      showMessage(error.message || "Failed to update score", "error");
    }
  }

  updateButtonStates() {
    // Reset both buttons to default state
    this.likeButtonTarget.classList.remove("bg-green-100", "text-green-700");
    this.dislikeButtonTarget.classList.remove("bg-red-100", "text-red-700");

    // Add active state based on current score
    if (this.element.dataset.currentScore === "1") {
      this.likeButtonTarget.classList.add("bg-green-100", "text-green-700");
    } else if (this.element.dataset.currentScore === "-1") {
      this.dislikeButtonTarget.classList.add("bg-red-100", "text-red-700");
    }
  }
}
