const API_BASE_URL = "http://localhost:8000";

const state = {
  token: localStorage.getItem("e9_token"),
  username: localStorage.getItem("e9_username"),
  rubrics: [],
  selectedRubricId: null,
  criterionRowIndex: 0,
  batchRowIndex: 0,
  historyLoaded: false
};

if (!state.token) {
  window.location.href = "login.html";
}

const el = (id) => document.getElementById(id);

function toast(message, type) {
  const node = el("toast");
  node.textContent = message;
  node.className = "toast" + (type ? " " + type : "");
  node.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { node.hidden = true; }, 3500);
}

async function apiFetch(path, options = {}) {
  const headers = Object.assign({ "Content-Type": "application/json" }, options.headers || {});
  headers["Authorization"] = "Bearer " + state.token;

  const response = await fetch(API_BASE_URL + path, Object.assign({}, options, { headers }));

  if (response.status === 401) {
    logout();
    throw new Error("your session expired, log in again");
  }

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const detail = typeof data.detail === "string" ? data.detail : "something went wrong, try again";
    throw new Error(detail);
  }

  return data;
}

function logout() {
  localStorage.removeItem("e9_token");
  localStorage.removeItem("e9_username");
  window.location.href = "login.html";
}

el("logoutBtn").addEventListener("click", logout);
el("usernameLabel").textContent = state.username || "";
el("userAvatar").textContent = (state.username || "?").slice(0, 2).toUpperCase();

document.querySelectorAll(".top-nav button").forEach((btn) => {
  btn.addEventListener("click", () => switchView(btn.dataset.view));
});

function switchView(viewName) {
  document.querySelectorAll(".top-nav button").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.view === viewName);
  });
  document.querySelectorAll(".view").forEach((view) => {
    view.classList.toggle("active", view.id === viewName + "View");
  });
  if (viewName === "history" && !state.historyLoaded) {
    loadHistory();
  }
}

async function loadRubrics() {
  try {
    state.rubrics = await apiFetch("/rubrics");
    renderRubricList();
    renderRubricSelect();
  } catch (err) {
    toast(err.message, "error");
  }
}

function renderRubricList() {
  const list = el("rubricList");
  list.innerHTML = "";

  if (state.rubrics.length === 0) {
    const empty = document.createElement("p");
    empty.className = "empty-note";
    empty.textContent = "No rubrics yet. Create one to start scoring reports.";
    list.appendChild(empty);
    return;
  }

  state.rubrics.forEach((rubric) => {
    const item = document.createElement("li");
    item.className = "rubric-item" + (rubric.id === state.selectedRubricId ? " active" : "");

    const info = document.createElement("div");
    info.className = "rubric-item-info";

    const title = document.createElement("span");
    title.className = "rubric-item-title";
    title.textContent = rubric.title;

    const id = document.createElement("span");
    id.className = "rubric-item-id mono";
    id.textContent = rubric.id + " · " + rubric.criteria.length + " criteria";

    info.appendChild(title);
    info.appendChild(id);

    const deleteBtn = document.createElement("button");
    deleteBtn.className = "icon-btn";
    deleteBtn.type = "button";
    deleteBtn.textContent = "Delete";
    deleteBtn.addEventListener("click", (event) => {
      event.stopPropagation();
      deleteRubric(rubric.id);
    });

    item.appendChild(info);
    item.appendChild(deleteBtn);

    item.addEventListener("click", () => {
      state.selectedRubricId = rubric.id;
      renderRubricList();
      renderRubricSelect();
      toast("Using \"" + rubric.title + "\" for scoring", "success");
    });

    list.appendChild(item);
  });
}

function renderRubricSelect() {
  const select = el("rubricSelect");
  select.innerHTML = "";

  if (state.rubrics.length === 0) {
    const option = document.createElement("option");
    option.textContent = "No rubrics yet — create one first";
    select.appendChild(option);
    return;
  }

  state.rubrics.forEach((rubric) => {
    const option = document.createElement("option");
    option.value = rubric.id;
    option.textContent = rubric.title + " (" + rubric.id + ")";
    select.appendChild(option);
  });

  if (!state.selectedRubricId && state.rubrics.length > 0) {
    state.selectedRubricId = state.rubrics[0].id;
  }
  select.value = state.selectedRubricId || "";
}

