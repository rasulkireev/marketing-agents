import { Controller } from "@hotwired/stimulus";

export default class extends Controller {
  static values = {
    url: String,
    suggestionId: Number,
    expanded: Boolean
  };

  static targets = ["status", "content", "buttonContainer", "dropdown", "chevron"];

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

      this.contentTarget.innerHTML = "";
      this.contentTarget.appendChild(contentContainer);

    } catch (error) {
      console.error("Error:", error);
      // Show error state and restore button
      this.statusTarget.innerHTML = `
        <div class="w-5 h-5 rounded-full border-2 border-gray-300"></div>
      `;
      this.buttonContainerTarget.innerHTML = `
        <button
          data-action="generate-content#generate"
          class="px-3 py-1 text-sm font-semibold text-white bg-pink-600 rounded-md hover:bg-pink-700">
          Generate Content
        </button>
      `;
    }
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
    input.className = `block mt-1 ${isTextarea ? "mb-2" : ""} w-full font-mono text-sm rounded-md border focus:border-pink-500 focus:ring-pink-500 sm:text-sm pr-20 ${extraClasses}`;
    input.readOnly = true;

    // Create copy button
    const copyButton = document.createElement("button");
    copyButton.setAttribute("data-action", "copy#copy");
    copyButton.setAttribute("data-copy-target", "button");
    copyButton.className = "absolute right-2" + (isTextarea ? " bottom-2" : " top-[30px]") + " px-3 py-1 text-sm font-semibold text-white bg-pink-600 rounded-md hover:bg-pink-700 focus:bg-pink-700 active:bg-pink-700 focus:outline-none focus:ring-2 focus:ring-pink-500 focus:ring-offset-2";
    copyButton.textContent = "Copy";

    // Add elements to the div
    div.appendChild(labelEl);
    div.appendChild(input);
    div.appendChild(copyButton);

    return div;
  }
}
