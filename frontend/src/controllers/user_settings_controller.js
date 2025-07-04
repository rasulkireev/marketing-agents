import { Controller } from "@hotwired/stimulus";

export default class extends Controller {
  static values = {
    projectId: Number,
  };

  connect() {
    this.fetchAndStoreSettings();
  }

  async fetchAndStoreSettings() {
    if (!this.hasProjectIdValue) {
      return; // Do nothing if no project ID is provided
    }

    try {
      const response = await fetch(
        `/api/user/settings?project_id=${this.projectIdValue}`, {
          credentials: 'same-origin'
        }
      );
      if (!response.ok) {
        // This is a background task, so just log errors, don't alert the user.
        console.error("Failed to fetch user settings in the background.");
        return;
      }
      const data = await response.json();

      localStorage.setItem("userProfileSettings", JSON.stringify(data.profile));
      localStorage.setItem(`projectSettings:${this.projectIdValue}`, JSON.stringify(data.project));

      // Dispatch an event to notify other controllers that settings are loaded
      const event = new CustomEvent("settings:loaded", {
        bubbles: true,
        detail: { projectId: this.projectIdValue },
      });
      this.element.dispatchEvent(event);

    } catch (error) {
      console.error("Error fetching user settings:", error);
    }
  }
}