el("rubricSelect").addEventListener("change", (event) => {
  state.selectedRubricId = event.target.value;
  renderRubricList();
});

async function deleteRubric(rubricId) {
  try {
    await apiFetch("/rubrics/" + rubricId, { method: "DELETE" });
    if (state.selectedRubricId === rubricId) {
      state.selectedRubricId = null;
    }
    await loadRubrics();
    toast("Rubric deleted", "success");
  } catch (err) {
    toast(err.message, "error");
  }
}

el("newRubricBtn").addEventListener("click", () => {
  el("rubricForm").hidden = false;
  el("rubricFormEmpty").hidden = true;
  el("criteriaRows").innerHTML = "";
  el("rubricTitle").value = "";
  state.criterionRowIndex = 0;
  addCriterionRow();
  addCriterionRow();
  recalcWeightSum();
});

el("cancelRubricBtn").addEventListener("click", () => {
  el("rubricForm").hidden = true;
  el("rubricFormEmpty").hidden = false;
});

function addCriterionRow() {
  const rowId = "criterion-" + state.criterionRowIndex++;
  const row = document.createElement("div");
  row.className = "criterion-row";
  row.dataset.rowId = rowId;

  row.innerHTML = `
    <div class="criterion-row-top">
      <input type="text" class="field-input criterion-name" placeholder="Criterion name" required>
      <input type="number" class="field-input weight-input" placeholder="Weight" min="1" max="100" required>
    </div>
    <textarea class="field-input criterion-description" rows="2" placeholder="What this criterion evaluates"></textarea>
    <button type="button" class="remove-row-btn">Remove</button>
  `;

  row.querySelector(".remove-row-btn").addEventListener("click", () => {
    row.remove();
    recalcWeightSum();
  });

  row.querySelector(".weight-input").addEventListener("input", recalcWeightSum);

  el("criteriaRows").appendChild(row);
}

el("addCriterionBtn").addEventListener("click", () => {
  addCriterionRow();
  recalcWeightSum();
});

function recalcWeightSum() {
  const inputs = document.querySelectorAll(".weight-input");
  let total = 0;
  inputs.forEach((input) => { total += Number(input.value) || 0; });

  const readout = el("weightSum");
  readout.textContent = total;
  const wrap = readout.parentElement;
  wrap.classList.toggle("balanced", total === 100);
  wrap.classList.toggle("unbalanced", total !== 100);
}

el("rubricForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  el("rubricError").hidden = true;

  const rows = document.querySelectorAll(".criterion-row");
  const criteria = Array.from(rows).map((row) => ({
    name: row.querySelector(".criterion-name").value.trim(),
    description: row.querySelector(".criterion-description").value.trim(),
    weight: Number(row.querySelector(".weight-input").value)
  }));

  try {
    const rubric = await apiFetch("/rubrics", {
      method: "POST",
      body: JSON.stringify({ title: el("rubricTitle").value.trim(), criteria })
    });
    el("rubricForm").hidden = true;
    el("rubricFormEmpty").hidden = false;
    state.selectedRubricId = rubric.id;
    await loadRubrics();
    toast("Rubric saved", "success");
  } catch (err) {
    el("rubricError").textContent = err.message;
    el("rubricError").hidden = false;
  }
});

el("reportText").addEventListener("input", (event) => {
  el("charCount").textContent = event.target.value.length + " characters";
});

el("batchToggle").addEventListener("change", (event) => {
  const isBatch = event.target.checked;
  el("singleReportBlock").hidden = isBatch;
  el("batchReportBlock").hidden = !isBatch;

  if (isBatch && el("batchReports").children.length === 0) {
    addBatchReportRow();
    addBatchReportRow();
  }
});

function addBatchReportRow() {
  const index = ++state.batchRowIndex;
  const row = document.createElement("div");
  row.className = "batch-report-row";
  row.innerHTML = `
    <span class="batch-report-label">Report ${index}</span>
    <textarea class="field-input" placeholder="Paste report text (minimum 200 characters)"></textarea>
  `;
  el("batchReports").appendChild(row);
}

