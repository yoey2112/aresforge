import { byId, on, setCodeBlock, setList, setMessage, setText } from "/js/core/dom.js";
import { fetchJson, prunePayload, toQuery } from "/js/core/http.js";

function parseQueueNotesSections(notesValue) {
  const lines = String(notesValue || "").split(/\r?\n/);
  const sections = {
    acceptance: [],
    requestedOutcome: "",
    validation: [],
  };
  let mode = "";
  lines.forEach((rawLine) => {
    const line = String(rawLine || "").trim();
    if (!line) {
      return;
    }
    const lower = line.toLowerCase();
    if (lower === "acceptance criteria:") {
      mode = "acceptance";
      return;
    }
    if (lower === "requested outcome:") {
      mode = "requested";
      return;
    }
    if (lower === "validation notes:") {
      mode = "validation";
      return;
    }
    const value = line.startsWith("- ") ? line.slice(2).trim() : line;
    if (!value) {
      return;
    }
    if (mode === "acceptance") {
      sections.acceptance.push(value);
    } else if (mode === "requested") {
      if (!sections.requestedOutcome) {
        sections.requestedOutcome = value;
      }
    } else if (mode === "validation") {
      sections.validation.push(value);
    }
  });
  return sections;
}

function renderQueueDetailUnavailable(messageText) {
  setText("queue-detail-item-id", "-");
  setText("queue-detail-status", "-");
  setText("queue-detail-type", "-");
  setText("queue-detail-priority", "-");
  setText("queue-detail-message", messageText || "Queue item detail is unavailable.");
  setList("queue-detail-summary", "queue-detail-summary-empty", []);
  setText("queue-detail-description", "No description available.");
  setText("queue-detail-requested-outcome", "No requested outcome captured.");
  setList("queue-detail-acceptance-notes", "queue-detail-acceptance-notes-empty", []);
  setList("queue-detail-validation-notes", "queue-detail-validation-notes-empty", []);
  setList("queue-detail-readiness-summary", "queue-detail-readiness-summary-empty", []);
  setList("queue-detail-readiness-blockers", "queue-detail-readiness-blockers-empty", []);
  setList("queue-detail-readiness-warnings", "queue-detail-readiness-warnings-empty", []);
}

function renderQueueItemDetail(item, readinessPayload) {
  const parsedNotes = parseQueueNotesSections(item && item.notes);
  setText("queue-detail-item-id", (item && item.item_id) || "-");
  setText("queue-detail-status", (item && item.status) || "-");
  setText("queue-detail-type", (item && item.item_type) || "-");
  setText("queue-detail-priority", (item && item.priority) || "-");
  setText("queue-detail-message", "Queue item details loaded (read-only).");
  setList("queue-detail-summary", "queue-detail-summary-empty", [
    `title: ${item && item.title ? item.title : "-"}`,
    `project_id: ${item && item.project_id ? item.project_id : "-"}`,
    `repo_id: ${item && item.repo_id ? item.repo_id : "-"}`,
    `source: ${item && item.source ? item.source : "-"}`,
    `assigned_agent: ${item && item.assigned_agent ? item.assigned_agent : "unassigned"}`,
    `tags: ${(item && item.tags && item.tags.length ? item.tags.join(", ") : "none")}`,
    `created_at: ${item && item.created_at ? item.created_at : "-"}`,
    `updated_at: ${item && item.updated_at ? item.updated_at : "-"}`,
  ]);
  setText("queue-detail-description", (item && item.description) || "No description available.");
  setText("queue-detail-requested-outcome", parsedNotes.requestedOutcome || "No requested outcome captured.");
  setList("queue-detail-acceptance-notes", "queue-detail-acceptance-notes-empty", parsedNotes.acceptance);
  setList("queue-detail-validation-notes", "queue-detail-validation-notes-empty", parsedNotes.validation);

  if (readinessPayload && readinessPayload.ok) {
    const readinessSummary = [
      `readiness_status: ${readinessPayload.readiness_status || "-"}`,
      `can_start: ${Boolean(readinessPayload.can_start)}`,
      `status: ${readinessPayload.status || "-"}`,
      `next_safe_action: ${(readinessPayload.recommended_next_action || readinessPayload.next_safe_action || "-")}`,
    ];
    setList("queue-detail-readiness-summary", "queue-detail-readiness-summary-empty", readinessSummary);
    setList("queue-detail-readiness-blockers", "queue-detail-readiness-blockers-empty", readinessPayload.blockers || []);
    setList("queue-detail-readiness-warnings", "queue-detail-readiness-warnings-empty", readinessPayload.warnings || []);
  } else {
    setList(
      "queue-detail-readiness-summary",
      "queue-detail-readiness-summary-empty",
      ["Readiness data unavailable for this item. Use Inspect Readiness in lifecycle controls if needed."],
    );
    setList("queue-detail-readiness-blockers", "queue-detail-readiness-blockers-empty", []);
    setList("queue-detail-readiness-warnings", "queue-detail-readiness-warnings-empty", []);
  }
}

