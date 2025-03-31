import { Controller } from "@hotwired/stimulus";
import { showMessage } from "../utils/messages";

export default class extends Controller {
  static targets = ["toggleButton", "overlay", "formContainer", "feedbackInput"];

  connect() {
    // Initialize the controller
    this.isOpen = false;

    // Bind keyboard event handlers
    this.handleKeydownBound = this.handleKeydown.bind(this);
    document.addEventListener("keydown", this.handleKeydownBound);
  }

  disconnect() {
    // Clean up event listeners when controller disconnects
    document.removeEventListener("keydown", this.handleKeydownBound);
  }

  toggleFeedback() {
    if (this.isOpen) {
      this.closeFeedback();
    } else {
      this.openFeedback();
    }
  }

  openFeedback() {
    // Display the overlay
    this.overlayTarget.classList.remove("opacity-0", "pointer-events-none");
    this.overlayTarget.classList.add("opacity-100", "pointer-events-auto");

    // Scale up the form with animation
    setTimeout(() => {
      this.formContainerTarget.classList.remove("scale-95");
      this.formContainerTarget.classList.add("scale-100");
    }, 10);

    // Focus the input field
    setTimeout(() => {
      this.feedbackInputTarget.focus();
    }, 300);

    this.isOpen = true;
  }

  closeFeedback() {
    // Scale down the form with animation
    this.formContainerTarget.classList.remove("scale-100");
    this.formContainerTarget.classList.add("scale-95");

    // Hide the overlay with animation
    setTimeout(() => {
      this.overlayTarget.classList.remove("opacity-100", "pointer-events-auto");
      this.overlayTarget.classList.add("opacity-0", "pointer-events-none");
    }, 100);

    this.isOpen = false;
  }

  closeIfClickedOutside(event) {
    // Close if clicked outside the form
    if (event.target === this.overlayTarget) {
      this.closeFeedback();
    }
  }

  handleKeydown(event) {
    // Close with Escape key
    if (event.key === "Escape" && this.isOpen) {
      event.preventDefault();
      this.closeFeedback();
    }

    // Submit with Enter key when focused on the textarea (unless Shift is pressed for multiline)
    if (event.key === "Enter" && !event.shiftKey && this.isOpen &&
        document.activeElement === this.feedbackInputTarget) {
      event.preventDefault();
      this.submitFeedback(event);
    }
  }

  submitFeedback(event) {
    event.preventDefault();

    const feedback = this.feedbackInputTarget.value.trim();

    if (!feedback) {
      return;
    }

    // Add loading state
    const submitButton = event.target.tagName === 'BUTTON' ? event.target : this.element.querySelector('button[type="submit"]');
    const originalButtonText = submitButton?.textContent || 'Submit';
    if (submitButton) {
      submitButton.disabled = true;
      submitButton.textContent = 'Submitting...';
    }

    fetch('/api/submit-feedback', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
      },
      body: JSON.stringify({ feedback, page: window.location.pathname }),
    })
    .then(response => {
      if (!response.ok) {
        throw new Error(`Server responded with ${response.status}: ${response.statusText}`);
      }
      return response.json();
    })
    .then(data => {
      this.resetForm();
      this.closeFeedback();
      showMessage(data.message || "Feedback submitted successfully", 'success');
    })
    .catch((error) => {
      console.error('Error:', error);
      showMessage(error.message || "Failed to submit feedback. Please try again later.", 'error');
      // Reset loading state on error
      if (submitButton) {
        submitButton.disabled = false;
        submitButton.textContent = originalButtonText;
      }
    });
  }

  resetForm() {
    this.feedbackInputTarget.value = "";
  }
}
