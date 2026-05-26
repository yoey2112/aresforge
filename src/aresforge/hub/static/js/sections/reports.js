import { byId, on, setCodeBlock, setList, setMessage, setText } from "/js/core/dom.js";
import { fetchJson, toQuery } from "/js/core/http.js";

export function renderReportSummary(state, report, deps) {
  const {
    countLines,
    queueEntries,
    statusBadgeText,
    renderActiveProjectSummary,
    renderActiveProjectWorkbench,
    renderWorkflowCards,
    renderBootstrapStatus,
  } = deps;
  const activeProjectSummary = report.active_project_summary || {};
  const projectSummary = report.project_summary || {};
  const repoSummary = report.repo_summary || {};
  const queueSummary = report.queue_summary || {};
  const agentSummary = report.agent_summary || {};
  const orchestrationSummary = report.orchestration_summary || {};
  const escalationSummary = report.escalation_summary || {};
  const docsSummary = report.docs_summary || {};
  const githubSummary = report.github_summary || {};
  const readiness = report.readiness_indicators || {};
  const actionCenter = report.action_center || {};

  byId("project-count").textContent = String(projectSummary.project_count || 0);
  byId("repo-count").textContent = String(repoSummary.repo_count || 0);
  byId("queue-total").textContent = String(queueSummary.item_count || 0);
  byId("agent-count").textContent = String(agentSummary.agent_count || 0);
  byId("home-orchestration-count").textContent = String(orchestrationSummary.assigned_count || 0);
  byId("home-escalation-count").textContent = String((escalationSummary.cloud_llm_recommended_count || 0) + (escalationSummary.human_required_count || 0));
  byId("home-docs-status").textContent = docsSummary.docs_ready ? "ready" : "needs docs";
  byId("home-overall-status").textContent = statusBadgeText(readiness);
  byId("github-linked-project-count").textContent = String(githubSummary.linked_project_count || 0);
  byId("github-linked-repo-count").textContent = String(githubSummary.linked_repo_count || 0);
  byId("github-unlinked-project-count").textContent = String(githubSummary.unlinked_project_count || 0);
  byId("github-unlinked-repo-count").textContent = String(githubSummary.unlinked_repo_count || 0);

  renderActiveProjectSummary({
    active_project_selected: Boolean(activeProjectSummary.active_project_selected || report.active_project_selected),
    active_project_id: activeProjectSummary.active_project_id || report.active_project_id || "",
    active_project: activeProjectSummary.active_project || null,
    active_repo_id: activeProjectSummary.active_repo_id || report.active_repo_id || "",
    active_repo: activeProjectSummary.active_repo || null,
  });
  byId("home-active-project-queue-total").textContent = String(activeProjectSummary.active_project_queue_item_count || 0);
  byId("home-active-project-queue-detail").textContent = `ready=${activeProjectSummary.active_project_ready_item_count || 0} | blocked=${activeProjectSummary.active_project_blocked_item_count || 0}`;
  renderActiveProjectWorkbench(report);

  setList("queue-status-list", "queue-empty-state", queueEntries(queueSummary.counts_by_status));
  setList("warnings-list", "warnings-empty-state", report.warnings || []);
  setList("actions-list", "actions-empty-state", report.recommended_next_actions || []);
  setList(
    "readiness-list",
    "readiness-empty-state",
    (report.project_management_readiness || []).concat((report.plan_only_boundary_hints || []).map((hint) => `Boundary: ${hint}`)),
  );
  setList("home-readiness-indicators", "home-readiness-indicators-empty", Object.keys(readiness).map((key) => `${key}: ${readiness[key]}`));
  setList("home-action-center", "home-action-center-empty", [
    `blocked_work_items: ${(actionCenter.blocked_work_items || []).length}`,
    `urgent_or_high_priority_items: ${(actionCenter.urgent_or_high_priority_items || []).length}`,
    `unassigned_queue_items: ${(actionCenter.unassigned_queue_items || []).length}`,
    `cloud_escalation_candidates: ${actionCenter.cloud_escalation_candidates || 0}`,
    `human_required_items: ${actionCenter.human_required_items || 0}`,
    `missing_docs: ${(actionCenter.missing_docs || []).length}`,
    `projects_missing_github_link: ${(actionCenter.projects_missing_github_link || []).length}`,
    `projects_missing_primary_repo: ${(actionCenter.projects_missing_primary_repo || []).length}`,
    `repos_missing_github_identity: ${(actionCenter.repos_missing_github_identity || []).length}`,
    `missing_local_state_files: ${(actionCenter.missing_local_state_files || []).length}`,
  ]);
  renderWorkflowCards("home-workflow-cards", "home-workflow-cards-empty", (report.operator_workflows || []).slice(0, 6));
  if (state.bootstrapStatus) {
    renderBootstrapStatus(state.bootstrapStatus);
  }

  setList("reports-active-project-summary", "reports-active-project-summary-empty", [
    `active_project_selected: ${Boolean(activeProjectSummary.active_project_selected || report.active_project_selected)}`,
    `active_project_id: ${activeProjectSummary.active_project_id || report.active_project_id || "-"}`,
    `active_repo_id: ${activeProjectSummary.active_repo_id || report.active_repo_id || "-"}`,
    `queue_items: ${activeProjectSummary.active_project_queue_item_count || 0}`,
    `ready_items: ${activeProjectSummary.active_project_ready_item_count || 0}`,
    `blocked_items: ${activeProjectSummary.active_project_blocked_item_count || 0}`,
    `github_sync_status: ${activeProjectSummary.github_sync_status || "planned_gated_not_executed"}`,
  ]);

  setList("reports-project-repo-summary", "reports-project-repo-summary-empty", [
    `project_count: ${projectSummary.project_count || 0}`,
    ...countLines("project_status", projectSummary.counts_by_status),
    `repo_count: ${repoSummary.repo_count || 0}`,
    ...countLines("repo_status", repoSummary.counts_by_status),
    ...countLines("repo_role", repoSummary.counts_by_role),
  ]);
  setList("reports-github-linkage", "reports-github-linkage-empty", [
    `linked_projects: ${githubSummary.linked_project_count || 0}`,
    `linked_repos: ${githubSummary.linked_repo_count || 0}`,
    `unlinked_projects: ${githubSummary.unlinked_project_count || 0}`,
    `unlinked_repos: ${githubSummary.unlinked_repo_count || 0}`,
    `missing_primary_repo_count: ${githubSummary.missing_primary_repo_count || 0}`,
    `projects_missing_github_link: ${(githubSummary.projects_missing_github_link || []).join(", ") || "none"}`,
    `repos_missing_github_link: ${(githubSummary.repos_missing_github_link || []).join(", ") || "none"}`,
    `warnings: ${(githubSummary.warnings || []).join(" | ") || "none"}`,
  ]);
  setList("reports-queue-summary", "reports-queue-summary-empty", [
    `item_count: ${queueSummary.item_count || 0}`,
    ...countLines("status", queueSummary.counts_by_status),
    ...countLines("priority", queueSummary.counts_by_priority),
    ...countLines("type", queueSummary.counts_by_type),
    `blocked_items: ${(queueSummary.blocked_items || []).length}`,
    `ready_items: ${(queueSummary.ready_items || []).length}`,
    `in_progress_items: ${(queueSummary.in_progress_items || []).length}`,
  ]);
  setList("reports-agent-summary", "reports-agent-summary-empty", [
    `agent_count: ${agentSummary.agent_count || 0}`,
    `handoff_target_count: ${agentSummary.handoff_target_count || 0}`,
    ...countLines("role", agentSummary.counts_by_role),
    ...countLines("execution_mode", agentSummary.counts_by_execution_mode),
    ...countLines("status", agentSummary.counts_by_status),
  ]);
  setList("reports-orchestration-summary", "reports-orchestration-summary-empty", [
    `orchestration_available: ${orchestrationSummary.orchestration_available}`,
    `assigned_count: ${orchestrationSummary.assigned_count || 0}`,
    `unassigned_count: ${orchestrationSummary.unassigned_count || 0}`,
    `blocked_count: ${orchestrationSummary.blocked_count || 0}`,
    `risk_count: ${orchestrationSummary.risk_count || 0}`,
    `latest_orchestration_artifact: ${orchestrationSummary.latest_orchestration_artifact || "(none)"}`,
  ]);
  setList("reports-escalation-summary", "reports-escalation-summary-empty", [
    `escalation_available: ${escalationSummary.escalation_available}`,
    `local_llm_suitable_count: ${escalationSummary.local_llm_suitable_count || 0}`,
    `codex_suitable_count: ${escalationSummary.codex_suitable_count || 0}`,
    `cloud_llm_recommended_count: ${escalationSummary.cloud_llm_recommended_count || 0}`,
    `human_required_count: ${escalationSummary.human_required_count || 0}`,
    `blocked_or_needs_clarification_count: ${escalationSummary.blocked_or_needs_clarification_count || 0}`,
    `latest_escalation_artifact: ${escalationSummary.latest_escalation_artifact || "(none)"}`,
  ]);
  setList("reports-docs-summary", "reports-docs-summary-empty", [
    `docs_ready: ${docsSummary.docs_ready}`,
    `present_count: ${docsSummary.present_count || 0}`,
    `missing_count: ${docsSummary.missing_count || 0}`,
    `missing_docs: ${(docsSummary.missing_docs || []).join(", ") || "none"}`,
  ]);
  setList("reports-readiness", "reports-readiness-empty", Object.keys(readiness).map((key) => `${key}: ${readiness[key]}`));
  setList("reports-action-center", "reports-action-center-empty", [
    `blocked_work_items: ${(actionCenter.blocked_work_items || []).length}`,
    `urgent_or_high_priority_items: ${(actionCenter.urgent_or_high_priority_items || []).length}`,
    `unassigned_queue_items: ${(actionCenter.unassigned_queue_items || []).length}`,
    `cloud_escalation_candidates: ${actionCenter.cloud_escalation_candidates || 0}`,
    `human_required_items: ${actionCenter.human_required_items || 0}`,
    `missing_docs: ${(actionCenter.missing_docs || []).join(", ") || "none"}`,
    `projects_missing_github_link: ${(actionCenter.projects_missing_github_link || []).join(", ") || "none"}`,
    `projects_missing_primary_repo: ${(actionCenter.projects_missing_primary_repo || []).join(", ") || "none"}`,
    `repos_missing_github_identity: ${(actionCenter.repos_missing_github_identity || []).join(", ") || "none"}`,
    `missing_local_state_files: ${(actionCenter.missing_local_state_files || []).join(", ") || "none"}`,
  ]);
  renderWorkflowCards("reports-operator-workflows", "reports-operator-workflows-empty", report.operator_workflows || []);
  setList("reports-warnings", "reports-warnings-empty", report.warnings || []);
  setList("reports-risks", "reports-risks-empty", report.risks || []);
  setList("boundary-list", "boundary-empty-state", report.boundary_confirmations || []);
}