async function loadQueueItemDetail(itemId, { setLocalQueueLifecycleItemId }) {
  const normalizedItemId = String(itemId || "").trim();
  if (!normalizedItemId) {
    renderQueueDetailUnavailable("No queue item selected. Select a queue item to inspect details.");
    return;
  }
  setText("queue-detail-message", `Loading details for ${normalizedItemId}...`);
  try {
    const detailPayload = await fetchJson(`/api/queue/${encodeURIComponent(normalizedItemId)}`, { method: "GET" });
    let readinessPayload = null;
    try {
      readinessPayload = await fetchJson(`/api/local-queue/items/${encodeURIComponent(normalizedItemId)}/readiness`, { method: "GET" });
    } catch (_readinessError) {
      readinessPayload = null;
    }
    renderQueueItemDetail(detailPayload.item || {}, readinessPayload);
    setLocalQueueLifecycleItemId(normalizedItemId);
  } catch (error) {
    renderQueueDetailUnavailable(`Failed to load queue item details for ${normalizedItemId}.`);
    setMessage("queue-message", String(error.message || error), "error");
  }
}

export function renderQueueReadOnlySummary(payload) {
  const queueTotals = payload.queue_totals || {};
  const activeProject = payload.active_project || {};
  const statusCounts = queueTotals.status_counts || {};
  const groupedItems = payload.items_by_status || {};
  const blockedItems = Array.isArray(payload.blocked_items) ? payload.blocked_items : [];
  const readyItems = Array.isArray(payload.next_ready_items) ? payload.next_ready_items : [];
  const groupedStatuses = ["proposed", "ready", "in_progress", "blocked", "done", "cancelled"];

  setText("queue-readonly-total-count", String(queueTotals.item_count || 0));
  setText("queue-readonly-active-project", activeProject.project_id || "None selected");
  setText("queue-readonly-next-safe-action", payload.next_safe_action || "No recommendation available.");
  setList(
    "queue-readonly-status-counts",
    "queue-readonly-status-counts-empty",
    Object.keys(statusCounts)
      .sort()
      .map((status) => `${status}: ${statusCounts[status]}`),
  );
  setList(
    "queue-readonly-grouped-items",
    "queue-readonly-grouped-items-empty",
    groupedStatuses.map((status) => `${status}: ${((groupedItems[status] || []).length)}`),
  );
  setList(
    "queue-readonly-blocked-items",
    "queue-readonly-blocked-items-empty",
    blockedItems.map((item) => `${item.item_id || "-"} | ${item.title || "(untitled)"} | ${(item.assigned_agent || "").trim() || "unassigned"}`),
  );
  setList(
    "queue-readonly-ready-items",
    "queue-readonly-ready-items-empty",
    readyItems.map((item) => `${item.item_id || "-"} | ${item.title || "(untitled)"} | ${(item.assigned_agent || "").trim() || "unassigned"}`),
  );
}

