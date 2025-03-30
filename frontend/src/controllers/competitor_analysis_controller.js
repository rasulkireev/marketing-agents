import { Controller } from "@hotwired/stimulus";

export default class extends Controller {
    static targets = ["dialog", "url", "form", "submitButton", "spinner", "errorMessage"];

    connect() {
        this.isProcessing = false;
    }

    analyze() {
        this.dialogTarget.showModal();
        if (this.hasErrorMessageTarget) {
            this.errorMessageTarget.textContent = "";
            this.errorMessageTarget.classList.add("hidden");
        }
    }

    closeDialog() {
        this.dialogTarget.close();
        this.urlTarget.value = "";
        this.resetFormState();
    }

    resetFormState() {
        if (this.hasSubmitButtonTarget && this.hasSpinnerTarget) {
            this.submitButtonTarget.disabled = false;
            this.spinnerTarget.classList.add("hidden");
            this.submitButtonTarget.querySelector("span").classList.remove("hidden");
        }
        this.isProcessing = false;
    }

    async submitAnalysis(event) {
        event.preventDefault();

        if (this.isProcessing) {
            return;
        }

        const url = this.urlTarget.value;
        if (!url) {
            this.handleError("URL is required");
            return;
        }

        const projectId = this.getProjectId();
        if (!projectId) {
            this.handleError("Project ID could not be determined");
            return;
        }

        this.isProcessing = true;
        this.setLoadingState();

        try {
            const csrfToken = this.getCsrfToken();
            if (!csrfToken) {
                throw new Error("CSRF token not found");
            }

            console.log("Submitting request:", {
                project_id: projectId,
                url: url
            });

            const response = await fetch("/api/add-competitor", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfToken
                },
                body: JSON.stringify({
                    project_id: projectId,
                    url: url
                })
            });

            if (!response.ok) {
                // Try to get more detailed error information
                let errorMsg;
                try {
                    const errorData = await response.json();
                    errorMsg = errorData.message || errorData.detail || `Server error: ${response.status}`;
                } catch (e) {
                    errorMsg = `Server error: ${response.status}`;
                }
                throw new Error(errorMsg);
            }

            const result = await response.json();

            if (result.status === "error") {
                throw new Error(result.message || "Failed to analyze competitor");
            }