export async function loadDashboardReport(state, deps) {
  setMessage("reports-message", "Loading dashboard report...", "loading");
  const payload = await fetchJson("/api/reports/dashboard", { method: "GET" });
  state.report = payload;
  renderReportSummary(state, payload, deps);
  setMessage("reports-message", "Report loaded.", "success");
}

export function renderLocalProjectReportFoundation(report, countLines) {
  const activeProject = (report && report.active_project) || {};
  const projectHealth = (report && report.project_health) || {};
  const roadmapSummary = (report && report.roadmap_summary) || {};
  const queueSummary = (report && report.queue_summary) || {};
  const validationSummary = (report && report.validation_summary) || {};
  const documentationSummary = (report && report.documentation_summary) || {};
  const blockers = Array.isArray(report && report.blockers) ? report.blockers : [];
  const warnings = Array.isArray(report && report.warnings) ? report.warnings : [];

  setText("reports-local-active-project", activeProject.active_project_name || activeProject.active_project_id || "None selected");
  setText("reports-local-project-health", projectHealth.overall_status || "needs_attention");
  setText("reports-local-recommended-next-action", (report && report.recommended_next_action) || "No recommendation available.");
  setList("reports-local-roadmap-summary", "reports-local-roadmap-summary-empty", [
    `roadmap_doc_exists: ${Boolean(roadmapSummary.roadmap_doc_exists)}`,
    `active_milestone: ${roadmapSummary.active_milestone || "none"}`,
    `status: ${roadmapSummary.status || "missing"}`,
  ]);
  setList("reports-local-queue-summary", "reports-local-queue-summary-empty", [
    `item_count: ${queueSummary.item_count || 0}`,
    ...countLines("status", queueSummary.counts_by_status),
    `blocked_count: ${queueSummary.blocked_count || 0}`,
    `ready_count: ${queueSummary.ready_count || 0}`,
  ]);
  setList(
    "reports-local-validation-summary",
    "reports-local-validation-summary-empty",
    Object.keys(validationSummary)
      .sort()
      .map((key) => `${key}: ${validationSummary[key]}`),
  );
  setList("reports-local-documentation-summary", "reports-local-documentation-summary-empty", [
    `docs_ready: ${Boolean(documentationSummary.docs_ready)}`,
    `present_count: ${documentationSummary.present_count || 0}`,
    `missing_count: ${documentationSummary.missing_count || 0}`,
    `missing_docs: ${(documentationSummary.missing_docs || []).join(", ") || "none"}`,
  ]);
  setList("reports-local-blockers", "reports-local-blockers-empty", blockers);
  setList("reports-local-warnings", "reports-local-warnings-empty", warnings);
}

