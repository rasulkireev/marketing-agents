import { Controller } from "@hotwired/stimulus";
import * as d3 from "d3";

// Controller to handle rendering of D3 trend graphs for keywords
export default class extends Controller {
  static targets = [ "graph", "formMessage", "search", "list" ];

  connect() {
    this.renderAllGraphs();
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
      graphElement.innerHTML = "<p class=\"text-xs text-gray-400 text-center p-1\">Trend data script not found.</p>";
      return;
    }

    let trendDataObjects;
    try {
      trendDataObjects = JSON.parse(trendScriptElement.textContent);
    } catch (e) {
      graphElement.innerHTML = "<p class=\"text-xs text-gray-400 text-center p-1\">Error parsing trend data.</p>";
      console.error("Error parsing trend data JSON:", e);
      return;
    }

    if (!trendDataObjects || trendDataObjects.length === 0) {
      graphElement.innerHTML = "<p class=\"text-xs text-gray-400 text-center p-1\">No trend data available.</p>";
      return;
    }

    graphElement.innerHTML = ""; // Clear previous content

    const { width, height } = graphElement.getBoundingClientRect();
    const padding = { top: 10, right: 10, bottom: 50, left: 30 }; // Increased bottom for rotated x labels

    const svg = d3.select(graphElement)
      .append("svg")
      .attr("width", width)
      .attr("height", height);

    const plotWidth = width - padding.left - padding.right;

    // X Scale (Band for bars)
    const xScale = d3.scaleBand()
      .domain(trendDataObjects.map(d => `${d.month.substring(0,3)}/${String(d.year).slice(-2)}`))
      .range([padding.left, width - padding.right])
      .paddingInner(0.2)
      .paddingOuter(0.1);

    // Y Scale (Linear for bar height)
    let yMin = d3.min(trendDataObjects, d => d.value);
    let yMax = d3.max(trendDataObjects, d => d.value);

    yMin = yMin > 0 ? 0 : yMin - (yMax - yMin) * 0.05;
    yMax = yMax < 0 ? 0 : yMax + (yMax - yMin) * 0.05;
    if (yMin === yMax) {
        yMin = yMin > 0 ? 0 : yMin -1;
        yMax = yMax === 0 ? 1 : yMax +1;
    }
    if (yMax < yMin) yMax = yMin +1;

    const yScale = d3.scaleLinear()
      .domain([yMin, yMax])
      .range([height - padding.bottom, padding.top]);

    const yAxisTickFormat = (d) => {
        if (d === null || d === undefined) return "";
        if (Math.abs(d) >= 1000000) return d3.format(".1s")(d).replace('G', 'B');
        if (Math.abs(d) >= 1000) return d3.format(".1s")(d);
        return d3.format(".0f")(d);
    };

    const yAxis = d3.axisLeft(yScale)
      .ticks(3)
      .tickSizeInner(3)
      .tickSizeOuter(0)
      .tickFormat(yAxisTickFormat);

    svg.append("g")
      .attr("class", "y-axis")
      .attr("transform", `translate(${padding.left}, 0)`)
      .call(yAxis)
      .selectAll("text")
      .style("font-size", "8px") // Slightly larger for y-axis for better readability if space allows
      .style("fill", "#9ca3af");
    svg.selectAll("g.y-axis path.domain").style("stroke", "#d1d5db");
    svg.selectAll("g.y-axis .tick line").style("stroke", "#d1d5db");

    const gridLines = d3.axisLeft(yScale)
      .ticks(3)
      .tickSize(-(plotWidth))
      .tickFormat("");

    svg.append("g")
      .attr("class", "grid")
      .attr("transform", `translate(${padding.left}, 0)`)
      .call(gridLines)
      .selectAll("line")
      .style("stroke", "#e5e7eb")
      .style("stroke-opacity", 1);
    svg.selectAll("g.grid path.domain").remove();

    const xAxis = d3.axisBottom(xScale);
      // .tickFormat((d) => d); // d is already month/year string from xScale.domain()

    svg.append("g")
      .attr("class", "x-axis")
      .attr("transform", `translate(0, ${height - padding.bottom})`)
      .call(xAxis)
      .selectAll("text")
      .style("font-size", "8px")
      .style("fill", "#9ca3af")
      .attr("text-anchor", "start")
      .attr("transform", "rotate(45)")
      .attr("dx", "0.5em")
      .attr("dy", "0.8em");
    svg.selectAll("g.x-axis path.domain").style("stroke", "#d1d5db");
    svg.selectAll("g.x-axis .tick line").style("stroke", "#d1d5db");

    svg.selectAll(".bar")
      .data(trendDataObjects)
      .enter()
      .append("rect")
      .attr("class", "bar")
      .attr("x", d => xScale(`${d.month.substring(0,3)}/${String(d.year).slice(-2)}`))
      .attr("y", d => yScale(Math.max(0, d.value)))
      .attr("width", xScale.bandwidth())
      .attr("height", d => Math.abs(yScale(Math.max(0,d.value)) - yScale(0)))
      .attr("fill", "#ec4899")
      .append("title")
      .text(d => `${d.month} ${d.year}: ${yAxisTickFormat(d.value)}`);
  }

  async addKeyword(event) {
    event.preventDefault();
    const form = event.target;
    const formMessage = this.hasFormMessageTarget ? this.formMessageTarget : null;
    if (formMessage) {
      formMessage.textContent = "Adding keyword...";
      formMessage.className = "ml-4 text-sm text-gray-500";
    }
    const formData = new FormData(form);
    const project_id = formData.get("project_id");
    const keyword_text = formData.get("keyword_text");
    if (!keyword_text || !project_id) {
      if (formMessage) {
        formMessage.textContent = "Keyword and project are required.";
        formMessage.className = "ml-4 text-sm text-red-600";
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
        if (formMessage) {
          formMessage.textContent = "Keyword added! Reloading...";
          formMessage.className = "ml-4 text-sm text-green-600";
        }
        setTimeout(() => { window.location.reload(); }, 800);
      } else {
        if (formMessage) {
          formMessage.textContent = data.message || "Failed to add keyword.";
          formMessage.className = "ml-4 text-sm text-red-600";
        }
      }
    } catch (e) {
      if (formMessage) {
        formMessage.textContent = "An error occurred. Please try again.";
        formMessage.className = "ml-4 text-sm text-red-600";
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
    button.textContent = "Toggling...";
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
          button.textContent = "Unmark as Used";
          button.className = "px-3 py-1.5 text-xs font-semibold text-white bg-pink-600 rounded-md shadow-sm transition focus:outline-none focus:ring-2 focus:ring-pink-500 focus:ring-offset-2 hover:bg-pink-700";
          button.setAttribute("data-keyword-use", "true");
        } else {
          button.textContent = "Mark as Used";
          button.className = "px-3 py-1.5 text-xs font-semibold text-pink-700 bg-white rounded-md border border-pink-300 shadow-sm transition focus:outline-none focus:ring-2 focus:ring-pink-500 focus:ring-offset-2 hover:bg-pink-50";
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
    const items = this.listTarget.querySelectorAll("li");
    items.forEach(item => {
      const keywordTextElem = item.querySelector(".text-lg.font-bold");
      if (!keywordTextElem) {
        item.style.display = "";
        return;
      }
      const keywordText = keywordTextElem.textContent.trim().toLowerCase();
      if (keywordText.includes(searchValue)) {
        item.style.display = "";
      } else {
        item.style.display = "none";
      }
    });
  }

  disconnect() {
    // console.log("KeywordTrendsController disconnected");
  }
}
