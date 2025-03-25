import { Controller } from "@hotwired/stimulus";

export default class extends Controller {
    static targets = ["dialog", "url"];

    analyze() {
        this.dialogTarget.showModal();
    }

    closeDialog() {
        this.dialogTarget.close();
        this.urlTarget.value = "";  // Clear input when closing
    }

    async submitAnalysis(event) {
        event.preventDefault();

        const url = this.urlTarget.value;

        try {
            const response = await fetch("/api/competitors/analyze/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": this.getCsrfToken()
                },
                body: JSON.stringify({ url: url })
            });

            if (!response.ok) {
                throw new Error("Network response was not ok");
            }

            // Refresh the page to show new competitor
            window.location.reload();
        } catch (error) {
            console.error("Error:", error);
            // You might want to show an error message to the user here
        }

        this.closeDialog();
    }

    getCsrfToken() {
        return document.querySelector("[name='csrfmiddlewaretoken']").value;
    }
}
