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
  const routingMetadata = (item && item.routing_metadata) || {};
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
    `routing_agent_lane: ${routingMetadata.recommended_agent_lane || "unassigned"}`,
    `routing_engine: ${routingMetadata.recommended_engine || "unassigned"}`,
    `routing_risk: ${routingMetadata.risk_level || "unknown"}`,
    `routing_complexity: ${routingMetadata.complexity_level || "unknown"}`,
    "routing_execution: not implemented",
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

function routedViewQuery() {
  return toQuery({
    status: byId("queue-routed-status") && byId("queue-routed-status").value,
    agent_lane: byId("queue-routed-agent-lane") && byId("queue-routed-agent-lane").value,
    engine: byId("queue-routed-engine") && byId("queue-routed-engine").value,
    risk_level: byId("queue-routed-risk") && byId("queue-routed-risk").value,
    complexity_level: byId("queue-routed-complexity") && byId("queue-routed-complexity").value,
    group_by: byId("queue-routed-group-by") && byId("queue-routed-group-by").value,
    include_unrouted: byId("queue-routed-include-unrouted") && byId("queue-routed-include-unrouted").checked ? "true" : "false",
  });
}

export function renderRoutedQueueViews(payload) {
  setText("queue-routed-next-safe-action", (payload && payload.next_safe_action) || "Routed views unavailable.");
  setList("queue-routed-summary", "queue-routed-summary-empty", [
    `source_queue: ${payload && payload.source_queue ? payload.source_queue : "-"}`,
    `group_by: ${payload && payload.group_by ? payload.group_by : "-"}`,
    `total_items: ${payload && typeof payload.total_items === "number" ? payload.total_items : 0}`,
    `routed_items_count: ${payload && typeof payload.routed_items_count === "number" ? payload.routed_items_count : 0}`,
    `unrouted_items_count: ${payload && typeof payload.unrouted_items_count === "number" ? payload.unrouted_items_count : 0}`,
    `execution_allowed: ${Boolean(payload && payload.execution_allowed)}`,
  ]);
  const groups = (payload && payload.groups) || {};
  setList(
    "queue-routed-groups",
    "queue-routed-groups-empty",
    Object.keys(groups).sort().map((key) => `${key}: ${groups[key].count || 0}`),
  );
  setList(
    "queue-routed-items",
    "queue-routed-items-empty",
    ((payload && payload.items) || []).map((item) => {
      const metadata = item.routing_metadata || {};
      return `${item.item_id || "-"} | ${item.title || "(untitled)"} | status=${item.status || "-"} | lane=${metadata.recommended_agent_lane || "unrouted"} | engine=${metadata.recommended_engine || "unrouted"} | risk=${metadata.risk_level || "unknown"} | routed=${Boolean(item.routed)}`;
    }),
  );
}