export function renderLocalProjectReportFoundationUnavailable() {
  setText("reports-local-active-project", "Unavailable");
  setText("reports-local-project-health", "needs_attention");
  setText("reports-local-recommended-next-action", "Local project report endpoint unavailable.");
  setList("reports-local-roadmap-summary", "reports-local-roadmap-summary-empty", []);
  setList("reports-local-queue-summary", "reports-local-queue-summary-empty", []);
  setList("reports-local-validation-summary", "reports-local-validation-summary-empty", []);
  setList("reports-local-documentation-summary", "reports-local-documentation-summary-empty", []);
  setList("reports-local-blockers", "reports-local-blockers-empty", ["Local project report endpoint unavailable."]);
  setList("reports-local-warnings", "reports-local-warnings-empty", []);
}

export async function loadLocalProjectReportFoundation(countLines) {
  const payload = await fetchJson("/api/local-project-report", { method: "GET" });
  renderLocalProjectReportFoundation(payload, countLines);
}

export async function loadReportSlices(renderWorkflowCards) {
  const readiness = await fetchJson("/api/reports/readiness", { method: "GET" });
  const actionCenter = await fetchJson("/api/reports/action-center", { method: "GET" });
  const workflows = await fetchJson("/api/reports/operator-workflows", { method: "GET" });
  setList("reports-readiness", "reports-readiness-empty", Object.keys(readiness.readiness_indicators || {}).map((key) => `${key}: ${readiness.readiness_indicators[key]}`));
  setList("reports-action-center", "reports-action-center-empty", [
    `blocked_work_items: ${(actionCenter.action_center || {}).blocked_work_items ? (actionCenter.action_center.blocked_work_items || []).length : 0}`,
    `urgent_or_high_priority_items: ${(actionCenter.action_center || {}).urgent_or_high_priority_items ? (actionCenter.action_center.urgent_or_high_priority_items || []).length : 0}`,
    `unassigned_queue_items: ${(actionCenter.action_center || {}).unassigned_queue_items ? (actionCenter.action_center.unassigned_queue_items || []).length : 0}`,
  ]);
  renderWorkflowCards("reports-operator-workflows", "reports-operator-workflows-empty", workflows.operator_workflows || []);
}

