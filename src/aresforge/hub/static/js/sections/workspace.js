import { byId, on, setList, setMessage, setText } from "/js/core/dom.js";
import { fetchJson } from "/js/core/http.js";

export function renderWorkspace(state, payload) {
  state.workspace = payload || null;
  const summary = (payload && payload.active_project_summary) || {};
  const project = summary.active_project || {};
  const repo = summary.active_repo || {};
  const reportStatus = (payload && payload.report_status) || {};
  const repoStatus = (payload && payload.repo_status) || {};
  const selected = Boolean(payload && payload.active_project_selected);
  const projectId = String((payload && payload.active_project_id) || "").trim();
  const activeRepoId = String((payload && payload.active_repo_id) || "").trim();

  setText("workspace-project-name", selected ? (project.name || projectId || "None selected") : "None selected");
  const badge = byId("workspace-project-badge");
  if (badge) {
    badge.textContent = selected ? "active" : "not selected";
    badge.className = selected ? "status-pill status-pill-ready" : "status-pill status-pill-needs_attention";
  }
  setText(
    "workspace-project-detail",
    selected
      ? `${projectId} | status=${project.status || "-"} | repo=${activeRepoId || "-"}`
      : "Select an active project from Projects.",
  );
  setText("workspace-report-status", reportStatus.overall_status || "needs_attention");
  setText("workspace-report-detail", reportStatus.message || "No report data available yet.");

  const repoHeadline = activeRepoId || repoStatus.repo_id || repo.repo_id || "No active repo";
  setText("workspace-repo-status", repoHeadline);
  setText(
    "workspace-repo-detail",
    repoStatus.available
      ? `status=${repoStatus.status || repo.status || "-"} | branch=${repoStatus.local_git_branch || "-"} | ${repoStatus.local_git_status_summary || repoStatus.message || "Local repo facts available."}`
      : (repoStatus.message || "No local repo facts available yet."),
  );
  const nextSafe = (payload && payload.next_safe_action) || "Select an active project to continue.";
  setText("workspace-next-safe-action", `Local-only: ${nextSafe}`);
  setList(
    "workspace-current-items",
    "workspace-current-items-empty",
    ((payload && payload.current_queue_items) || []).map((item) => {
      return `${item.item_id || "-"} | ${item.title || "(no title)"} | status=${item.status || "-"} | priority=${item.priority || "-"} | repo=${item.repo_id || "-"} | agent=${item.assigned_agent || "unassigned"}`;
    }),
  );
  setList(
    "workspace-completed-items",
    "workspace-completed-items-empty",
    ((payload && payload.recent_completed_queue_items) || []).map((item) => {
      return `${item.item_id || "-"} | ${item.title || "(no title)"} | status=${item.status || "done"} | updated=${item.updated_at || "-"}`;
    }),
  );
  setList("workspace-warnings", "workspace-warnings-empty", (payload && payload.warnings) || []);
  setMessage(
    "workspace-message",
    selected
      ? "Active project workspace loaded. Local-only view; operator actions required for changes."
      : "No active project selected. Use Projects to choose one before continuing task intake or queue lifecycle.",
    selected ? "success" : "warn",
  );
}

export function renderWorkspaceUnavailable() {
  setText("workspace-project-name", "Unavailable");
  setText("workspace-project-detail", "Workspace endpoint unavailable.");
  setText("workspace-report-status", "needs_attention");
  setText("workspace-report-detail", "Workspace report data unavailable.");
  setText("workspace-repo-status", "Unavailable");
  setText("workspace-repo-detail", "Workspace repo facts unavailable.");
  setText("workspace-next-safe-action", "Refresh Workspace to retry.");
  setList("workspace-current-items", "workspace-current-items-empty", []);
  setList("workspace-completed-items", "workspace-completed-items-empty", []);
  setList("workspace-warnings", "workspace-warnings-empty", ["Active project workspace endpoint unavailable."]);
  setMessage("workspace-message", "Workspace data is unavailable.", "warn");
}

export function bindWorkspaceActions({
  refreshSummaryAndReport,
  loadWorkspaceData,
  activateQueueIntakeFocus,
  activateSection,
}) {
  on("workspace-refresh", "click", async () => {
    setMessage("workspace-message", "Refreshing workspace (local-only)...", "loading");
    try {
      await refreshSummaryAndReport();
      await loadWorkspaceData();
      setMessage("workspace-message", "Workspace refreshed. Local-only view.", "success");
    } catch (error) {
      setMessage("workspace-message", String(error.message || error), "error");
    }
  });

  on("workspace-continue-intake", "click", () => {
    activateQueueIntakeFocus();
    setMessage("workspace-message", "Navigate to Queue/Intake (local-only).", "success");
  });

  on("workspace-open-queue", "click", () => {
    activateSection("queue");
    setMessage("workspace-message", "Open Queue Lifecycle (local-only).", "success");
  });

  on("workspace-select-project", "click", () => {
    activateSection("projects");
    setMessage("workspace-message", "Select an active project. No automation will run automatically.", "success");
    const selector = byId("active-project-select");
    if (selector) {
      selector.focus();
    }
  });
}

export async function loadWorkspace(state) {
  const payload = await fetchJson("/api/active-project/workspace", { method: "GET" });
  renderWorkspace(state, payload);
  return payload;
}