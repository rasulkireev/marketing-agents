import { Controller } from "@hotwired/stimulus";

export default class extends Controller {
  static targets = [
    "monthlyPriceDisplay",
    "yearlyPriceDisplay",
    "monthlyLabel",
    "yearlyLabel",
    "monthlyCheckout",
    "yearlyCheckout",
    "toggle"
  ];

  connect() {
    this.isMonthly = true;
    this.updateUI();
  }

  switch() {
    this.isMonthly = !this.isMonthly;
    this.updateUI();
  }

  updateUI() {
    if (this.isMonthly) {
      this.monthlyPriceDisplayTarget.classList.remove("hidden");
      this.yearlyPriceDisplayTarget.classList.add("hidden");

      this.monthlyCheckoutTarget.classList.remove("hidden");
      this.yearlyCheckoutTarget.classList.add("hidden");

      this.monthlyLabelTarget.classList.add("bg-pink-600", "text-white");
      this.monthlyLabelTarget.classList.remove("text-gray-500");
      this.yearlyLabelTarget.classList.add("text-gray-500");
      this.yearlyLabelTarget.classList.remove("bg-pink-600", "text-white");

    } else {
      this.yearlyPriceDisplayTarget.classList.remove("hidden");
      this.monthlyPriceDisplayTarget.classList.add("hidden");

      this.yearlyCheckoutTarget.classList.remove("hidden");
      this.monthlyCheckoutTarget.classList.add("hidden");

      this.yearlyLabelTarget.classList.add("bg-pink-600", "text-white");
      this.yearlyLabelTarget.classList.remove("text-gray-500");
      this.monthlyLabelTarget.classList.add("text-gray-500");
      this.monthlyLabelTarget.classList.remove("bg-pink-600", "text-white");
    }
  }
}