el("addBatchReportBtn").addEventListener("click", addBatchReportRow);

el("scoreBtn").addEventListener("click", async () => {
  el("scoreError").hidden = true;

  if (!state.selectedRubricId) {
    el("scoreError").textContent = "create or select a rubric before scoring";
    el("scoreError").hidden = false;
    return;
  }

  const isBatch = el("batchToggle").checked;

  el("scoreBtn").disabled = true;
  el("loadingCard").hidden = false;
  el("resultsArea").innerHTML = "";

  try {
    if (isBatch) {
      const reports = Array.from(document.querySelectorAll("#batchReports textarea"))
        .map((t) => t.value.trim())
        .filter((v) => v.length > 0);

      const data = await apiFetch("/score/batch", {
        method: "POST",
        body: JSON.stringify({ rubric_id: state.selectedRubricId, reports })
      });

      data.scorecards.forEach((scorecard, i) => renderResult(scorecard, el("resultsArea"), i + 1));

      if (data.failed.length > 0) {
        toast(data.failed.length + " report(s) failed guardrail checks", "error");
      }
    } else {
      const reportText = el("reportText").value.trim();
      const scorecard = await apiFetch("/score", {
        method: "POST",
        body: JSON.stringify({ rubric_id: state.selectedRubricId, report_text: reportText })
      });
      renderResult(scorecard, el("resultsArea"), null);
    }
    state.historyLoaded = false;
  } catch (err) {
    el("scoreError").textContent = err.message;
    el("scoreError").hidden = false;
  } finally {
    el("scoreBtn").disabled = false;
    el("loadingCard").hidden = true;
  }
});

function bandColor(percentage) {
  if (percentage >= 85) return "#34D399";
  if (percentage >= 70) return "#38BDF8";
  if (percentage >= 50) return "#FBBF24";
  return "#F87171";
}

function buildRing(percentage) {
  const radius = 48;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - Math.min(percentage, 100) / 100);
  const color = bandColor(percentage);

  return `
    <svg viewBox="0 0 110 110" width="118" height="118">
      <circle cx="55" cy="55" r="${radius}" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="9"></circle>
      <circle cx="55" cy="55" r="${radius}" fill="none" stroke="${color}" stroke-width="9"
        stroke-linecap="round" stroke-dasharray="${circumference}" stroke-dashoffset="${offset}"
        transform="rotate(-90 55 55)"></circle>
    </svg>
  `;
}