export async function loadRoutedQueueViews() {
  const payload = await fetchJson(`/api/local-queue/routed-views${routedViewQuery()}`, { method: "GET" });
  renderRoutedQueueViews(payload);
  return payload;
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

function buildCodexHighValuePromptPayload() {
  return prunePayload({
    output: byId("queue-codex-high-value-output").value.trim(),
    include_context: Boolean(byId("queue-codex-high-value-include-context") && byId("queue-codex-high-value-include-context").checked),
    include_validation_expectations: Boolean(byId("queue-codex-high-value-include-validation") && byId("queue-codex-high-value-include-validation").checked),
    include_operating_rules: Boolean(byId("queue-codex-high-value-include-rules") && byId("queue-codex-high-value-include-rules").checked),
    operator_override: Boolean(byId("queue-codex-high-value-operator-override") && byId("queue-codex-high-value-operator-override").checked),
    force: Boolean(byId("queue-codex-high-value-force") && byId("queue-codex-high-value-force").checked),
  });
}

function buildLocalLlmPromptPreviewPayload() {
  return prunePayload({
    prompt_style: byId("queue-local-llm-preview-style").value.trim(),
    output: byId("queue-local-llm-preview-output").value.trim(),
    include_context: Boolean(byId("queue-local-llm-preview-include-context") && byId("queue-local-llm-preview-include-context").checked),
    include_validation_expectations: Boolean(byId("queue-local-llm-preview-include-validation") && byId("queue-local-llm-preview-include-validation").checked),
    force: Boolean(byId("queue-local-llm-preview-force") && byId("queue-local-llm-preview-force").checked),
  });
}

function buildLocalLlmExecutePayload() {
  return prunePayload({
    confirm_operator_gate: Boolean(byId("queue-local-llm-execute-confirm") && byId("queue-local-llm-execute-confirm").checked),
    use_preview: true,
    output: byId("queue-local-llm-execute-output").value.trim(),
    force: Boolean(byId("queue-local-llm-execute-force") && byId("queue-local-llm-execute-force").checked),
    operator_override: Boolean(byId("queue-local-llm-execute-operator-override") && byId("queue-local-llm-execute-operator-override").checked),
    dry_run: Boolean(byId("queue-local-llm-execute-dry-run") && byId("queue-local-llm-execute-dry-run").checked),
  });
}

function buildLocalQueuePromptPackPayload({ parseCommaList }) {
  return prunePayload({
    item_ids: parseCommaList(byId("queue-prompt-pack-item-ids").value),
    statuses: parseCommaList(byId("queue-prompt-pack-statuses").value),
    output: byId("queue-prompt-pack-output").value.trim(),
    force: Boolean(byId("queue-prompt-pack-force") && byId("queue-prompt-pack-force").checked),
    include_routing: Boolean(byId("queue-prompt-pack-include-routing") && byId("queue-prompt-pack-include-routing").checked),
    group_by_routing: Boolean(byId("queue-prompt-pack-group-by-routing") && byId("queue-prompt-pack-group-by-routing").checked),
    routing_group_by: byId("queue-prompt-pack-routing-group-by") && byId("queue-prompt-pack-routing-group-by").value,
    include_unrouted: Boolean(byId("queue-prompt-pack-include-unrouted") && byId("queue-prompt-pack-include-unrouted").checked),
    recommend_missing_routing: Boolean(byId("queue-prompt-pack-recommend-missing-routing") && byId("queue-prompt-pack-recommend-missing-routing").checked),
    include_prompt_text: true,
  });
}

function buildExecutionAuditQuery() {
  return toQuery({
    item_id: byId("queue-execution-audit-item-id") && byId("queue-execution-audit-item-id").value.trim(),
    action_type: byId("queue-execution-audit-action-type") && byId("queue-execution-audit-action-type").value.trim(),
    engine: byId("queue-execution-audit-engine") && byId("queue-execution-audit-engine").value.trim(),
    limit: byId("queue-execution-audit-limit") && byId("queue-execution-audit-limit").value.trim(),
  });
}

function buildAiArtifactsQuery() {
  return toQuery({
    item_id: byId("queue-ai-artifacts-item-id") && byId("queue-ai-artifacts-item-id").value.trim(),
    artifact_type: byId("queue-ai-artifacts-type") && byId("queue-ai-artifacts-type").value.trim(),
    source_action: byId("queue-ai-artifacts-source-action") && byId("queue-ai-artifacts-source-action").value.trim(),
    engine: byId("queue-ai-artifacts-engine") && byId("queue-ai-artifacts-engine").value.trim(),
    exists: byId("queue-ai-artifacts-exists") && byId("queue-ai-artifacts-exists").value,
    limit: byId("queue-ai-artifacts-limit") && byId("queue-ai-artifacts-limit").value.trim(),
  });
}

function buildOperatorRunHistoryQuery() {
  return toQuery({
    project_id: byId("queue-operator-run-history-project-id") && byId("queue-operator-run-history-project-id").value.trim(),
    item_id: byId("queue-operator-run-history-item-id") && byId("queue-operator-run-history-item-id").value.trim(),
    action_type: byId("queue-operator-run-history-action-type") && byId("queue-operator-run-history-action-type").value.trim(),
    artifact_type: byId("queue-operator-run-history-artifact-type") && byId("queue-operator-run-history-artifact-type").value.trim(),
    limit: byId("queue-operator-run-history-limit") && byId("queue-operator-run-history-limit").value.trim(),
  });
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

function buildLocalQueueEvidencePayload({ parseLineList }) {
  return prunePayload({
    evidence_summary: byId("queue-lifecycle-evidence-summary").value.trim(),
    validation_commands: parseLineList(byId("queue-lifecycle-evidence-validation-commands").value),
    validation_results: parseLineList(byId("queue-lifecycle-evidence-validation-results").value),
    smoke_checks: parseLineList(byId("queue-lifecycle-evidence-smoke-checks").value),
    diff_check_result: byId("queue-lifecycle-evidence-diff-check-result").value.trim(),
    files_changed: parseLineList(byId("queue-lifecycle-evidence-files-changed").value),
    commit_hash: byId("queue-lifecycle-evidence-commit-hash").value.trim(),
    push_result: byId("queue-lifecycle-evidence-push-result").value.trim(),
    operator_notes: byId("queue-lifecycle-evidence-operator-notes").value.trim(),
  });
}

function buildLocalQueueCloseoutPayload() {
  return prunePayload({
    closed_by: byId("queue-lifecycle-closeout-closed-by").value.trim(),
    closeout_summary: byId("queue-lifecycle-closeout-summary").value.trim(),
  });
}

function buildRoutingRecommendationPayload({ parseLineList }) {
  return prunePayload({
    risk_level: byId("queue-lifecycle-routing-risk").value.trim(),
    complexity_level: byId("queue-lifecycle-routing-complexity").value.trim(),
    affected_files: parseLineList(byId("queue-lifecycle-routing-affected-files").value),
    validation_burden: byId("queue-lifecycle-routing-validation-burden").value.trim(),
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

function renderCodexHighValuePromptResult(payload) {
  setList("queue-codex-high-value-summary", "queue-codex-high-value-summary-empty", [
    `item_id: ${payload && payload.item_id ? payload.item_id : "-"}`,
    `eligible_for_codex_lane: ${Boolean(payload && payload.eligible_for_codex_lane)}`,
    `recommended_engine: ${payload && payload.recommended_engine ? payload.recommended_engine : "-"}`,
    `recommended_model: ${payload && payload.recommended_model ? payload.recommended_model : "-"}`,
    `execution_allowed: ${Boolean(payload && payload.execution_allowed)}`,
    `codex_lane_reason: ${payload && payload.codex_lane_reason ? payload.codex_lane_reason : "-"}`,
    `output_path: ${payload && payload.output_path ? payload.output_path : "-"}`,
    `next_safe_action: ${payload && payload.next_safe_action ? payload.next_safe_action : "-"}`,
  ].concat([
    ...((payload && payload.warnings) || []).map((warning) => `warning: ${warning}`),
    ...((payload && payload.blockers) || []).map((blocker) => `blocker: ${blocker}`),
  ]));
  setCodeBlock("queue-codex-high-value-preview", "queue-codex-high-value-preview-empty", (payload && payload.prompt_preview) || "");
}

function renderLocalLlmPromptPreviewResult(payload) {
  setList("queue-local-llm-preview-summary", "queue-local-llm-preview-summary-empty", [
    `item_id: ${payload && payload.item_id ? payload.item_id : "-"}`,
    `recommended_engine: ${payload && payload.recommended_engine ? payload.recommended_engine : "-"}`,
    `recommended_model: ${payload && payload.recommended_model ? payload.recommended_model : "-"}`,
    `preview_allowed: ${Boolean(payload && payload.preview_allowed)}`,
    `execution_allowed: ${Boolean(payload && payload.execution_allowed)}`,
    `output_path: ${payload && payload.output_path ? payload.output_path : "-"}`,
    `next_safe_action: ${payload && payload.next_safe_action ? payload.next_safe_action : "-"}`,
  ].concat([
    ...((payload && payload.warnings) || []).map((warning) => `warning: ${warning}`),
    ...((payload && payload.blockers) || []).map((blocker) => `blocker: ${blocker}`),
  ]));
  setCodeBlock("queue-local-llm-preview", "queue-local-llm-preview-empty", (payload && payload.prompt_preview) || "");
}

function renderLocalLlmExecuteResult(payload) {
  setList("queue-local-llm-execute-summary", "queue-local-llm-execute-summary-empty", [
    `item_id: ${payload && payload.item_id ? payload.item_id : "-"}`,
    `provider: ${payload && payload.provider ? payload.provider : "-"}`,
    `model: ${payload && payload.model ? payload.model : "-"}`,
    `execution_allowed: ${Boolean(payload && payload.execution_allowed)}`,
    `executed: ${Boolean(payload && payload.executed)}`,
    `dry_run: ${Boolean(payload && payload.dry_run)}`,
    `result_artifact_path: ${payload && payload.result_artifact_path ? payload.result_artifact_path : "-"}`,
    `captured_at: ${payload && payload.captured_at ? payload.captured_at : "-"}`,
    `next_safe_action: ${payload && payload.next_safe_action ? payload.next_safe_action : "-"}`,
  ].concat([
    ...((payload && payload.warnings) || []).map((warning) => `warning: ${warning}`),
    ...((payload && payload.blockers) || []).map((blocker) => `blocker: ${blocker}`),
  ]));
  setCodeBlock("queue-local-llm-execute-response", "queue-local-llm-execute-response-empty", (payload && payload.response_text) || "");
}

function renderLocalQueuePromptPackResult(payload) {
  setList("queue-prompt-pack-summary", "queue-prompt-pack-summary-empty", [
    `item_count: ${payload && typeof payload.item_count === "number" ? payload.item_count : 0}`,
    `groups: ${payload && payload.groups && payload.groups.length ? payload.groups.join(" | ") : "none"}`,
    `include_routing: ${Boolean(payload && payload.include_routing)}`,
    `group_by_routing: ${Boolean(payload && payload.group_by_routing)}`,
    `routing_group_by: ${payload && payload.routing_group_by ? payload.routing_group_by : "-"}`,
    `execution_allowed: ${Boolean(payload && payload.execution_allowed)}`,
    `output_path: ${payload && payload.output_path ? payload.output_path : "-"}`,
    `next_safe_action: ${payload && payload.next_safe_action ? payload.next_safe_action : "-"}`,
  ].concat((payload && payload.warnings ? payload.warnings : []).map((warning) => `warning: ${warning}`)));
  setCodeBlock("queue-prompt-pack-preview", "queue-prompt-pack-preview-empty", (payload && payload.prompt_pack) || "");
}

function renderExecutionAuditLog(payload) {
  setList("queue-execution-audit-summary", "queue-execution-audit-summary-empty", [
    `total_entries: ${payload && typeof payload.total_entries === "number" ? payload.total_entries : 0}`,
    `generated_at: ${payload && payload.generated_at ? payload.generated_at : "-"}`,
    `next_safe_action: ${payload && payload.next_safe_action ? payload.next_safe_action : "-"}`,
  ].concat((payload && payload.warnings ? payload.warnings : []).map((warning) => `warning: ${warning}`)));
  setList(
    "queue-execution-audit-entries",
    "queue-execution-audit-entries-empty",
    ((payload && payload.entries) || []).map((entry) => `${entry.timestamp || "-"} | ${entry.action_type || "-"} | item=${entry.item_id || "-"} | engine=${entry.engine || "-"} | outcome=${entry.outcome || "-"} | executed=${Boolean(entry.executed)}`),
  );
}

function renderAiArtifactRegistry(payload) {
  setList("queue-ai-artifacts-summary", "queue-ai-artifacts-summary-empty", [
    `total_artifacts: ${payload && typeof payload.total_artifacts === "number" ? payload.total_artifacts : 0}`,
    `generated_at: ${payload && payload.generated_at ? payload.generated_at : "-"}`,
    `next_safe_action: ${payload && payload.next_safe_action ? payload.next_safe_action : "-"}`,
  ].concat((payload && payload.warnings ? payload.warnings : []).map((warning) => `warning: ${warning}`)));
  setList(
    "queue-ai-artifacts-entries",
    "queue-ai-artifacts-entries-empty",
    ((payload && payload.artifacts) || []).map((artifact) => `${artifact.created_at || "-"} | ${artifact.artifact_type || "-"} | item=${artifact.item_id || "-"} | exists=${Boolean(artifact.exists)} | ${artifact.artifact_path || "-"}`),
  );
}

function renderOperatorRunHistory(payload) {
  setList("queue-operator-run-history-summary", "queue-operator-run-history-summary-empty", [
    `total_audit_entries: ${payload && typeof payload.total_audit_entries === "number" ? payload.total_audit_entries : 0}`,
    `total_artifacts: ${payload && typeof payload.total_artifacts === "number" ? payload.total_artifacts : 0}`,
    `timeline_entries: ${payload && payload.timeline ? payload.timeline.length : 0}`,
    `generated_at: ${payload && payload.generated_at ? payload.generated_at : "-"}`,
    `next_safe_action: ${payload && payload.next_safe_action ? payload.next_safe_action : "-"}`,
  ].concat((payload && payload.warnings ? payload.warnings : []).map((warning) => `warning: ${warning}`)));
  setList(
    "queue-operator-run-history-timeline",
    "queue-operator-run-history-timeline-empty",
    ((payload && payload.timeline) || []).map((entry) => `${entry.timestamp || "-"} | ${entry.kind || "-"} | item=${entry.item_id || "-"} | action=${entry.action_type || "-"} | artifact=${entry.artifact_type || "-"} | outcome=${entry.outcome || "-"} | safety=${entry.safety_status || "-"} | gate=${entry.gate_status || "-"} | executed=${Boolean(entry.executed)} | allowed=${Boolean(entry.execution_allowed)} | repo_mutation=${Boolean(entry.repo_mutation_allowed)} | external_mutation=${Boolean(entry.external_mutation_allowed)} | automatic_execution=${Boolean(entry.automatic_execution_allowed)} | path=${entry.artifact_path || "-"}`),
  );
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

function renderLocalQueueEvidenceResult(payload) {
  const evidence = (payload && payload.completion_evidence) || {};
  setList("queue-lifecycle-evidence-summary-list", "queue-lifecycle-evidence-summary-list-empty", [
    `item_id: ${payload && payload.item_id ? payload.item_id : "-"}`,
    `status: ${payload && payload.status ? payload.status : "-"}`,
    `captured_at: ${payload && payload.captured_at ? payload.captured_at : evidence.captured_at || "-"}`,
    `closeout_eligible: ${Boolean(payload && payload.closeout_eligible)}`,
    `commit_hash: ${evidence.commit_hash || "-"}`,
    `diff_check_result: ${evidence.diff_check_result || "-"}`,
    `next_safe_action: ${payload && payload.next_safe_action ? payload.next_safe_action : "-"}`,
  ]);
  setList("queue-lifecycle-evidence-warnings", "queue-lifecycle-evidence-warnings-empty", (payload && payload.warnings) || []);
}

function renderLocalQueueCloseoutResult(payload) {
  setList("queue-lifecycle-closeout-summary-list", "queue-lifecycle-closeout-summary-list-empty", [
    `item_id: ${payload && payload.item_id ? payload.item_id : "-"}`,
    `previous_status: ${payload && payload.previous_status ? payload.previous_status : "-"}`,
    `status: ${payload && payload.status ? payload.status : "-"}`,
    `closed_at: ${payload && payload.closed_at ? payload.closed_at : "-"}`,
    `closed_by: ${payload && payload.closed_by ? payload.closed_by : "-"}`,
    `next_safe_action: ${payload && payload.next_safe_action ? payload.next_safe_action : "-"}`,
  ]);
  setList("queue-lifecycle-closeout-warnings", "queue-lifecycle-closeout-warnings-empty", (payload && payload.warnings) || []);
}

function renderRoutingRecommendationResult(payload) {
  setList("queue-lifecycle-routing-summary", "queue-lifecycle-routing-summary-empty", [
    `item_id: ${payload && payload.item_id ? payload.item_id : "-"}`,
    `project_ai_mode: ${payload && payload.project_ai_mode ? payload.project_ai_mode : "-"}`,
    `recommended_agent_lane: ${payload && payload.recommended_agent_lane ? payload.recommended_agent_lane : "manual_required"}`,
    `recommended_engine: ${payload && payload.recommended_engine ? payload.recommended_engine : "manual_required"}`,
    `fallback_engine: ${payload && payload.fallback_engine ? payload.fallback_engine : "-"}`,
    `risk_level: ${payload && payload.risk_level ? payload.risk_level : "unknown"}`,
    `complexity_level: ${payload && payload.complexity_level ? payload.complexity_level : "unknown"}`,
    `metadata_written: ${Boolean(payload && payload.metadata_written)}`,
    `execution_allowed: ${Boolean(payload && payload.execution_allowed)}`,
    `next_safe_action: ${payload && payload.next_safe_action ? payload.next_safe_action : "-"}`,
  ]);
  setList("queue-lifecycle-routing-warnings", "queue-lifecycle-routing-warnings-empty", [
    ...((payload && payload.warnings) || []),
    ...((payload && payload.blockers) || []),
  ]);
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

  on("queue-routed-views-form", "submit", async (event) => {
    event.preventDefault();
    try {
      setMessage("queue-lifecycle-message", "Loading routed queue views...", "loading");
      await loadRoutedQueueViews();
      setMessage("queue-lifecycle-message", "Routed queue views loaded. No execution performed.", "success");
    } catch (error) {
      renderRoutedQueueViews((error && error.payload) || null);
      setMessage("queue-lifecycle-message", String(error.message || error), "error");
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

  on("queue-lifecycle-routing-form", "submit", async (event) => {
    event.preventDefault();
    const submitButton = byId("queue-lifecycle-routing-recommend-submit");
    const originalLabel = submitButton ? submitButton.textContent : "";
    try {
      if (submitButton) {
        submitButton.disabled = true;
        submitButton.textContent = "Recommending...";
      }
      const itemId = requireLocalQueueLifecycleItemId();
      setMessage("queue-lifecycle-message", `Recommending routing metadata for ${itemId}...`, "loading");
      const payload = await fetchJson(`/api/local-queue/items/${encodeURIComponent(itemId)}/routing-recommendation`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildRoutingRecommendationPayload({ parseLineList })),
      });
      renderRoutingRecommendationResult(payload);
      setMessage("queue-lifecycle-message", `Routing recommendation loaded for ${itemId}. No execution performed.`, "success");
    } catch (error) {
      renderRoutingRecommendationResult((error && error.payload) || null);
      setMessage("queue-lifecycle-message", String(error.message || error), "error");
    } finally {
      if (submitButton) {
        submitButton.disabled = false;
        submitButton.textContent = originalLabel;
      }
    }
  });

  on("queue-lifecycle-routing-apply", "click", async () => {
    try {
      const itemId = requireLocalQueueLifecycleItemId();
      setMessage("queue-lifecycle-message", `Applying routing metadata for ${itemId}...`, "loading");
      const payload = await fetchJson(`/api/local-queue/items/${encodeURIComponent(itemId)}/apply-routing-recommendation`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildRoutingRecommendationPayload({ parseLineList })),
      });
      renderRoutingRecommendationResult(payload);
      await loadQueueData();
      await refreshSummaryAndReport();
      setMessage("queue-lifecycle-message", `Routing metadata applied for ${itemId}. No execution performed.`, "success");
    } catch (error) {
      renderRoutingRecommendationResult((error && error.payload) || null);
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

  on("queue-codex-high-value-form", "submit", async (event) => {
    event.preventDefault();
    const submitButton = byId("queue-codex-high-value-submit");
    const originalLabel = submitButton ? submitButton.textContent : "";
    try {
      if (submitButton) {
        submitButton.disabled = true;
        submitButton.textContent = "Generating...";
      }
      const itemId = requireLocalQueueLifecycleItemId();
      setMessage("queue-lifecycle-message", `Generating Codex high-value lane prompt for ${itemId}...`, "loading");
      const payload = await fetchJson(`/api/local-queue/items/${encodeURIComponent(itemId)}/codex-high-value-prompt`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildCodexHighValuePromptPayload()),
      });
      renderCodexHighValuePromptResult(payload);
      setMessage("queue-lifecycle-message", `Codex high-value prompt generated for ${itemId}. Copy/paste manually only.`, "success");
    } catch (error) {
      renderCodexHighValuePromptResult((error && error.payload) || null);
      setMessage("queue-lifecycle-message", String(error.message || error), "error");
    } finally {
      if (submitButton) {
        submitButton.disabled = false;
        submitButton.textContent = originalLabel;
      }
    }
  });

  on("queue-local-llm-preview-form", "submit", async (event) => {
    event.preventDefault();
    const submitButton = byId("queue-local-llm-preview-submit");
    const originalLabel = submitButton ? submitButton.textContent : "";
    try {
      if (submitButton) {
        submitButton.disabled = true;
        submitButton.textContent = "Generating...";
      }
      const itemId = requireLocalQueueLifecycleItemId();
      setMessage("queue-lifecycle-message", `Generating local LLM prompt preview for ${itemId}...`, "loading");
      const payload = await fetchJson(`/api/local-queue/items/${encodeURIComponent(itemId)}/local-llm-prompt-preview`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildLocalLlmPromptPreviewPayload()),
      });
      renderLocalLlmPromptPreviewResult(payload);
      setMessage("queue-lifecycle-message", `Local LLM prompt preview generated for ${itemId}. No execution performed.`, "success");
    } catch (error) {
      renderLocalLlmPromptPreviewResult((error && error.payload) || null);
      setMessage("queue-lifecycle-message", String(error.message || error), "error");
    } finally {
      if (submitButton) {
        submitButton.disabled = false;
        submitButton.textContent = originalLabel;
      }
    }
  });

  on("queue-local-llm-execute-form", "submit", async (event) => {
    event.preventDefault();
    const submitButton = byId("queue-local-llm-execute-submit");
    const originalLabel = submitButton ? submitButton.textContent : "";
    try {
      if (submitButton) {
        submitButton.disabled = true;
        submitButton.textContent = "Running...";
      }
      const itemId = requireLocalQueueLifecycleItemId();
      setMessage("queue-lifecycle-message", `Running operator-gated local LLM prototype for ${itemId}...`, "loading");
      const payload = await fetchJson(`/api/local-queue/items/${encodeURIComponent(itemId)}/local-llm-execute`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildLocalLlmExecutePayload()),
      });
      renderLocalLlmExecuteResult(payload);
      setMessage("queue-lifecycle-message", `Local LLM prototype result captured for ${itemId}. Advisory output only.`, "success");
    } catch (error) {
      renderLocalLlmExecuteResult((error && error.payload) || null);
      setMessage("queue-lifecycle-message", String(error.message || error), "error");
    } finally {
      if (submitButton) {
        submitButton.disabled = false;
        submitButton.textContent = originalLabel;
      }
    }
  });

  on("queue-prompt-pack-form", "submit", async (event) => {
    event.preventDefault();
    const submitButton = byId("queue-prompt-pack-submit");
    const originalLabel = submitButton ? submitButton.textContent : "";
    try {
      if (submitButton) {
        submitButton.disabled = true;
        submitButton.textContent = "Generating...";
      }
      setMessage("queue-lifecycle-message", "Generating local prompt pack...", "loading");
      const payload = await fetchJson("/api/local-queue/prompt-pack", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildLocalQueuePromptPackPayload({ parseCommaList })),
      });
      renderLocalQueuePromptPackResult(payload);
      setMessage("queue-lifecycle-message", "Local prompt pack generated. Copy/paste manually.", "success");
    } catch (error) {
      renderLocalQueuePromptPackResult((error && error.payload) || null);
      setMessage("queue-lifecycle-message", String(error.message || error), "error");
    } finally {
      if (submitButton) {
        submitButton.disabled = false;
        submitButton.textContent = originalLabel;
      }
    }
  });

  on("queue-execution-audit-form", "submit", async (event) => {
    event.preventDefault();
    const submitButton = byId("queue-execution-audit-submit");
    const originalLabel = submitButton ? submitButton.textContent : "";
    try {
      if (submitButton) {
        submitButton.disabled = true;
        submitButton.textContent = "Loading...";
      }
      setMessage("queue-lifecycle-message", "Loading execution audit log...", "loading");
      const payload = await fetchJson(`/api/execution-audit-log${buildExecutionAuditQuery()}`, { method: "GET" });
      renderExecutionAuditLog(payload);
      setMessage("queue-lifecycle-message", "Execution audit log loaded. No execution performed.", "success");
    } catch (error) {
      renderExecutionAuditLog((error && error.payload) || null);
      setMessage("queue-lifecycle-message", String(error.message || error), "error");
    } finally {
      if (submitButton) {
        submitButton.disabled = false;
        submitButton.textContent = originalLabel;
      }
    }
  });

  on("queue-ai-artifacts-form", "submit", async (event) => {
    event.preventDefault();
    const submitButton = byId("queue-ai-artifacts-submit");
    const originalLabel = submitButton ? submitButton.textContent : "";
    try {
      if (submitButton) {
        submitButton.disabled = true;
        submitButton.textContent = "Loading...";
      }
      setMessage("queue-lifecycle-message", "Loading AI artifact registry...", "loading");
      const payload = await fetchJson(`/api/ai-artifacts${buildAiArtifactsQuery()}`, { method: "GET" });
      renderAiArtifactRegistry(payload);
      setMessage("queue-lifecycle-message", "AI artifact registry loaded. No execution performed.", "success");
    } catch (error) {
      renderAiArtifactRegistry((error && error.payload) || null);
      setMessage("queue-lifecycle-message", String(error.message || error), "error");
    } finally {
      if (submitButton) {
        submitButton.disabled = false;
        submitButton.textContent = originalLabel;
      }
    }
  });

  on("queue-operator-run-history-form", "submit", async (event) => {
    event.preventDefault();
    const submitButton = byId("queue-operator-run-history-submit");
    const originalLabel = submitButton ? submitButton.textContent : "";
    try {
      if (submitButton) {
        submitButton.disabled = true;
        submitButton.textContent = "Loading...";
      }
      setMessage("queue-lifecycle-message", "Loading operator run history...", "loading");
      const payload = await fetchJson(`/api/operator-run-history${buildOperatorRunHistoryQuery()}`, { method: "GET" });
      renderOperatorRunHistory(payload);
      setMessage("queue-lifecycle-message", "Operator run history loaded. No execution performed.", "success");
    } catch (error) {
      renderOperatorRunHistory((error && error.payload) || null);
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

  on("queue-lifecycle-evidence-form", "submit", async (event) => {
    event.preventDefault();
    const submitButton = byId("queue-lifecycle-evidence-submit");
    const originalLabel = submitButton ? submitButton.textContent : "";
    try {
      if (submitButton) {
        submitButton.disabled = true;
        submitButton.textContent = "Capturing...";
      }
      const itemId = requireLocalQueueLifecycleItemId();
      setMessage("queue-lifecycle-message", `Capturing local evidence for ${itemId}...`, "loading");
      const payload = await fetchJson(`/api/local-queue/items/${encodeURIComponent(itemId)}/evidence`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildLocalQueueEvidencePayload({ parseLineList })),
      });
      renderLocalQueueEvidenceResult(payload);
      await loadQueueData();
      await refreshSummaryAndReport();
      setMessage("queue-lifecycle-message", `Captured local evidence for ${itemId}.`, "success");
    } catch (error) {
      renderLocalQueueEvidenceResult((error && error.payload) || null);
      setMessage("queue-lifecycle-message", String(error.message || error), "error");
    } finally {
      if (submitButton) {
        submitButton.disabled = false;
        submitButton.textContent = originalLabel;
      }
    }
  });

  on("queue-lifecycle-closeout-form", "submit", async (event) => {
    event.preventDefault();
    const submitButton = byId("queue-lifecycle-closeout-submit");
    const originalLabel = submitButton ? submitButton.textContent : "";
    try {
      if (submitButton) {
        submitButton.disabled = true;
        submitButton.textContent = "Closing...";
      }
      const itemId = requireLocalQueueLifecycleItemId();
      setMessage("queue-lifecycle-message", `Closing out ${itemId} locally...`, "loading");
      const payload = await fetchJson(`/api/local-queue/items/${encodeURIComponent(itemId)}/closeout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildLocalQueueCloseoutPayload()),
      });
      renderLocalQueueCloseoutResult(payload);
      await loadQueueData();
      await refreshSummaryAndReport();
      setMessage("queue-lifecycle-message", `Closed out ${itemId}.`, "success");
    } catch (error) {
      renderLocalQueueCloseoutResult((error && error.payload) || null);
      setMessage("queue-lifecycle-message", String(error.message || error), "error");
    } finally {
      if (submitButton) {
        submitButton.disabled = false;
        submitButton.textContent = originalLabel;
      }
    }
  });
}