export function renderQueueReadOnlySummaryUnavailable() {
  setText("queue-readonly-total-count", "0");
  setText("queue-readonly-active-project", "Unavailable");
  setText("queue-readonly-next-safe-action", "Queue summary endpoint unavailable.");
  setList("queue-readonly-status-counts", "queue-readonly-status-counts-empty", []);
  setList("queue-readonly-grouped-items", "queue-readonly-grouped-items-empty", []);
  setList("queue-readonly-blocked-items", "queue-readonly-blocked-items-empty", []);
  setList("queue-readonly-ready-items", "queue-readonly-ready-items-empty", []);
}

export async function loadQueueReadOnlySummary() {
  const payload = await fetchJson("/api/local-queue-agent-summary");
  renderQueueReadOnlySummary(payload);
}

export function renderQueueItems(items, { setLocalQueueLifecycleItemId, reloadQueue, loadDashboardReport }) {
  const container = byId("queue-items");
  const empty = byId("queue-items-empty-state");
  if (!container || !empty) {
    return;
  }
  container.innerHTML = "";
  if (!items || items.length === 0) {
    empty.style.display = "block";
    renderQueueDetailUnavailable("No queue items available. Add or load queue items to inspect details.");
    return;
  }
  empty.style.display = "none";

  items.forEach((item) => {
    const card = document.createElement("article");
    card.className = "card queue-card";
    card.innerHTML = `
      <h3>${item.item_id}</h3>
      <p>${item.title || "(no title)"}</p>
      <p><strong>Project:</strong> ${item.project_id || "-"} | <strong>Repo:</strong> ${item.repo_id || "-"}</p>
      <p><strong>Status:</strong> ${item.status || "-"} | <strong>Priority:</strong> ${item.priority || "-"} | <strong>Type:</strong> ${item.item_type || "-"}</p>
      <p><strong>Assigned:</strong> ${item.assigned_agent || "-"}</p>
    `;
    const controls = document.createElement("div");
    controls.className = "quick-actions";
    const selectButton = document.createElement("button");
    selectButton.type = "button";
    selectButton.textContent = "Use For Lifecycle";
    selectButton.addEventListener("click", () => {
      setLocalQueueLifecycleItemId(item.item_id);
      setMessage("queue-lifecycle-message", `Selected ${item.item_id} for local lifecycle actions.`, "success");
    });
    controls.appendChild(selectButton);
    const detailButton = document.createElement("button");
    detailButton.type = "button";
    detailButton.textContent = "View Details";
    detailButton.addEventListener("click", async () => {
      await loadQueueItemDetail(item.item_id, { setLocalQueueLifecycleItemId });
    });
    controls.appendChild(detailButton);
    ["ready", "in_progress", "blocked", "done"].forEach((status) => {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = `Set ${status}`;
      button.addEventListener("click", async () => {
        try {
          setMessage("queue-message", `Updating ${item.item_id} -> ${status}...`, "loading");
          await fetchJson(`/api/queue/${encodeURIComponent(item.item_id)}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ status }),
          });
          await reloadQueue();
          await loadDashboardReport();
          setMessage("queue-message", `Updated ${item.item_id} to ${status}.`, "success");
        } catch (error) {
          setMessage("queue-message", String(error.message || error), "error");
        }
      });
      controls.appendChild(button);
    });
    card.appendChild(controls);
    container.appendChild(card);
  });
}

export async function loadQueue({ state, countLines, setLocalQueueLifecycleItemId, loadDashboardReport }) {
  setMessage("queue-message", "Loading queue...", "loading");
  try {
    await loadQueueReadOnlySummary();
  } catch (_error) {
    renderQueueReadOnlySummaryUnavailable();
  }
  const payload = await fetchJson(`/api/queue${toQuery(state.queueFilters)}`);
  renderQueueItems(payload.items || [], {
    setLocalQueueLifecycleItemId,
    reloadQueue: () => loadQueue({ state, countLines, setLocalQueueLifecycleItemId, loadDashboardReport }),
    loadDashboardReport,
  });
  setList(
    "queue-counts",
    "queue-counts-empty-state",
    [].concat(
      countLines("status", payload.counts_by_status),
      countLines("type", payload.counts_by_type),
      countLines("priority", payload.counts_by_priority),
    ),
  );
  setMessage(
    "queue-message",
    payload.warnings && payload.warnings.length ? payload.warnings.join(" | ") : "Queue loaded.",
    payload.warnings && payload.warnings.length ? "warn" : "success",
  );
  if (!payload.items || payload.items.length === 0) {
    renderQueueDetailUnavailable("No queue items available. Add or load queue items to inspect details.");
  } else {
    renderQueueDetailUnavailable("No queue item selected. Select a queue item to inspect details.");
  }
}

export function bindQueueActions({
  state,
  loadQueueData,
  applyActiveProjectDefaultsToQueueForm,
  activeProjectId,
  activeRepoId,
  buildQueuePayload,
  refreshSummaryAndReport,
}) {
  on("queue-use-active-project", "click", () => {
    applyActiveProjectDefaultsToQueueForm();
    setMessage(
      "queue-message",
      activeProjectId() ? "Active project defaults applied to queue form." : "No active project selected.",
      activeProjectId() ? "success" : "warn",
    );
  });

  on("queue-filter-active-project", "click", async () => {
    if (!activeProjectId()) {
      setMessage("queue-message", "No active project selected.", "warn");
      return;
    }
    byId("filter-project-id").value = activeProjectId();
    byId("filter-repo-id").value = activeRepoId();
    state.queueFilters.project_id = activeProjectId();
    state.queueFilters.repo_id = activeRepoId();
    try {
      await loadQueueData();
      setMessage("queue-message", "Queue filtered to active project.", "success");
    } catch (error) {
      setMessage("queue-message", String(error.message || error), "error");
    }
  });

  on("queue-filter-form", "submit", async (event) => {
    event.preventDefault();
    state.queueFilters.project_id = byId("filter-project-id").value.trim();
    state.queueFilters.repo_id = byId("filter-repo-id").value.trim();
    state.queueFilters.status = byId("filter-status").value.trim();
    state.queueFilters.type = byId("filter-type").value.trim();
    state.queueFilters.assigned_agent = byId("filter-assigned-agent").value.trim();
    try {
      await loadQueueData();
    } catch (error) {
      setMessage("queue-message", String(error.message || error), "error");
    }
  });

  on("queue-filter-reset", "click", async () => {
    byId("filter-project-id").value = "";
    byId("filter-repo-id").value = "";
    byId("filter-status").value = "";
    byId("filter-type").value = "";
    byId("filter-assigned-agent").value = "";
    state.queueFilters = { project_id: "", repo_id: "", status: "", type: "", assigned_agent: "" };
    try {
      await loadQueueData();
      setMessage("queue-message", "Filters reset.", "success");
    } catch (error) {
      setMessage("queue-message", String(error.message || error), "error");
    }
  });

  on("queue-form", "submit", async (event) => {
    event.preventDefault();
    try {
      setMessage("queue-message", "Saving queue item...", "loading");
      await fetchJson("/api/queue", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildQueuePayload()),
      });
      await loadQueueData();
      await refreshSummaryAndReport();
      setMessage("queue-message", "Queue item saved.", "success");
    } catch (error) {
      setMessage("queue-message", String(error.message || error), "error");
    }
  });
}

export function buildQueuePayload({ activeProjectId, activeRepoId, parseCommaList }) {
  if (!byId("queue-project-id").value.trim() && activeProjectId()) {
    byId("queue-project-id").value = activeProjectId();
  }
  if (!byId("queue-repo-id").value.trim() && activeRepoId()) {
    byId("queue-repo-id").value = activeRepoId();
  }
  return prunePayload({
    item_id: byId("queue-item-id").value.trim(),
    project_id: byId("queue-project-id").value.trim(),
    repo_id: byId("queue-repo-id").value.trim(),
    title: byId("queue-title").value.trim(),
    description: byId("queue-description").value.trim(),
    status: byId("queue-status").value.trim(),
    priority: byId("queue-priority").value.trim(),
    item_type: byId("queue-item-type").value.trim(),
    tags: parseCommaList(byId("queue-tags").value),
    dependencies: parseCommaList(byId("queue-dependencies").value),
    blocked_by: parseCommaList(byId("queue-blocked-by").value),
    assigned_agent: byId("queue-assigned-agent").value.trim(),
    source: byId("queue-source").value.trim(),
    notes: byId("queue-notes").value.trim(),
  });
}

export function setLocalQueueLifecycleItemId(itemId) {
  const value = String(itemId || "").trim();
  if (byId("queue-lifecycle-item-id")) {
    byId("queue-lifecycle-item-id").value = value;
  }
}

function selectedLocalQueueLifecycleItemId() {
  return byId("queue-lifecycle-item-id") ? byId("queue-lifecycle-item-id").value.trim() : "";
}

function requireLocalQueueLifecycleItemId() {
  const itemId = selectedLocalQueueLifecycleItemId();
  if (!itemId) {
    throw new Error("Enter an item_id or select one from Queue Items first.");
  }
  return itemId;
}

function buildLocalQueueAddPayload({ parseCommaList, parseLineList }) {
  return prunePayload({
    title: byId("queue-lifecycle-add-title").value.trim(),
    description: byId("queue-lifecycle-add-description").value.trim(),
    item_type: byId("queue-lifecycle-add-type").value.trim(),
    priority: byId("queue-lifecycle-add-priority").value.trim(),
    target_area: byId("queue-lifecycle-add-target-area").value.trim(),
    tags: parseCommaList(byId("queue-lifecycle-add-tags").value),
    acceptance_criteria: parseLineList(byId("queue-lifecycle-add-acceptance-criteria").value),
  });
}

function buildLocalQueueCodexPromptPayload() {
  return {
    output: byId("queue-lifecycle-codex-output").value.trim(),
    commit_message: byId("queue-lifecycle-codex-commit-message").value.trim(),
    force: Boolean(byId("queue-lifecycle-codex-force") && byId("queue-lifecycle-codex-force").checked),
  };
}

function buildLocalQueueCompletePayload({ parseLineList }) {
  return prunePayload({
    commit_hash: byId("queue-lifecycle-complete-commit-hash").value.trim(),
    completed_by: byId("queue-lifecycle-complete-completed-by").value.trim(),
    validation_summary: byId("queue-lifecycle-complete-validation-summary").value.trim(),
    evidence_note: byId("queue-lifecycle-complete-evidence-note").value.trim(),
    tests_run: parseLineList(byId("queue-lifecycle-complete-tests-run").value),
    changed_files: parseLineList(byId("queue-lifecycle-complete-changed-files").value),
    artifact_paths: parseLineList(byId("queue-lifecycle-complete-artifact-paths").value),
  });
}

export function renderLocalQueueAddResult(payload) {
  setList("queue-lifecycle-add-result", "queue-lifecycle-add-result-empty", [
    `item_id: ${payload && payload.item_id ? payload.item_id : "-"}`,
    `status: ${payload && payload.status ? payload.status : "-"}`,
    `project_id: ${payload && payload.project_id ? payload.project_id : "-"}`,
    `repo_id: ${payload && payload.repo_id ? payload.repo_id : "-"}`,
    `next_safe_action: ${payload && payload.next_safe_action ? payload.next_safe_action : "-"}`,
  ].concat((payload && payload.warnings ? payload.warnings : []).map((warning) => `warning: ${warning}`)));
  if (payload && payload.item_id) {
    setLocalQueueLifecycleItemId(payload.item_id);
  }
}

function renderLocalQueueReadinessResult(payload) {
  setList("queue-lifecycle-readiness-summary", "queue-lifecycle-readiness-summary-empty", [
    `item_id: ${payload && payload.item_id ? payload.item_id : "-"}`,
    `readiness_status: ${payload && payload.readiness_status ? payload.readiness_status : "-"}`,
    `can_start: ${Boolean(payload && payload.can_start)}`,
    `status: ${payload && payload.status ? payload.status : "-"}`,
    `next_safe_action: ${payload && (payload.recommended_next_action || payload.next_safe_action) ? (payload.recommended_next_action || payload.next_safe_action) : "-"}`,
  ]);
  setList("queue-lifecycle-readiness-blockers", "queue-lifecycle-readiness-blockers-empty", (payload && payload.blockers) || []);
  setList("queue-lifecycle-readiness-warnings", "queue-lifecycle-readiness-warnings-empty", (payload && payload.warnings) || []);
}

function renderLocalQueueStartResult(payload) {
  const readiness = (payload && payload.readiness) || {};
  setList("queue-lifecycle-start-summary", "queue-lifecycle-start-summary-empty", [
    `item_id: ${payload && payload.item_id ? payload.item_id : "-"}`,
    `previous_status: ${payload && payload.previous_status ? payload.previous_status : "-"}`,
    `status: ${payload && payload.status ? payload.status : "-"}`,
    `readiness_status: ${readiness.readiness_status || payload.readiness_status || "-"}`,
    `message: ${payload && payload.message ? payload.message : "-"}`,
  ].concat((payload && payload.warnings ? payload.warnings : []).map((warning) => `warning: ${warning}`)));
}

function renderLocalQueueCodexPromptResult(payload) {
  setList("queue-lifecycle-codex-summary", "queue-lifecycle-codex-summary-empty", [
    `item_id: ${payload && payload.item_id ? payload.item_id : "-"}`,
    `readiness_status: ${payload && payload.readiness_status ? payload.readiness_status : "-"}`,
    `output_path: ${payload && payload.output_path ? payload.output_path : "-"}`,
    `commit_message: ${payload && payload.commit_message ? payload.commit_message : "-"}`,
  ].concat((payload && payload.warnings ? payload.warnings : []).map((warning) => `warning: ${warning}`)));
  setCodeBlock("queue-lifecycle-codex-prompt", "queue-lifecycle-codex-prompt-empty", (payload && payload.prompt) || "");
}

function renderLocalQueueCompleteResult(payload) {
  setList("queue-lifecycle-complete-summary", "queue-lifecycle-complete-summary-empty", [
    `item_id: ${payload && payload.item_id ? payload.item_id : "-"}`,
    `previous_status: ${payload && payload.previous_status ? payload.previous_status : "-"}`,
    `status: ${payload && payload.status ? payload.status : "-"}`,
    `completion_commit: ${payload && payload.completion_commit ? payload.completion_commit : "-"}`,
    `validation_summary: ${payload && payload.validation_summary ? payload.validation_summary : "-"}`,
  ]);
  setList("queue-lifecycle-complete-warnings", "queue-lifecycle-complete-warnings-empty", (payload && payload.warnings) || []);
}

export function bindQueueLifecycleActions({
  parseCommaList,
  parseLineList,
  loadQueueData,
  refreshSummaryAndReport,
}) {
  on("queue-lifecycle-add-form", "submit", async (event) => {
    event.preventDefault();
    const submitButton = byId("queue-lifecycle-add-submit");
    const originalLabel = submitButton ? submitButton.textContent : "";
    try {
      if (submitButton) {
        submitButton.disabled = true;
        submitButton.textContent = "Adding...";
      }
      setMessage("queue-lifecycle-message", "Adding local queue task...", "loading");
      const payload = await fetchJson("/api/local-queue/items", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildLocalQueueAddPayload({ parseCommaList, parseLineList })),
      });
      renderLocalQueueAddResult(payload);
      await loadQueueData();
      await refreshSummaryAndReport();
      setMessage("queue-lifecycle-message", `Added ${payload.item_id}.`, "success");
    } catch (error) {
      renderLocalQueueAddResult((error && error.payload) || null);
      setMessage("queue-lifecycle-message", String(error.message || error), "error");
    } finally {
      if (submitButton) {
        submitButton.disabled = false;
        submitButton.textContent = originalLabel;
      }
    }
  });

  on("queue-lifecycle-readiness", "click", async () => {
    try {
      const itemId = requireLocalQueueLifecycleItemId();
      setMessage("queue-lifecycle-message", `Inspecting readiness for ${itemId}...`, "loading");
      const payload = await fetchJson(`/api/local-queue/items/${encodeURIComponent(itemId)}/readiness`, { method: "GET" });
      renderLocalQueueReadinessResult(payload);
      setMessage("queue-lifecycle-message", `Readiness loaded for ${itemId}.`, "success");
    } catch (error) {
      renderLocalQueueReadinessResult((error && error.payload) || { item_id: selectedLocalQueueLifecycleItemId(), blockers: [], warnings: [] });
      setMessage("queue-lifecycle-message", String(error.message || error), "error");
    }
  });

  on("queue-lifecycle-start", "click", async () => {
    try {
      const itemId = requireLocalQueueLifecycleItemId();
      setMessage("queue-lifecycle-message", `Starting ${itemId}...`, "loading");
      const payload = await fetchJson(`/api/local-queue/items/${encodeURIComponent(itemId)}/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      renderLocalQueueStartResult(payload);
      await loadQueueData();
      await refreshSummaryAndReport();
      setMessage("queue-lifecycle-message", `Started ${itemId}.`, "success");
    } catch (error) {
      renderLocalQueueStartResult((error && error.payload) || { item_id: selectedLocalQueueLifecycleItemId() });
      setMessage("queue-lifecycle-message", String(error.message || error), "error");
    }
  });

  on("queue-lifecycle-codex-form", "submit", async (event) => {
    event.preventDefault();
    const submitButton = byId("queue-lifecycle-codex-submit");
    const originalLabel = submitButton ? submitButton.textContent : "";
    try {
      if (submitButton) {
        submitButton.disabled = true;
        submitButton.textContent = "Generating...";
      }
      const itemId = requireLocalQueueLifecycleItemId();
      setMessage("queue-lifecycle-message", `Generating local Codex prompt for ${itemId}...`, "loading");
      const payload = await fetchJson(`/api/local-queue/items/${encodeURIComponent(itemId)}/codex-prompt`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildLocalQueueCodexPromptPayload()),
      });
      renderLocalQueueCodexPromptResult(payload);
      setMessage("queue-lifecycle-message", `Codex prompt generated for ${itemId}.`, "success");
    } catch (error) {
      renderLocalQueueCodexPromptResult((error && error.payload) || null);
      setMessage("queue-lifecycle-message", String(error.message || error), "error");
    } finally {
      if (submitButton) {
        submitButton.disabled = false;
        submitButton.textContent = originalLabel;
      }
    }
  });

  on("queue-lifecycle-complete-form", "submit", async (event) => {
    event.preventDefault();
    const submitButton = byId("queue-lifecycle-complete-submit");
    const originalLabel = submitButton ? submitButton.textContent : "";
    try {
      if (submitButton) {
        submitButton.disabled = true;
        submitButton.textContent = "Completing...";
      }
      const itemId = requireLocalQueueLifecycleItemId();
      setMessage("queue-lifecycle-message", `Completing ${itemId} with local evidence...`, "loading");
      const payload = await fetchJson(`/api/local-queue/items/${encodeURIComponent(itemId)}/complete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildLocalQueueCompletePayload({ parseLineList })),
      });
      renderLocalQueueCompleteResult(payload);
      await loadQueueData();
      await refreshSummaryAndReport();
      setMessage("queue-lifecycle-message", `Completed ${itemId}.`, "success");
    } catch (error) {
      renderLocalQueueCompleteResult((error && error.payload) || null);
      setMessage("queue-lifecycle-message", String(error.message || error), "error");
    } finally {
      if (submitButton) {
        submitButton.disabled = false;
        submitButton.textContent = originalLabel;
      }
    }
  });
}
