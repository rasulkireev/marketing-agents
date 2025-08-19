import { Controller } from "@hotwired/stimulus";
import * as d3 from "d3";
import { showMessage } from "../utils/messages";

// Controller to handle rendering of D3 trend graphs for keywords
export default class extends Controller {
  static targets = [ "graph", "formMessage", "search", "list", "addButton", "sort" ];

  connect() {
    this.renderAllGraphs();
    // Default sort on connect
    if (this.hasSortTarget) {
      this.sortTarget.value = "volume_desc";
      this.sortKeywords();
    }
  }

  renderAllGraphs() {
    this.graphTargets.forEach(graphElement => {
      this.renderGraph(graphElement);
    });
  }

  renderGraph(graphElement) {
    const trendDataId = graphElement.dataset.trendDataId;
    const trendScriptElement = document.getElementById(trendDataId);

    if (!trendScriptElement) {
      graphElement.innerHTML = "<div class=\"flex items-center justify-center h-full text-xs text-gray-400\">No data</div>";
      return;
    }

    let trendDataObjects;
    try {
      trendDataObjects = JSON.parse(trendScriptElement.textContent);
    } catch (e) {
      graphElement.innerHTML = "<div class=\"flex items-center justify-center h-full text-xs text-gray-400\">Error</div>";
      console.error("Error parsing trend data JSON:", e);
      return;
    }

    if (!trendDataObjects || trendDataObjects.length === 0) {
      graphElement.innerHTML = "<div class=\"flex items-center justify-center h-full text-xs text-gray-400\">No data</div>";
      return;
    }

    graphElement.innerHTML = ""; // Clear previous content

    const { width, height } = graphElement.getBoundingClientRect();
    const padding = { top: 2, right: 2, bottom: 2, left: 2 }; // Minimal padding for sparkline

    const svg = d3.select(graphElement)
      .append("svg")
      .attr("width", width)
      .attr("height", height);

    // X Scale (for sparkline positioning)
    const xScale = d3.scaleLinear()
      .domain([0, trendDataObjects.length - 1])
      .range([padding.left, width - padding.right]);

    // Y Scale (Linear for line/area height)
    let yMin = d3.min(trendDataObjects, d => d.value);
    let yMax = d3.max(trendDataObjects, d => d.value);

    // Handle edge cases
    if (yMin === yMax) {
      yMin = yMin > 0 ? yMin * 0.9 : yMin * 1.1;
      yMax = yMax > 0 ? yMax * 1.1 : yMax * 0.9;
    }

    const yScale = d3.scaleLinear()
      .domain([yMin, yMax])
      .range([height - padding.bottom, padding.top]);

    // Create line generator for sparkline
    const line = d3.line()
      .x((d, i) => xScale(i))
      .y(d => yScale(d.value))
      .curve(d3.curveMonotoneX);

    // Create area generator for sparkline
    const area = d3.area()
      .x((d, i) => xScale(i))
      .y0(height - padding.bottom)
      .y1(d => yScale(d.value))
      .curve(d3.curveMonotoneX);

    // Add area fill
    svg.append("path")
      .datum(trendDataObjects)
      .attr("class", "area")
      .attr("d", area)
      .attr("fill", "#374151")
      .attr("fill-opacity", 0.1);

    // Add line
    svg.append("path")
      .datum(trendDataObjects)
      .attr("class", "line")
      .attr("d", line)
      .attr("fill", "none")
      .attr("stroke", "#374151")
      .attr("stroke-width", 1.5);

    // Add tooltip functionality
    const tooltip = d3.select("body").append("div")
      .attr("class", "tooltip")
      .style("opacity", 0)
      .style("position", "absolute")
      .style("background", "rgba(0, 0, 0, 0.8)")
      .style("color", "white")
      .style("padding", "8px")
      .style("border-radius", "4px")
      .style("font-size", "12px")
      .style("pointer-events", "none");

    // Add invisible overlay for tooltip
    svg.append("rect")
      .attr("width", width)
      .attr("height", height)
      .attr("fill", "transparent")
      .on("mousemove", (event) => {
        const [mouseX] = d3.pointer(event);
        const index = Math.round(xScale.invert(mouseX));

        if (index >= 0 && index < trendDataObjects.length) {
          const data = trendDataObjects[index];
          const formatValue = (val) => {
            if (Math.abs(val) >= 1000000) return d3.format(".1s")(val).replace("G", "B");
            if (Math.abs(val) >= 1000) return d3.format(".1s")(val);
            return d3.format(".0f")(val);
          };

          tooltip.transition()
            .duration(200)
            .style("opacity", .9);
          tooltip.html(`${data.month} ${data.year}: ${formatValue(data.value)}`)
            .style("left", (event.pageX + 10) + "px")
            .style("top", (event.pageY - 28) + "px");
        }
      })
      .on("mouseout", () => {
        tooltip.transition()
          .duration(500)
          .style("opacity", 0);
      });
  }

