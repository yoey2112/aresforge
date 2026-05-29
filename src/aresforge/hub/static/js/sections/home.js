import { byId, on, setList, setMessage, setText } from "/js/core/dom.js";
import { fetchJson } from "/js/core/http.js";

export function bindHomeQuickNavActions({ activateSection }) {
  on("home-nav-workspace", "click", () => {
    activateSection("workspace");
  });
  on("home-nav-projects", "click", () => {
    activateSection("projects");
  });
  on("home-nav-queue", "click", () => {
    activateSection("queue");
  });
  on("home-nav-reports", "click", () => {
    activateSection("reports");
  });
  on("home-local-open-project-context", "click", () => {
    const label = String((byId("home-local-open-project-context") && byId("home-local-open-project-context").textContent) || "").toLowerCase();
    activateSection(label.includes("workspace") ? "workspace" : "projects");
  });
  on("home-local-open-queue", "click", () => {
    activateSection("queue");
  });
  on("home-local-open-repos", "click", () => {
    activateSection("repos");
  });
  on("home-local-open-lanes", "click", () => {
    activateSection("queue");
  });
  on("home-local-open-reports", "click", () => {
    activateSection("reports");
  });
}

export function bindHomeActions({
  refreshSummaryAndReport,
  loadExecutionReadiness,
  activeProjectId,
  activateSection,
  activateQueueIntakeFocus,
  focusNewProjectWizard,
}) {
  on("home-refresh-summary", "click", async () => {
    try {
      await refreshSummaryAndReport();
      await loadExecutionReadiness(activeProjectId());
      setMessage("reports-message", "Summary refreshed.", "success");
    } catch (error) {
      setMessage("reports-message", String(error.message || error), "error");
    }
  });

  on("home-open-bootstrap", "click", () => {
    activateSection("bootstrap");
  });

  on("home-quick-intake", "click", () => {
    activateQueueIntakeFocus();
  });

  on("home-start-new-project", "click", () => {
    focusNewProjectWizard();
  });
}

export function renderLocalHomeDashboard(dashboard) {
  const projectSummary = (dashboard && dashboard.project_summary) || {};
  const queueSummary = (dashboard && dashboard.queue_summary) || {};
  const laneSummary = (dashboard && dashboard.agent_lane_summary) || {};
  const repoSummary = (dashboard && dashboard.repo_summary) || {};
  const blockers = Array.isArray((dashboard && dashboard.blockers)) ? dashboard.blockers : [];
  const warnings = Array.isArray((dashboard && dashboard.warnings)) ? dashboard.warnings : [];
  const queueStatuses = queueSummary.counts_by_status || {};
  const laneDetails = Array.isArray(laneSummary.lanes) ? laneSummary.lanes : [];
  const repoWarnings = Array.isArray(repoSummary.warnings) ? repoSummary.warnings : [];

  const queueLines = Object.keys(queueStatuses)
    .sort()
    .map((key) => `${key}: ${queueStatuses[key]}`);
  const laneLines = laneDetails.map((lane) => `${lane.lane_id || "unknown"}: ${lane.item_count || 0}`);

  const activeProjectId = String(projectSummary.active_project_id || "").trim();
  const activeProjectName = String(projectSummary.active_project_name || "").trim();
  const activeProjectLabel = activeProjectId ? (activeProjectName || activeProjectId) : "No active project selected";
  const projectContextButton = byId("home-local-open-project-context");
  if (projectContextButton) {
    projectContextButton.textContent = activeProjectId ? "Open workspace" : "View projects";
  }

  setText("home-local-total-projects", String(projectSummary.total_projects || 0));
  setText("home-local-active-project", activeProjectLabel);
  setText("home-local-active-project-id", `project_id: ${activeProjectId || "-"}`);
  setText("home-local-active-project-status", projectSummary.active_project_status || "unknown");
  setText("home-local-queue-count", String(queueSummary.total_items || 0));
  setList("home-local-queue-status-summary", "home-local-queue-status-summary-empty", queueLines);
  setText("home-local-agent-lane-count", String(laneSummary.total_lanes || 0));
  setList("home-local-agent-lane-details", "home-local-agent-lane-details-empty", laneLines);
  setText("home-local-repo-availability", repoSummary.available ? "available" : "unavailable");
  setText("home-local-repo-status", repoSummary.status || "unknown");
  setList("home-local-repo-warnings", "home-local-repo-warnings-empty", repoWarnings);
  setList("home-local-blockers", "home-local-blockers-empty", blockers);
  setList("home-local-warnings", "home-local-warnings-empty", warnings);
  setText(
    "home-local-recommended-next-action",
    dashboard.next_safe_action || "No safe next action recommendation available yet.",
  );
  setText("home-local-dashboard-message", "Read-only local dashboard snapshot loaded from /api/dashboard/summary.");
}

