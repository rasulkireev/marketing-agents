import { Controller } from "@hotwired/stimulus";
import { showMessage } from "../utils/messages";
export default class extends Controller {
  static values = {
    url: String,
    suggestionId: Number,
    projectId: Number,
    hasProSubscription: Boolean,
    hasAutoSubmissionSetting: Boolean,
    pricingUrl: String,
    projectSettingsUrl: String
  };

  static targets = [
    "status",
    "content",
    "buttonContainer",
    "dropdown",
    "chevron",
    "postButtonContainer"
  ];

  connect() {
    this.expandedValue = false;
  }

  toggle() {
    this.expandedValue = !this.expandedValue;

    if (this.hasDropdownTarget) {
      this.dropdownTarget.classList.toggle("hidden");
    }

    if (this.hasChevronTarget) {
      this.chevronTarget.classList.toggle("rotate-180");
    }
  }

  async generate(event) {
    event.preventDefault();

    try {
      // Remove the button
      this.buttonContainerTarget.innerHTML = "";

      // Update status to spinning wheel
      this.statusTarget.innerHTML = `
        <div class="w-5 h-5 rounded-full border-2 border-gray-300 animate-spin border-t-pink-600"></div>
      `;

      const response = await fetch(`/api/generate-blog-content/${this.suggestionIdValue}`, {
        method: "POST",
        headers: {
          "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]").value
        }
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || "Generation failed");
      }

      const data = await response.json();

      // Check if the response indicates an error
      if (data.status === "error") {
        throw new Error(data.message || "Generation failed");
      }

      // Update status icon to checkmark with dropdown button
      this.statusTarget.innerHTML = `
        <div class="flex gap-x-2 items-center">
          <div class="text-green-500">
            <svg class="w-5 h-5" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
            </svg>
          </div>
          <button data-action="generate-content#toggle" class="flex items-center text-gray-500 hover:text-gray-700">
            <svg data-generate-content-target="chevron" class="w-5 h-5 transition-transform duration-200" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
            </svg>
          </button>
        </div>
      `;

      // Create form elements and set content
      const contentContainer = document.createElement("div");
      contentContainer.className = "space-y-4";

      // Add slug input
      const slugDiv = this.createFormGroup("slug", data.slug, "Slug");
      contentContainer.appendChild(slugDiv);

      // Add tags input
      const tagsDiv = this.createFormGroup("tags", data.tags, "Tags");
      contentContainer.appendChild(tagsDiv);

      // Add description textarea
      const descriptionDiv = this.createFormGroup("description", data.description, "Description", true);
      contentContainer.appendChild(descriptionDiv);

      // Add content textarea
      const contentDiv = this.createFormGroup("content", data.content, "Content", true, "h-96 font-mono");
      contentContainer.appendChild(contentDiv);

      this._appendPostButton(this.postButtonContainerTarget, data.id);

      this.contentTarget.innerHTML = "";
      this.contentTarget.appendChild(contentContainer);

    } catch (error) {
      showMessage(error.message || "Failed to generate content. Please try again later.", 'error');
      // reset the button
      this.buttonContainerTarget.innerHTML = `
        <button
          data-action="generate-content#generate"
          class="px-3 py-1 text-sm font-semibold text-white bg-pink-600 rounded-md hover:bg-pink-700">
          Generate
        </button>
      `;
      this.statusTarget.innerHTML = "";
    }
  }

  _appendPostButton(container, generatedPostId) {
    container.innerHTML = '';

    const profileSettingsJSON = localStorage.getItem("userProfileSettings");
    const projectSettingsJSON = localStorage.getItem(`projectSettings:${this.projectIdValue}`);

    const profileSettings = profileSettingsJSON ? JSON.parse(profileSettingsJSON) : {};
    const projectSettings = projectSettingsJSON ? JSON.parse(projectSettingsJSON) : {};

    const hasPro = profileSettings.has_pro_subscription || false;
    const hasAutoSubmit = projectSettings.has_auto_submission_setting || false;

    let buttonHtml;

    if (hasPro && hasAutoSubmit) {
      // Pro user with settings: Enabled Post button
      buttonHtml = `
        <button
          data-action="post-button#post"
          class="inline-flex gap-x-2 items-center px-4 py-2 text-sm font-medium text-white bg-pink-600 rounded-md border-2 border-pink-600 hover:bg-pink-700 transition-colors duration-200"
        >
          Post
        </button>
      `;
    } else if (hasPro && !hasAutoSubmit) {
      // Pro user without settings: Disabled link to settings
      buttonHtml = `
        <a
          href="${this.projectSettingsUrlValue}#blogging-agent-settings"
          class="inline-flex gap-x-2 items-center px-4 py-2 text-sm font-medium text-gray-400 bg-gray-200 rounded-md border-2 border-gray-200 transition-colors duration-200 cursor-not-allowed"
          data-controller="tooltip"
          data-tooltip-message-value="You need to set up the API endpoint for automatic posting in your project settings."
          data-action="mouseenter->tooltip#show mouseleave->tooltip#hide"
        >
          Post
        </a>
      `;
    } else {
      // Not a pro user: Disabled link to pricing
      buttonHtml = `
        <a
          href="${this.pricingUrlValue}"
          class="inline-flex gap-x-2 items-center px-4 py-2 text-sm font-medium text-gray-400 bg-gray-200 rounded-md border-2 border-gray-200 transition-colors duration-200 cursor-not-allowed"
          data-controller="tooltip"
          data-tooltip-message-value="This feature is available for Pro subscribers only."
          data-action="mouseenter->tooltip#show mouseleave->tooltip#hide"
        >
          Post
        </a>
      `;
    }

    const wrapperDiv = document.createElement('div');
    wrapperDiv.setAttribute('data-controller', 'post-button');
    wrapperDiv.setAttribute('data-post-button-generated-post-id-value', generatedPostId);
    wrapperDiv.setAttribute('data-post-button-project-id-value', this.projectIdValue);
    wrapperDiv.innerHTML = buttonHtml.trim();

    container.appendChild(wrapperDiv);
  }

  createFormGroup(id, value, label, isTextarea = false, extraClasses = "") {
    const div = document.createElement("div");
    div.setAttribute("data-controller", "copy");
    div.className = "relative" + (isTextarea ? " mb-4" : "");

    // Create label
    const labelEl = document.createElement("label");
    labelEl.className = "block text-sm font-medium text-gray-700";
    labelEl.textContent = label;

    // Create input/textarea
    const input = document.createElement(isTextarea ? "textarea" : "input");
    input.value = value;
    input.id = id;
    input.setAttribute("data-copy-target", "source");
    input.className = `block mt-1 ${isTextarea ? "mb-2" : ""} w-full font-mono text-sm rounded-md border sm:text-sm pr-20 ${extraClasses}`;
    input.readOnly = true;

    // Create copy button
    const copyButton = document.createElement("button");
    copyButton.setAttribute("data-action", "copy#copy");
    copyButton.setAttribute("data-copy-target", "button");
    copyButton.className = "absolute right-2" + (isTextarea ? " bottom-2" : " top-[30px]") + " px-3 py-1 text-sm font-semibold text-white bg-pink-600 rounded-md hover:bg-pink-700";
    copyButton.textContent = "Copy";

    // Add elements to the div
    div.appendChild(labelEl);
    div.appendChild(input);
    div.appendChild(copyButton);

    return div;
  }
}