function renderResult(scorecard, container, batchIndex) {
  const wrap = document.createElement("div");
  wrap.className = "result-block";

  const header = document.createElement("div");
  header.className = "card glass floaty result-header";
  header.innerHTML = `
    <div class="score-ring-wrap">
      ${buildRing(scorecard.weighted_total)}
      <div class="score-ring-value mono">${scorecard.weighted_total}</div>
    </div>
    <div class="result-meta">
      ${batchIndex ? `<span class="batch-report-label">Report ${batchIndex}</span>` : ""}
      <span class="grade-badge grade-${scorecard.grade}">${scorecard.grade}</span>
      <div class="result-ids">
        <span>Report <span class="mono">${scorecard.report_id}</span></span>
        <span>Scorecard <span class="mono">${scorecard.id}</span></span>
      </div>
      <span class="result-status">Status: ${scorecard.status.replace("_", " ")}</span>
    </div>
  `;
  wrap.appendChild(header);

  if (scorecard.disagreements && scorecard.disagreements.length > 0) {
    const banner = document.createElement("div");
    banner.className = "disagreement-banner";
    const pairs = scorecard.disagreements
      .map((d) => `${d.criterion_a} vs ${d.criterion_b} (${d.difference} pts)`)
      .join(", ");
    banner.innerHTML = `<strong>Worth a second look.</strong> ${pairs} — held for review.`;
    wrap.appendChild(banner);
  }

  const table = document.createElement("div");
  table.className = "card glass criteria-table";
  const rows = scorecard.raw_scores.map((s) => `
    <tr>
      <td class="criterion-name">${s.name}</td>
      <td>
        <div class="score-cell">
          <div class="score-bar-track"><div class="score-bar-fill" style="width:${s.score}%; background:${bandColor(s.score)}"></div></div>
          <span class="score-value mono">${s.score}</span>
        </div>
      </td>
      <td class="evidence-quote">"${s.evidence_quote}"</td>
      <td class="confidence-value">${Math.round(s.confidence * 100)}%</td>
    </tr>
  `).join("");

  table.innerHTML = `
    <table>
      <thead><tr><th>Criterion</th><th>Score</th><th>Evidence</th><th>Confidence</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
    <div class="export-row">
      <button class="btn btn-ghost btn-small export-btn">Export JSON</button>
    </div>
  `;
  table.querySelector(".export-btn").addEventListener("click", () => exportScorecard(scorecard.report_id));
  wrap.appendChild(table);

  const accordion = document.createElement("div");
  accordion.className = "card glass accordion";
  const trailEntries = scorecard.raw_scores.map((s) => `
    <div class="trail-entry">
      <div class="trail-entry-head">
        <span>${s.name}</span>
        <span class="mono">confidence ${Math.round(s.confidence * 100)}%</span>
      </div>
      <pre>${JSON.stringify(s, null, 2)}</pre>
    </div>
  `).join("");

  accordion.innerHTML = `
    <button type="button" class="accordion-toggle">
      Reasoning trail
      <span class="accordion-chevron">▾</span>
    </button>
    <div class="accordion-body">${trailEntries}</div>
  `;
  accordion.querySelector(".accordion-toggle").addEventListener("click", () => {
    accordion.classList.toggle("open");
  });
  wrap.appendChild(accordion);

  container.appendChild(wrap);
}

async function exportScorecard(reportId) {
  try {
    const data = await apiFetch("/score/" + reportId + "/export");
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = reportId + "_export.json";
    link.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    toast(err.message, "error");
  }
}

function rubricTitleFor(rubricId) {
  const rubric = state.rubrics.find((r) => r.id === rubricId);
  return rubric ? rubric.title : rubricId;
}

async function loadHistory() {
  const wrap = el("historyTableWrap");
  wrap.innerHTML = "<p class=\"empty-note\">Loading...</p>";

  try {
    const scorecards = await apiFetch("/scorecards");
    state.historyLoaded = true;

    if (scorecards.length === 0) {
      wrap.innerHTML = "<p class=\"empty-note\">Nothing scored yet. Head to the Score tab to run your first report.</p>";
      return;
    }

    const rows = scorecards.map((s) => `
      <tr class="history-row" data-report-id="${s.report_id}">
        <td class="mono">${s.report_id}</td>
        <td>${rubricTitleFor(s.rubric_id)}</td>
        <td><span class="grade-badge grade-${s.grade}">${s.grade}</span></td>
        <td class="mono">${s.weighted_total}</td>
        <td><span class="history-status status-${s.status}">${s.status.replace("_", " ")}</span></td>
        <td>${new Date(s.created_at).toLocaleString()}</td>
      </tr>
    `).join("");

    wrap.innerHTML = `
      <table>
        <thead><tr><th>Report</th><th>Rubric</th><th>Grade</th><th>Score</th><th>Status</th><th>Scored</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    `;

    document.querySelectorAll(".history-row").forEach((row) => {
      row.addEventListener("click", () => openHistoryDetail(row.dataset.reportId));
    });
  } catch (err) {
    wrap.innerHTML = "";
    toast(err.message, "error");
  }
}

async function openHistoryDetail(reportId) {
  const detail = el("historyDetail");
  detail.innerHTML = "<p class=\"empty-note\">Loading report...</p>";
  try {
    const scorecard = await apiFetch("/score/" + reportId);
    detail.innerHTML = "";
    renderResult(scorecard, detail, null);
    detail.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (err) {
    detail.innerHTML = "";
    toast(err.message, "error");
  }
}

async function init() {
  await loadRubrics();
}

init();
