import { on, setList, setMessage, setText } from "/js/core/dom.js";
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

export function renderLocalHomeDashboard(dashboard, report) {
  const projectSummary = (dashboard && dashboard.project_summary) || {};
  const queueSummary = (dashboard && dashboard.queue_summary) || {};
  const docsSummary = (dashboard && dashboard.docs_summary) || {};
  const activeProject = (dashboard && dashboard.active_project) || {};
  const readinessSummary = (report && report.project_health) || {};
  const warnings = Array.isArray((dashboard && dashboard.warnings)) ? dashboard.warnings : [];
  const blockers = Array.isArray((report && report.blockers)) ? report.blockers : [];
  const recommended =
    (report && report.recommended_next_action) ||
    (dashboard && dashboard.recommended_next_action) ||
    "No recommendation available yet.";
  const overallStatus =
    readinessSummary.overall_status ||
    ((dashboard && dashboard.validation_summary) || {}).overall_status ||
    "needs_attention";
  const queueStatuses = queueSummary.counts_by_status || {};
  const queueLines = Object.keys(queueStatuses)
    .sort()
    .map((key) => `${key}: ${queueStatuses[key]}`);

  setText("home-local-total-projects", String(projectSummary.project_count || dashboard.total_projects || 0));
  setText("home-local-active-project", activeProject.name || "None selected");
  setText("home-local-active-project-id", `project_id: ${dashboard.active_project_id || "-"}`);
  setText("home-local-active-repo", dashboard.active_repo_id || "-");
  setText("home-local-overall-readiness", overallStatus);
  setText("home-local-queue-count", String(queueSummary.item_count || 0));
  setText("home-local-docs-readiness", docsSummary.docs_ready ? "ready" : "needs docs");
  setList("home-local-queue-status-summary", "home-local-queue-status-summary-empty", queueLines);
  setText("home-local-recommended-next-action", recommended);
  setList(
    "home-local-warnings-blockers",
    "home-local-warnings-blockers-empty",
    blockers.concat(warnings).slice(0, 12),
  );
  setText("home-local-dashboard-message", "Read-only local dashboard/report snapshot loaded.");
}

export function renderLocalHomeDashboardUnavailable() {
  setText("home-local-dashboard-message", "Local home dashboard data is unavailable.");
  setText("home-local-recommended-next-action", "Refresh Summary to retry local dashboard loading.");
  setList("home-local-queue-status-summary", "home-local-queue-status-summary-empty", []);
  setList(
    "home-local-warnings-blockers",
    "home-local-warnings-blockers-empty",
    ["Local dashboard/report endpoint unavailable."],
  );
}

export async function loadLocalHomeDashboard() {
  const dashboard = await fetchJson("/api/local-project-dashboard", { method: "GET" });
  const report = await fetchJson("/api/local-project-report", { method: "GET" });
  renderLocalHomeDashboard(dashboard, report);
}