import { byId, on, setList, setMessage, setText } from "/js/core/dom.js";
import { fetchJson, toQuery } from "/js/core/http.js";

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