            // Handle successful response
            this.handleSuccess(result);
        } catch (error) {
            this.handleError(error.message);
        } finally {
            this.resetFormState();
        }
    }

    setLoadingState() {
        if (this.hasSubmitButtonTarget && this.hasSpinnerTarget) {
            this.submitButtonTarget.disabled = true;
            this.spinnerTarget.classList.remove("hidden");
            this.submitButtonTarget.querySelector("span").classList.add("hidden");
        }
    }

    handleSuccess(competitor) {
        // Add the new competitor to the page without refreshing
        this.addCompetitorToUI(competitor);
        this.closeDialog();
    }

    handleError(message) {
        console.error("Error:", message);
        if (this.hasErrorMessageTarget) {
            this.errorMessageTarget.textContent = message;
            this.errorMessageTarget.classList.remove("hidden");
        }
    }

    addCompetitorToUI(competitor) {
        const competitorsContainer = document.querySelector(".competitors-container");

        if (!competitorsContainer) {
            // Refresh the page if we can't find the container
            window.location.reload();
            return;
        }

        // Create new competitor element
        const competitorElement = this.createCompetitorElement(competitor);

        // Add it to the end of the container instead of prepending
        competitorsContainer.appendChild(competitorElement);

        // If "no competitors" message exists, remove it
        const emptyMessage = document.querySelector(".empty-competitors-message");
        if (emptyMessage) {
            emptyMessage.remove();
        }
    }

    createCompetitorElement(competitor) {
        const template = document.createElement("template");

        // Only show the full details if we have analysis data
        const hasAnalysis = competitor.summary || competitor.competitor_analysis ||
                           competitor.strengths || competitor.weaknesses ||
                           competitor.opportunities || competitor.threats ||
                           competitor.key_features || competitor.key_benefits;

        if (hasAnalysis) {
            template.innerHTML = `
                <details class="mb-4 bg-white rounded-lg border border-pink-100 shadow-sm group" open>
                    <summary class="flex justify-between items-center p-6 list-none cursor-pointer">
                        <div class="flex gap-x-3 items-center">
                            <div class="flex justify-center items-center w-8 h-8 bg-pink-50 rounded-lg">
                                <svg class="w-5 h-5 text-pink-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                                </svg>
                            </div>
                            <div>
                                <h4 class="text-lg font-medium text-gray-900">${competitor.name}</h4>
                                <p class="text-sm text-gray-500">${competitor.url}</p>
                            </div>
                        </div>
                        <svg class="w-5 h-5 text-gray-500 transition-transform group-open:rotate-180" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                        </svg>
                    </summary>
                    <div class="px-6 pb-6 space-y-6">
                        ${competitor.summary ? `
                        <div class="max-w-full prose">
                            <h5 class="text-sm font-medium text-gray-900">Summary</h5>
                            <div class="p-4 mt-2 bg-gray-50 rounded-lg">
                                <p class="text-sm text-gray-600">${competitor.summary.replace(/\n/g, '<br>')}</p>
                            </div>
                        </div>
                        ` : ''}

                        ${competitor.competitor_analysis ? `
                        <div class="max-w-full prose">
                            <h5 class="text-sm font-medium text-gray-900">Analysis</h5>
                            <div class="p-4 mt-2 bg-gray-50 rounded-lg">
                                <p class="text-sm text-gray-600">${competitor.competitor_analysis.replace(/\n/g, '<br>')}</p>
                            </div>
                        </div>
                        ` : ''}

                        <div class="grid grid-cols-2 gap-4">
                            ${competitor.strengths ? `
                            <div class="max-w-full prose">
                                <h5 class="text-sm font-medium text-gray-900">Strengths</h5>
                                <div class="p-4 mt-2 bg-green-50 rounded-lg">
                                    <p class="text-sm text-gray-600">${competitor.strengths.replace(/\n/g, '<br>')}</p>
                                </div>
                            </div>
                            ` : ''}

                            ${competitor.weaknesses ? `
                            <div class="max-w-full prose">
                                <h5 class="text-sm font-medium text-gray-900">Weaknesses</h5>
                                <div class="p-4 mt-2 bg-red-50 rounded-lg">
                                    <p class="text-sm text-gray-600">${competitor.weaknesses.replace(/\n/g, '<br>')}</p>
                                </div>
                            </div>
                            ` : ''}

                            ${competitor.opportunities ? `
                            <div class="max-w-full prose">
                                <h5 class="text-sm font-medium text-gray-900">Opportunities</h5>
                                <div class="p-4 mt-2 bg-blue-50 rounded-lg">
                                    <p class="text-sm text-gray-600">${competitor.opportunities.replace(/\n/g, '<br>')}</p>
                                </div>
                            </div>
                            ` : ''}

                            ${competitor.threats ? `
                            <div class="max-w-full prose">
                                <h5 class="text-sm font-medium text-gray-900">Threats</h5>
                                <div class="p-4 mt-2 bg-yellow-50 rounded-lg">
                                    <p class="text-sm text-gray-600">${competitor.threats.replace(/\n/g, '<br>')}</p>
                                </div>
                            </div>
                            ` : ''}
                        </div>

                        <div class="grid grid-cols-2 gap-4">
                            ${competitor.key_features ? `
                            <div class="max-w-full prose">
                                <h5 class="text-sm font-medium text-gray-900">Key Features</h5>
                                <div class="p-4 mt-2 bg-gray-50 rounded-lg">
                                    <p class="text-sm text-gray-600">${competitor.key_features.replace(/\n/g, '<br>')}</p>
                                </div>
                            </div>
                            ` : ''}

                            ${competitor.key_benefits ? `
                            <div class="max-w-full prose">
                                <h5 class="text-sm font-medium text-gray-900">Key Benefits</h5>
                                <div class="p-4 mt-2 bg-gray-50 rounded-lg">
                                    <p class="text-sm text-gray-600">${competitor.key_benefits.replace(/\n/g, '<br>')}</p>
                                </div>
                            </div>
                            ` : ''}
                        </div>
                    </div>
                </details>
            `;
        } else {
            template.innerHTML = `
                <div class="p-6 mb-4 bg-white rounded-lg border border-pink-100 shadow-sm">
                    <div class="flex gap-x-3 items-center">
                        <div class="flex justify-center items-center w-8 h-8 bg-pink-50 rounded-lg">
                            <svg class="w-5 h-5 text-pink-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                            </svg>
                        </div>
                        <div>
                            <h4 class="text-lg font-medium text-gray-900">${competitor.name}</h4>
                            <p class="text-sm text-gray-500">${competitor.url}</p>
                        </div>
                    </div>
                    <p class="mt-4 text-sm text-gray-500">Analysis pending. Check back later for insights.</p>
                </div>
            `;
        }

        return template.content.firstElementChild;
    }

    getProjectId() {
        // First try to extract from URL
        const projectIdMatch = window.location.pathname.match(/\/projects\/(\d+)/);
        if (projectIdMatch && projectIdMatch[1]) {
            return projectIdMatch[1];
        }

        // If not found in URL, try to find a hidden input or data attribute
        const projectIdInput = document.getElementById("project_id");
        if (projectIdInput) {
            return projectIdInput.value;
        }

        // Try data attribute on body or other main element
        const projectIdData = document.body.getAttribute("data-project-id");
        if (projectIdData) {
            return projectIdData;
        }

        // If all else fails, check if we have it in window object
        if (window.PROJECT_ID) {
            return window.PROJECT_ID;
        }

        return null;
    }

    getCsrfToken() {
        // First try the standard way
        const csrfInput = document.querySelector("[name='csrfmiddlewaretoken']");
        if (csrfInput) {
            return csrfInput.value;
        }

        // Try to get it from cookies
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.startsWith('csrftoken=')) {
                return cookie.substring('csrftoken='.length, cookie.length);
            }
        }

        // If we still can't find it, try to get it from the meta tag
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        if (metaTag) {
            return metaTag.getAttribute('content');
        }

        return null;
    }
}