  async addKeyword(event) {
    event.preventDefault();
    const form = event.target;
    const addButton = this.hasAddButtonTarget ? this.addButtonTarget : null;
    if (addButton) {
      addButton.disabled = true;
      addButton.innerHTML = `<svg class="mr-2 -ml-1 w-5 h-5 text-white animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"></path></svg>Adding...`;
    }
    const formData = new FormData(form);
    const project_id = formData.get("project_id");
    const keyword_text = formData.get("keyword_text");
    if (!keyword_text || !project_id) {
      showMessage("Keyword and project are required.", "error");
      if (addButton) {
        addButton.disabled = false;
        addButton.textContent = "Add Keyword";
      }
      return;
    }
    try {
      const response = await fetch("/api/keywords/add", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": this.getCSRFToken(),
        },
        body: JSON.stringify({ project_id: parseInt(project_id), keyword_text: keyword_text.trim() })
      });
      const data = await response.json();
      if (data.status === "success") {
        showMessage("Keyword added successfully!", "success");
        setTimeout(() => { window.location.reload(); }, 800);
      } else {
        showMessage(data.message || "Failed to add keyword.", "error");
        if (addButton) {
          addButton.disabled = false;
          addButton.textContent = "Add Keyword";
        }
      }
    } catch (e) {
      showMessage("An error occurred. Please try again.", "error");
      if (addButton) {
        addButton.disabled = false;
        addButton.textContent = "Add Keyword";
      }
    }
  }

  getCSRFToken() {
    // Try to get CSRF token from cookie (Django default)
    const name = "csrftoken";
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      let cookie = cookies[i].trim();
      if (cookie.startsWith(name + '=')) {
        return decodeURIComponent(cookie.substring(name.length + 1));
      }
    }
    return '';
  }

  async toggleUse(event) {
    const button = event.currentTarget;
    const projectId = button.getAttribute("data-project-id");
    const keywordId = button.getAttribute("data-keyword-id");
    if (!projectId || !keywordId) {
      button.textContent = "Error: Missing IDs";
      button.className += " bg-red-200 text-red-800";
      return;
    }
    const originalText = button.textContent;
    button.disabled = true;
    button.textContent = "";
    try {
      const response = await fetch("/api/keywords/toggle-use", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": this.getCSRFToken(),
        },
        body: JSON.stringify({ project_id: parseInt(projectId), keyword_id: parseInt(keywordId) })
      });
      const data = await response.json();
      if (data.status === "success") {
        if (data.use === true) {
          button.textContent = "In Use";
          button.className = "inline-flex items-center px-3 py-1.5 text-xs font-medium text-white bg-gray-900 rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 hover:bg-gray-800";
          button.setAttribute("data-keyword-use", "true");
        } else {
          button.textContent = "Use";
          button.className = "inline-flex items-center px-3 py-1.5 text-xs font-medium text-gray-700 bg-white rounded-md border border-gray-300 transition-colors focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 hover:bg-gray-50";
          button.setAttribute("data-keyword-use", "false");
        }
      } else {
        button.textContent = data.message || "Failed to toggle";
        button.className += " bg-red-200 text-red-800";
        setTimeout(() => {
          button.textContent = originalText;
          button.disabled = false;
        }, 1200);
        return;
      }
    } catch (e) {
      button.textContent = "Error";
      button.className += " bg-red-200 text-red-800";
      setTimeout(() => {
        button.textContent = originalText;
        button.disabled = false;
      }, 1200);
      return;
    }
    setTimeout(() => {
      button.disabled = false;
    }, 400);
  }

  filterKeywords() {
    if (!this.hasSearchTarget || !this.hasListTarget) return;
    const searchValue = this.searchTarget.value.trim().toLowerCase();
    const rows = this.listTarget.querySelectorAll("tr");
    rows.forEach(row => {
      const keywordTextElem = row.querySelector(".text-sm.font-medium");
      if (!keywordTextElem) {
        row.style.display = "";
        return;
      }
      const keywordText = keywordTextElem.textContent.trim().toLowerCase();
      if (keywordText.includes(searchValue)) {
        row.style.display = "";
      } else {
        row.style.display = "none";
      }
    });
  }

  sortKeywords() {
    if (!this.hasListTarget || !this.hasSortTarget) return;
    const sortValue = this.sortTarget.value;
    const rows = Array.from(this.listTarget.querySelectorAll("tr"));
    let getSortValue;
    let direction = 1;
    switch (sortValue) {
      case "created_asc":
        getSortValue = row => new Date(row.getAttribute("data-created-at"));
        direction = 1;
        break;
      case "created_desc":
        getSortValue = row => new Date(row.getAttribute("data-created-at"));
        direction = -1;
        break;
      case "volume_desc":
        getSortValue = row => parseInt(row.getAttribute("data-volume")) || 0;
        direction = -1;
        break;
      case "volume_asc":
        getSortValue = row => parseInt(row.getAttribute("data-volume")) || 0;
        direction = 1;
        break;
      case "competition_desc":
        getSortValue = row => parseFloat(row.getAttribute("data-competition")) || 0;
        direction = -1;
        break;
      case "competition_asc":
        getSortValue = row => parseFloat(row.getAttribute("data-competition")) || 0;
        direction = 1;
        break;
      case "cpc_desc":
        getSortValue = row => parseFloat(row.getAttribute("data-cpc-value")) || 0;
        direction = -1;
        break;
      case "cpc_asc":
        getSortValue = row => parseFloat(row.getAttribute("data-cpc-value")) || 0;
        direction = 1;
        break;
      default:
        getSortValue = row => new Date(row.getAttribute("data-created-at"));
        direction = -1;
    }
    rows.sort((a, b) => {
      const aVal = getSortValue(a);
      const bVal = getSortValue(b);
      if (aVal < bVal) return -1 * direction;
      if (aVal > bVal) return 1 * direction;
      return 0;
    });
    // Remove all rows and re-append in sorted order
    rows.forEach(row => this.listTarget.appendChild(row));
  }

  disconnect() {
    // console.log("KeywordTrendsController disconnected");
  }
}