export async function loadExportPreview(state, formatName) {
  const payload = await fetchJson(`/api/reports/export${toQuery({ format: formatName || "json" })}`, { method: "GET" });
  state.exportText = String(payload.content || "");
  setCodeBlock("reports-export-content", "reports-export-content-empty", state.exportText);
  return payload;
}

export async function copyExportText(state, loadExportPreviewForState) {
  if (!state.exportText) {
    await loadExportPreviewForState("json");
  }
  if (!state.exportText) {
    return false;
  }
  if (navigator.clipboard && navigator.clipboard.writeText) {
    await navigator.clipboard.writeText(state.exportText);
    return true;
  }
  const helper = document.createElement("textarea");
  helper.value = state.exportText;
  document.body.appendChild(helper);
  helper.select();
  document.execCommand("copy");
  document.body.removeChild(helper);
  return true;
}

export function bindReportsActions({
  refreshSummaryAndReport,
  copyExportTextForState,
  loadExportPreviewForState,
  loadHandoffPreview,
  loadOrchestrationPlan,
  loadEscalationPlan,
}) {
  on("reports-refresh", "click", async () => {
    try {
      await refreshSummaryAndReport();
      setMessage("reports-message", "Report refreshed.", "success");
    } catch (error) {
      setMessage("reports-message", String(error.message || error), "error");
    }
  });

  on("reports-copy-json", "click", async () => {
    try {
      const copied = await copyExportTextForState();
      setMessage("reports-message", copied ? "Report JSON copied." : "Nothing to copy.", copied ? "success" : "warn");
    } catch (error) {
      setMessage("reports-message", String(error.message || error), "error");
    }
  });

  on("reports-export-json", "click", async () => {
    try {
      await loadExportPreviewForState("json");
      setMessage("reports-message", "Report export JSON generated in-page.", "success");
    } catch (error) {
      setMessage("reports-message", String(error.message || error), "error");
    }
  });

  on("reports-generate-handoff", "click", async () => {
    try {
      await loadHandoffPreview();
      await refreshSummaryAndReport();
      setMessage("reports-message", "Handoff preview refreshed.", "success");
    } catch (error) {
      setMessage("reports-message", String(error.message || error), "error");
    }
  });

  on("reports-generate-orchestration", "click", async () => {
    try {
      await loadOrchestrationPlan({}, false);
      await refreshSummaryAndReport();
      setMessage("reports-message", "Orchestration plan refreshed.", "success");
    } catch (error) {
      setMessage("reports-message", String(error.message || error), "error");
    }
  });

  on("reports-generate-escalation", "click", async () => {
    try {
      await loadEscalationPlan({}, false);
      await refreshSummaryAndReport();
      setMessage("reports-message", "Escalation plan refreshed.", "success");
    } catch (error) {
      setMessage("reports-message", String(error.message || error), "error");
    }
  });
}