export function renderLocalHomeDashboardUnavailable() {
  setText("home-local-dashboard-message", "Local home dashboard data is unavailable.");
  setText("home-local-recommended-next-action", "Use Refresh Summary to retry /api/dashboard/summary.");
  setText("home-local-total-projects", "0");
  setText("home-local-active-project", "No active project selected");
  setText("home-local-active-project-id", "project_id: -");
  setText("home-local-active-project-status", "unknown");
  setText("home-local-queue-count", "0");
  setText("home-local-agent-lane-count", "0");
  setText("home-local-repo-availability", "unavailable");
  setText("home-local-repo-status", "unknown");
  const projectContextButton = byId("home-local-open-project-context");
  if (projectContextButton) {
    projectContextButton.textContent = "View projects";
  }
  setList("home-local-queue-status-summary", "home-local-queue-status-summary-empty", []);
  setList("home-local-agent-lane-details", "home-local-agent-lane-details-empty", []);
  setList("home-local-repo-warnings", "home-local-repo-warnings-empty", []);
  setList("home-local-blockers", "home-local-blockers-empty", []);
  setList("home-local-warnings", "home-local-warnings-empty", []);
  setList(
    "home-local-warnings",
    "home-local-warnings-empty",
    ["Dashboard summary endpoint unavailable."],
  );
}

export async function loadLocalHomeDashboard() {
  setText("home-local-dashboard-message", "Loading local read-only dashboard summary...");
  const dashboard = await fetchJson("/api/dashboard/summary", { method: "GET" });
  renderLocalHomeDashboard(dashboard);
}

export function renderActiveProjectSummary(state, payload) {
  state.activeProject = payload || null;
  const selected = Boolean(payload && payload.active_project_selected);
  const project = (payload && payload.active_project) || {};
  const repo = (payload && payload.active_repo) || {};
  const projectId = String((payload && payload.active_project_id) || "").trim();
  const repoId = String((payload && payload.active_repo_id) || "").trim();
  const projectName = project.name || projectId || "None selected";

  setText("home-active-project-name", selected ? projectName : "None selected");
  const badge = byId("home-active-project-badge");
  if (badge) {
    badge.textContent = selected ? "active" : "not selected";
    badge.className = selected ? "status-pill status-pill-ready" : "status-pill status-pill-needs_attention";
  }
  setText(
    "home-active-project-detail",
    selected
      ? `${projectId} | status=${project.status || "-"} | github=${project.github_connection_status || "unlinked"}`
      : "Select an active project from Projects.",
  );
  setText("home-active-repo-id", repoId || "-");
  setText(
    "home-active-repo-detail",
    repoId ? `${repo.name || repoId} | role=${repo.role || "-"} | status=${repo.status || "-"}` : "Used as the Queue default when available.",
  );
  setText(
    "projects-active-project-summary",
    selected ? `Active project: ${projectId} (${project.name || projectId}) | default repo: ${repoId || "-"}` : "No active project selected.",
  );
  setText(
    "queue-active-project-summary",
    selected
      ? `Queue defaults will use project=${projectId} and repo=${repoId || "(manual repo required)"}.`
      : "No active project selected. Queue filters and new items remain manual.",
  );
  setText(
    "intake-active-project-summary",
    selected
      ? `Creating local queue items for ${projectName} (${projectId})${repoId ? ` | repo=${repoId}` : " | repo resolved from project defaults when available"}.`
      : "Select an active project to create a local queue item.",
  );
}

export function renderActiveProjectWorkbench(report) {
  const activeProjectSummary = (report && report.active_project_summary) || {};
  const readiness = (report && report.readiness_indicators) || {};
  const actionCenter = (report && report.action_center) || {};
  const project = activeProjectSummary.active_project || {};
  const repo = activeProjectSummary.active_repo || {};
  const selected = Boolean(activeProjectSummary.active_project_selected || report.active_project_selected);
  const activeProjectIdValue = activeProjectSummary.active_project_id || report.active_project_id || "";
  const activeRepoIdValue = activeProjectSummary.active_repo_id || report.active_repo_id || "";

  const queueTotal = Number(activeProjectSummary.active_project_queue_item_count || 0);
  const readyCount = Number(activeProjectSummary.active_project_ready_item_count || 0);
  const blockedCount = Number(activeProjectSummary.active_project_blocked_item_count || 0);
  const inProgressCount = Number(activeProjectSummary.active_project_in_progress_item_count || 0);
  const highCount = Number(activeProjectSummary.active_project_high_priority_item_count || 0);
  const urgentCount = Number(activeProjectSummary.active_project_urgent_item_count || 0);
  const unassignedCount = Number(activeProjectSummary.active_project_unassigned_item_count || 0);
  const highUrgentCount = highCount + urgentCount;
  const githubSyncStatus = activeProjectSummary.github_sync_status || "planned_gated_not_executed";

  setText("home-workbench-project", selected ? `${activeProjectIdValue} | ${(project.name || activeProjectIdValue || "-")}` : "No active project selected");
  setText("home-workbench-project-detail", selected ? `status=${project.status || "-"}` : "Select an active project from Projects.");
  setText("home-workbench-repo", activeRepoIdValue ? `${activeRepoIdValue} | ${(repo.name || activeRepoIdValue)}` : "-");
  setText("home-workbench-repo-detail", activeRepoIdValue ? `status=${repo.status || "-"}` : "No active repo selected.");
  setText("home-workbench-current-work", `queue=${queueTotal} | ready=${readyCount} | blocked=${blockedCount}`);
  setText("home-workbench-current-work-detail", `in_progress=${inProgressCount} | high/urgent=${highUrgentCount} | unassigned=${unassignedCount}`);
  setText("home-workbench-attention", `blocked=${blockedCount} | high/urgent=${highUrgentCount}`);
  setText("home-workbench-attention-detail", `GitHub sync status: ${githubSyncStatus}`);

  const currentWorkItems = ((report && report.active_project_current_items) || []).map((item) => {
    const title = item.title || "(no title)";
    return `${item.item_id || "-"} | ${title} | status=${item.status || "-"} | priority=${item.priority || "-"} | agent=${item.assigned_agent || "-"}`;
  });
  setList("home-current-active-work", "home-current-active-work-empty", selected ? currentWorkItems : ["No active project selected"]);

  const workbenchActions = [];
  ((report && report.recommended_next_actions) || []).forEach((action) => workbenchActions.push(String(action)));
  if (activeProjectIdValue) {
    workbenchActions.push(`active_project_ready_items: ${readyCount}`);
    workbenchActions.push(`active_project_blocked_items: ${blockedCount}`);
  }
  if (Array.isArray(actionCenter.active_project_ready_items) && actionCenter.active_project_ready_items.length > 0) {
    workbenchActions.push(`action_center_ready_items: ${actionCenter.active_project_ready_items.join(", ")}`);
  }
  if (Array.isArray(actionCenter.active_project_blocked_items) && actionCenter.active_project_blocked_items.length > 0) {
    workbenchActions.push(`action_center_blocked_items: ${actionCenter.active_project_blocked_items.map((item) => item.item_id || "-").join(", ")}`);
  }
  if (readiness.active_project_selected === false) {
    workbenchActions.push("Select an active project from Projects.");
  }
  if (Array.isArray(actionCenter.bootstrap_recommended_actions)) {
    actionCenter.bootstrap_recommended_actions.forEach((action) => workbenchActions.push(`bootstrap: ${action}`));
  }
  const dedupedActions = workbenchActions.filter((value, index, all) => value && all.indexOf(value) === index);
  setList("home-workbench-actions", "home-workbench-actions-empty", dedupedActions);
}

export function activateQueueIntakeFocus(activateSection) {
  activateSection("queue");
  const intakeTitle = byId("intake-title");
  if (intakeTitle) {
    intakeTitle.focus();
  }
}

export function focusNewProjectWizard(activateSection) {
  activateSection("projects");
  const firstField = byId("wizard-project-name");
  if (firstField) {
    firstField.focus();
  }
}

export function renderActiveProjectIntakeResult(state, setLocalQueueLifecycleItemId, payload) {
  const activeProjectSummary = state.activeProject || {};
  const projectId = String((payload && payload.project_id) || activeProjectSummary.active_project_id || "").trim() || "-";
  const projectName = String((activeProjectSummary.active_project && activeProjectSummary.active_project.name) || projectId || "").trim() || "-";
  const repoId = String((payload && payload.repo_id) || activeProjectSummary.active_repo_id || "").trim() || "-";

  setList("intake-result", "intake-result-empty", [
    `item_id: ${payload && payload.item_id ? payload.item_id : "-"}`,
    `status: ${payload && payload.status ? payload.status : "-"}`,
    `active_project: ${projectId} | ${projectName}`,
    `repo_id: ${repoId}`,
    `next_safe_action: ${payload && payload.next_safe_action ? payload.next_safe_action : "-"}`,
  ].concat((payload && payload.warnings ? payload.warnings : []).map((warning) => `warning: ${warning}`)));

  if (payload && payload.item_id) {
    setLocalQueueLifecycleItemId(payload.item_id);
  }
}

export function buildIntakePayload({ activeProjectId, activeRepoId, parseCommaList }) {
  const intakeType = byId("intake-type").value.trim() || "task";
  const itemType = intakeType === "direction" || intakeType === "ui" || intakeType === "refactor"
    ? "task"
    : intakeType === "docs"
      ? "documentation"
      : intakeType;
  const tags = parseCommaList(byId("intake-tags").value);
  if (intakeType === "direction" && tags.indexOf("direction") === -1) {
    tags.push("direction");
  }
  if (intakeType === "ui" && tags.indexOf("ui") === -1) {
    tags.push("ui");
  }
  if (intakeType === "refactor" && tags.indexOf("refactor") === -1) {
    tags.push("refactor");
  }
  if (intakeType === "docs" && tags.indexOf("docs") === -1) {
    tags.push("docs");
  }
  if (tags.indexOf("active-project-intake") === -1) {
    tags.push("active-project-intake");
  }

  return prunePayload({
    project_id: activeProjectId(),
    repo_id: activeRepoId(),
    title: byId("intake-title").value.trim(),
    description: byId("intake-description").value.trim(),
    priority: byId("intake-priority").value.trim() || "normal",
    item_type: itemType,
    tags,
  });
}
