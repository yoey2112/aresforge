import { byId, on, setCodeBlock, setList, setMessage, setText } from "/js/core/dom.js";
import { fetchJson, prunePayload, toQuery } from "/js/core/http.js";
import { createState } from "/js/core/state.js";
import {
  activateQueueIntakeFocus as activateQueueIntakeFocusSection,
  buildIntakePayload as buildIntakePayloadSection,
  bindHomeActions,
  bindHomeQuickNavActions,
  focusNewProjectWizard as focusNewProjectWizardSection,
  loadLocalHomeDashboard,
  renderActiveProjectIntakeResult as renderActiveProjectIntakeResultSection,
  renderActiveProjectSummary as renderActiveProjectSummarySection,
  renderActiveProjectWorkbench as renderActiveProjectWorkbenchSection,
  renderLocalHomeDashboardUnavailable,
} from "/js/sections/home.js";
import {
  bindProjectsActions,
  loadProjectsSection,
  setActiveProject as setActiveProjectSection,
} from "/js/sections/projects.js";
import {
  bindQueueActions,
  bindQueueLifecycleActions,
  buildQueuePayload as buildQueuePayloadSection,
  loadQueue as loadQueueSection,
  renderLocalQueueAddResult as renderLocalQueueAddResultSection,
  setLocalQueueLifecycleItemId as setLocalQueueLifecycleItemIdSection,
} from "/js/sections/queue.js";
import {
  bindEscalationActions,
  loadEscalationPlan as loadEscalationPlanSection,
} from "/js/sections/escalation.js";
import {
  bindOrchestrationActions,
  loadOrchestrationPlan as loadOrchestrationPlanSection,
} from "/js/sections/orchestration.js";
import {
  bindAutonomyActions,
  loadAutonomyControlCenter as loadAutonomyControlCenterSection,
} from "/js/sections/autonomy.js";
import {
  bindGitHubSyncActions,
  loadGitHubSyncControlPanel as loadGitHubSyncControlPanelSection,
} from "/js/sections/githubSync.js";
import {
  bindReportsActions,
  copyExportText as copyExportTextSection,
  loadDashboardReport as loadDashboardReportSection,
  loadExportPreview as loadExportPreviewSection,
  loadLocalProjectReportFoundation as loadLocalProjectReportFoundationSection,
  loadReportSlices as loadReportSlicesSection,
  queueEntries,
  renderWorkflowCards,
  renderLocalProjectReportFoundationUnavailable,
  statusBadgeText,
} from "/js/sections/reports.js";
import {
  approveAgentDispatchPlan as approveAgentDispatchPlanSection,
  approveArchitecture as approveArchitectureSection,
  approveDocumentationCloseoutPlan as approveDocumentationCloseoutPlanSection,
  approveExecutionPhaseApproval as approveExecutionPhaseApprovalSection,
  approveMilestoneIssuePlan as approveMilestoneIssuePlanSection,
  approveValidationExecutionPlan as approveValidationExecutionPlanSection,
  approveScope as approveScopeSection,
  bindProjectFactoryAgentDispatchActions,
  bindProjectFactoryArchitectureActions,
  bindProjectFactoryCloseoutActions,
  bindProjectFactoryExecutionApprovalActions,
  bindProjectFactoryMilestonePlanActions,
  bindProjectFactoryScopeActions,
  bindProjectFactoryValidationActions,
  buildAgentDispatchPlanPayload as buildAgentDispatchPlanPayloadSection,
  buildArchitectureAuthoringPayload as buildArchitectureAuthoringPayloadSection,
  buildDocumentationCloseoutPlanPayload as buildDocumentationCloseoutPlanPayloadSection,
  buildExecutionPhaseApprovalPayload as buildExecutionPhaseApprovalPayloadSection,
  buildMilestoneIssuePlanPayload as buildMilestoneIssuePlanPayloadSection,
  buildScopeAuthoringPayload as buildScopeAuthoringPayloadSection,
  buildValidationExecutionPlanPayload as buildValidationExecutionPlanPayloadSection,
  loadAgentDispatchPlan as loadAgentDispatchPlanSection,
  loadArchitectureContract as loadArchitectureContractSection,
  loadDocumentationCloseoutPlan as loadDocumentationCloseoutPlanSection,
  loadExecutionPhaseApproval as loadExecutionPhaseApprovalSection,
  loadExecutionReadiness as loadExecutionReadinessSection,
  loadMilestoneIssuePlan as loadMilestoneIssuePlanSection,
  loadScopePackage as loadScopePackageSection,
  loadValidationExecutionPlan as loadValidationExecutionPlanSection,
  prepareAgentDispatchPlan as prepareAgentDispatchPlanSection,
  prepareArchitectureContract as prepareArchitectureContractSection,
  prepareDocumentationCloseoutPlan as prepareDocumentationCloseoutPlanSection,
  prepareExecutionPhaseApproval as prepareExecutionPhaseApprovalSection,
  prepareMilestoneIssuePlan as prepareMilestoneIssuePlanSection,
  prepareScopePackage as prepareScopePackageSection,
  prepareValidationExecutionPlan as prepareValidationExecutionPlanSection,
  renderAgentDispatchPlan as renderAgentDispatchPlanSection,
  renderArchitectureAuthoring as renderArchitectureAuthoringSection,
  renderDocumentationCloseoutPlan as renderDocumentationCloseoutPlanSection,
  renderExecutionPhaseApproval as renderExecutionPhaseApprovalSection,
  renderExecutionReadiness as renderExecutionReadinessSection,
  renderMilestoneIssuePlan as renderMilestoneIssuePlanSection,
  renderScopeAuthoring as renderScopeAuthoringSection,
  renderValidationExecutionPlan as renderValidationExecutionPlanSection,
  saveAgentDispatchPlanDraft as saveAgentDispatchPlanDraftSection,
  saveArchitectureDraft as saveArchitectureDraftSection,
  saveDocumentationCloseoutPlanDraft as saveDocumentationCloseoutPlanDraftSection,
  saveExecutionPhaseApprovalDraft as saveExecutionPhaseApprovalDraftSection,
  saveMilestoneIssuePlanDraft as saveMilestoneIssuePlanDraftSection,
  saveScopeDraft as saveScopeDraftSection,
  saveValidationExecutionPlanDraft as saveValidationExecutionPlanDraftSection,
} from "/js/sections/projectFactory/index.js";
import {
  bindReposActions,
  inspectRepoGitHubLinkSection,
  loadReposSection,
} from "/js/sections/repos.js";
import { bindWorkspaceActions, loadWorkspace, renderWorkspaceUnavailable } from "/js/sections/workspace.js";

function parseCommaList(value) {
  if (!value || typeof value !== "string") {
    return [];
  }
  return value
    .split(",")
    .map((item) => item.trim())
    .filter((item, index, all) => item && all.indexOf(item) === index);
}

function slugify(value) {
  const slug = String(value || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 48);
  return slug || "item";
}

function generatedQueueItemId(title) {
  return `m44-${slugify(title)}-${Date.now().toString(36)}`;
}

function activateSection(sectionName) {
  document.querySelectorAll(".nav-item").forEach((button) => {
    button.classList.toggle("active", button.dataset.section === sectionName);
  });
  document.querySelectorAll(".panel").forEach((panel) => {
    panel.classList.toggle("active", panel.dataset.panel === sectionName);
  });
}

function bindNavigation() {
  document.querySelectorAll(".nav-item").forEach((button) => {
    button.addEventListener("click", () => activateSection(button.dataset.section));
  });
}

function countLines(prefix, counts) {
  if (!counts || typeof counts !== "object") {
    return [];
  }
  return Object.keys(counts)
    .sort()
    .map((key) => `${prefix} ${key}: ${counts[key]}`);
}

const state = createState();

function renderBootstrapStatus(payload) {
  state.bootstrapStatus = payload || null;
  const files = (payload && payload.files) || {};
  const lines = [
    `bootstrap_ready: ${Boolean(payload && payload.bootstrap_ready)}`,
    `project_state_exists: ${Boolean(files.project_state)}`,
    `registry_exists: ${Boolean(files.managed_project_registry)}`,
    `queue_exists: ${Boolean(files.project_queue)}`,
    `agent_profiles_exists: ${Boolean(files.agent_profiles)}`,
    `aresforge_project_registered: ${Boolean((payload && payload.seeded_projects || []).includes("aresforge"))}`,
    `aresforge_github_link_present: ${Boolean((payload && payload.seeded_repos || []).includes("aresforge"))}`,
  ];
  setList("bootstrap-status-list", "bootstrap-status-empty", lines);
  setList("bootstrap-warnings", "bootstrap-warnings-empty", (payload && payload.warnings) || []);
  const homeStatus = byId("home-bootstrap-status");
  if (homeStatus) {
    if (payload && payload.bootstrap_ready) {
      homeStatus.textContent = "Bootstrap complete. Local setup is ready.";
    } else {
      const next = (payload && payload.recommended_next_actions && payload.recommended_next_actions[0]) || "Run Bootstrap Setup.";
      homeStatus.textContent = `Setup incomplete. ${next}`;
    }
  }
}

function renderBootstrapPlan(payload) {
  state.bootstrapPlan = payload || null;
  const actions = ((payload && payload.actions) || []).map((action) => `${action.id || "action"}: ${action.description || ""}`);
  setList("bootstrap-plan-actions", "bootstrap-plan-actions-empty", actions);
  const summary = [
    `would_initialize: ${((payload && payload.would_initialize) || []).join(", ") || "none"}`,
    `would_seed_projects: ${((payload && payload.would_seed_projects) || []).join(", ") || "none"}`,
    `would_seed_repos: ${((payload && payload.would_seed_repos) || []).join(", ") || "none"}`,
    `would_seed_agents: ${((payload && payload.would_seed_agents) || []).join(", ") || "none"}`,
    `would_seed_handoff_targets: ${((payload && payload.would_seed_handoff_targets) || []).join(", ") || "none"}`,
    `would_seed_queue_items: ${((payload && payload.would_seed_queue_items) || []).join(", ") || "none"}`,
  ];
  setList("bootstrap-plan-summary", "bootstrap-plan-summary-empty", summary);
}

function renderBootstrapApply(payload) {
  const lines = [
    `bootstrap_ready: ${Boolean(payload && payload.bootstrap_ready)}`,
    `initialized_files: ${((payload && payload.initialized_files) || []).join(", ") || "none"}`,
    `applied_actions: ${((payload && payload.applied_actions) || []).join(", ") || "none"}`,
    `already_existing_actions: ${((payload && payload.already_existing_actions) || []).join(", ") || "none"}`,
    `seeded_queue_items: ${((payload && payload.seeded_queue_items) || []).join(", ") || "none"}`,
  ];
  setList("bootstrap-apply-result", "bootstrap-apply-result-empty", lines.concat((payload && payload.warnings) || []));
}

async function loadBootstrapStatus() {
  setMessage("bootstrap-message", "Loading bootstrap status...", "loading");
  const payload = await fetchJson("/api/bootstrap/status", { method: "GET" });
  renderBootstrapStatus(payload);
  setMessage("bootstrap-message", "Bootstrap status loaded.", "success");
  return payload;
}

async function loadBootstrapPlan() {
  setMessage("bootstrap-message", "Loading bootstrap plan...", "loading");
  const seedSampleWork = byId("bootstrap-seed-sample-work") && byId("bootstrap-seed-sample-work").checked;
  const payload = await fetchJson(`/api/bootstrap/plan${toQuery({ seed_sample_work: seedSampleWork ? "true" : "false" })}`, { method: "GET" });
  renderBootstrapPlan(payload);
  setMessage("bootstrap-message", "Bootstrap plan loaded.", "success");
  return payload;
}

async function applyBootstrap() {
  setMessage("bootstrap-message", "Applying bootstrap locally...", "loading");
  const payload = await fetchJson("/api/bootstrap/apply", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      force: Boolean(byId("bootstrap-force") && byId("bootstrap-force").checked),
      seed_sample_work: Boolean(byId("bootstrap-seed-sample-work") && byId("bootstrap-seed-sample-work").checked),
    }),
  });
  renderBootstrapApply(payload);
  setMessage("bootstrap-message", "Bootstrap apply completed.", "success");
  return payload;
}

function activeProjectId() {
  return String((state.activeProject && state.activeProject.active_project_id) || "").trim();
}

function activeRepoId() {
  return String((state.activeProject && state.activeProject.active_repo_id) || "").trim();
}

function renderActiveProjectSummary(payload) {
  renderActiveProjectSummarySection(state, payload);
}

function parseLineList(value) {
  if (!value || typeof value !== "string") {
    return [];
  }
  return value
    .split(/\r?\n/)
    .map((item) => item.trim())
    .filter((item, index, all) => item && all.indexOf(item) === index);
}

function toTextareaList(value) {
  if (!Array.isArray(value)) {
    return "";
  }
  return value.map((item) => String(item || "").trim()).filter(Boolean).join("\n");
}

function renderActiveProjectWorkbench(report) {
  renderActiveProjectWorkbenchSection(report);
}

function renderProjectFactoryDossier(payload) {
  state.projectFactoryDossier = payload || null;
  const dossier = (payload && payload.dossier) || {};
  const safety = (payload && payload.safety_boundary) || {};
  const projectName = dossier.name || payload.project_id || "-";
  const lines = [];
  if (!payload || !payload.dossier_exists) {
    lines.push(`project: ${projectName}`);
    lines.push(`lifecycle_state: ${payload && payload.lifecycle_state ? payload.lifecycle_state : "not_started"}`);
    lines.push(`next_recommended_action: ${payload && payload.next_recommended_action ? payload.next_recommended_action : "create_project_via_new_project_wizard"}`);
    lines.push(`github_mode: ${(dossier && dossier.github_mode) || "not_set"}`);
  } else {
    lines.push(`project: ${projectName} (${payload.project_id || "-"})`);
    lines.push(`lifecycle_state: ${payload.lifecycle_state || "-"}`);
    lines.push(`next_recommended_action: ${payload.next_recommended_action || "-"}`);
    lines.push(`github_mode: ${dossier.github_mode || "create-later"}`);
    lines.push(`github_status: ${(safety.github_mutation_status || "not_requested")}`);
    lines.push(`model_status: ${(safety.model_execution_status || "not_requested")}`);
  }
  setList("home-project-factory-dossier", "home-project-factory-dossier-empty", lines);
  setList("home-project-factory-workflow", "home-project-factory-workflow-empty", renderWorkflowTimeline(payload && payload.workflow_steps));
  setList("home-scope-kickoff", "home-scope-kickoff-empty", [
    `selected_project: ${payload && payload.project_id ? payload.project_id : "none"}`,
    `lifecycle_state: ${payload && payload.lifecycle_state ? payload.lifecycle_state : "not_started"}`,
    `next_recommended_action: ${payload && payload.next_recommended_action ? payload.next_recommended_action : "create_project_via_new_project_wizard"}`,
    `initial_requirements: ${(dossier && dossier.initial_requirements) || "none yet"}`,
  ]);
  const scopeState = byId("home-scope-authoring-state");
  if (scopeState) {
    scopeState.textContent = `Scope lifecycle state: ${payload && payload.lifecycle_state ? payload.lifecycle_state : "not_started"}`;
  }
}

function renderWorkflowTimeline(steps) {
  return (steps || []).map((step) => {
    return `${step.step_id || "-"} | ${step.label || "-"} | status=${step.status || "-"} | gate=${step.gate_type || "none"} | local_only=${Boolean(step.local_only)}`;
  });
}

function activateQueueIntakeFocus() {
  activateQueueIntakeFocusSection(activateSection);
}

function renderAgents(agents) {
  const lines = (agents || []).map((agent) => {
    const types = (agent.allowed_item_types || []).join(", ") || "-";
    return `${agent.agent_id} | ${agent.name} | role=${agent.role || "-"} | mode=${agent.execution_mode || "-"} | status=${agent.status || "-"} | types=${types}`;
  });
  setList("agents-list", "agents-empty-state", lines);
}

function renderHandoffTargets(targets) {
  const lines = (targets || []).map((target) => {
    return `${target.target_id} | ${target.name} | type=${target.target_type || "-"} | status=${target.status || "-"}`;
  });
  setList("handoff-targets-list", "handoff-targets-empty-state", lines);
}

async function loadActiveProject() {
  const payload = await fetchJson("/api/projects/active");
  renderActiveProjectSummary(payload);
  return payload;
}

async function loadProjectFactoryDossier(projectId) {
  const query = toQuery({ project_id: projectId || "" });
  const payload = await fetchJson(`/api/project-factory/dossier${query}`, { method: "GET" });
  renderProjectFactoryDossier(payload);
  return payload;
}

async function prepareScopePackage() {
  return prepareScopePackageSection(activeProjectId);
}

function buildScopeAuthoringPayload() {
  return buildScopeAuthoringPayloadSection({
    activeProjectId,
    parseLineList,
  });
}

function renderScopeAuthoring(payload) {
  renderScopeAuthoringSection(state, payload, { toTextareaList });
}

function buildArchitectureAuthoringPayload() {
  return buildArchitectureAuthoringPayloadSection({
    activeProjectId,
    parseLineList,
  });
}

function renderArchitectureAuthoring(payload) {
  renderArchitectureAuthoringSection(state, payload, { toTextareaList });
}

function buildMilestoneIssuePlanPayload() {
  return buildMilestoneIssuePlanPayloadSection({
    activeProjectId,
    parseLineList,
  });
}

function buildGithubApplyPlanPayload() {
  return prunePayload({
    project_id: activeProjectId(),
    apply_summary: byId("github-apply-summary").value.trim(),
    operator_notes: byId("github-apply-operator-notes").value.trim(),
    labels: parseLineList(byId("github-apply-labels").value),
    dry_run_notes: parseLineList(byId("github-apply-dry-run-notes").value),
    preflight_checks: parseLineList(byId("github-apply-preflight-checks").value),
    approval_conditions: parseLineList(byId("github-apply-approval-conditions").value),
    known_risks: parseLineList(byId("github-apply-known-risks").value),
  });
}

function buildAgentDispatchPlanPayload() {
  return buildAgentDispatchPlanPayloadSection({
    activeProjectId,
    parseLineList,
  });
}

function buildValidationExecutionPlanPayload() {
  return buildValidationExecutionPlanPayloadSection({
    activeProjectId,
    parseLineList,
  });
}

function buildDocumentationCloseoutPlanPayload() {
  return buildDocumentationCloseoutPlanPayloadSection({
    activeProjectId,
    parseLineList,
  });
}

function buildExecutionPhaseApprovalPayload() {
  return buildExecutionPhaseApprovalPayloadSection({
    activeProjectId,
  });
}

function renderMilestoneIssuePlan(payload) {
  renderMilestoneIssuePlanSection(state, payload, { toTextareaList });
}

function renderGithubApplyPlan(payload) {
  state.githubApplyPlan = payload || null;
  const message = byId("home-github-apply-plan-message");
  const stateLine = byId("home-github-apply-plan-state");
  const statusLine = byId("home-github-apply-plan-status");
  const exists = Boolean(payload && payload.github_apply_plan_exists);
  const plan = (payload && payload.github_apply_plan) || {};
  if (!exists) {
    byId("github-apply-summary").value = "";
    byId("github-apply-operator-notes").value = "";
    byId("github-apply-labels").value = "";
    byId("github-apply-dry-run-notes").value = "";
    byId("github-apply-preflight-checks").value = "";
    byId("github-apply-approval-conditions").value = "";
    byId("github-apply-known-risks").value = "";
    setList("home-github-apply-plan-audit-trail", "home-github-apply-plan-audit-trail-empty", []);
    setCodeBlock("home-github-apply-plan-milestones", "home-github-apply-plan-milestones-empty", "");
    setCodeBlock("home-github-apply-plan-issues", "home-github-apply-plan-issues-empty", "");
    if (message) {
      message.textContent = "No GitHub apply plan found. Approve milestone/issue plan first, then prepare GitHub apply plan.";
    }
    if (stateLine) {
      stateLine.textContent = "GitHub Apply Plan lifecycle state: not_started";
    }
    if (statusLine) {
      statusLine.textContent = "mutation=not_requested | execution=not_executed";
    }
    return;
  }
  byId("github-apply-summary").value = String(plan.apply_summary || "");
  byId("github-apply-operator-notes").value = String(plan.operator_notes || "");
  byId("github-apply-labels").value = toTextareaList(plan.labels);
  byId("github-apply-dry-run-notes").value = toTextareaList(plan.dry_run_notes);
  byId("github-apply-preflight-checks").value = toTextareaList(plan.preflight_checks);
  byId("github-apply-approval-conditions").value = toTextareaList(plan.approval_conditions);
  byId("github-apply-known-risks").value = toTextareaList(plan.known_risks);
  const intent = plan.mutation_intent || {};
  setCodeBlock("home-github-apply-plan-milestones", "home-github-apply-plan-milestones-empty", JSON.stringify(intent.create_milestones || [], null, 2));
  setCodeBlock("home-github-apply-plan-issues", "home-github-apply-plan-issues-empty", JSON.stringify(intent.create_issues || [], null, 2));
  setList(
    "home-github-apply-plan-audit-trail",
    "home-github-apply-plan-audit-trail-empty",
    (plan.audit_trail || []).map((entry) => `${entry.timestamp || "-"} | ${entry.event_type || "-"} | state=${entry.lifecycle_state || "-"} | actor=${entry.actor || "-"}`)
  );
  if (message) {
    message.textContent = "This is a local apply plan only. It does not create GitHub milestones or issues.";
  }
  if (stateLine) {
    stateLine.textContent = `GitHub Apply Plan lifecycle state: ${plan.lifecycle_state || "not_started"}`;
  }
  if (statusLine) {
    statusLine.textContent = `mutation=${plan.github_mutation_status || "not_requested"} | execution=${plan.github_execution_status || "not_executed"}`;
  }
}

function renderAgentDispatchPlan(payload) {
  renderAgentDispatchPlanSection(state, payload, { toTextareaList });
}

function renderValidationExecutionPlan(payload) {
  renderValidationExecutionPlanSection(state, payload, { toTextareaList });
}

function renderDocumentationCloseoutPlan(payload) {
  renderDocumentationCloseoutPlanSection(state, payload, { toTextareaList });
}

function renderExecutionPhaseApproval(payload) {
  renderExecutionPhaseApprovalSection(state, payload);
}

function renderExecutionReadiness(payload) {
  renderExecutionReadinessSection(state, payload);
}

async function loadScopePackage(projectId) {
  return loadScopePackageSection(projectId, { renderScopeAuthoringForState: renderScopeAuthoring });
}

async function loadArchitectureContract(projectId) {
  return loadArchitectureContractSection(projectId, { renderArchitectureAuthoringForState: renderArchitectureAuthoring });
}

async function loadMilestoneIssuePlan(projectId) {
  return loadMilestoneIssuePlanSection(projectId, { renderMilestoneIssuePlanForState: renderMilestoneIssuePlan });
}

async function loadGithubApplyPlan(projectId) {
  const query = toQuery({ project_id: projectId || "" });
  const payload = await fetchJson(`/api/project-factory/github-apply-plan${query}`, { method: "GET" });
  renderGithubApplyPlan(payload);
  return payload;
}

async function loadAgentDispatchPlan(projectId) {
  return loadAgentDispatchPlanSection(projectId, { renderAgentDispatchPlanForState: renderAgentDispatchPlan });
}

async function loadValidationExecutionPlan(projectId) {
  return loadValidationExecutionPlanSection(projectId, { renderValidationExecutionPlanForState: renderValidationExecutionPlan });
}

async function loadDocumentationCloseoutPlan(projectId) {
  return loadDocumentationCloseoutPlanSection(projectId, { renderDocumentationCloseoutPlanForState: renderDocumentationCloseoutPlan });
}

async function loadExecutionPhaseApproval(projectId) {
  return loadExecutionPhaseApprovalSection(projectId, { renderExecutionPhaseApprovalForState: renderExecutionPhaseApproval });
}

async function loadExecutionReadiness(projectId) {
  return loadExecutionReadinessSection(projectId, { renderExecutionReadinessForState: renderExecutionReadiness });
}

async function saveScopeDraft() {
  return saveScopeDraftSection(buildScopeAuthoringPayload);
}

async function approveScope() {
  return approveScopeSection(activeProjectId);
}

async function prepareArchitectureContract() {
  return prepareArchitectureContractSection(activeProjectId);
}

async function saveArchitectureDraft() {
  return saveArchitectureDraftSection(buildArchitectureAuthoringPayload);
}

async function approveArchitecture() {
  return approveArchitectureSection(activeProjectId);
}

async function prepareMilestoneIssuePlan() {
  return prepareMilestoneIssuePlanSection(activeProjectId);
}

async function saveMilestoneIssuePlanDraft() {
  return saveMilestoneIssuePlanDraftSection(buildMilestoneIssuePlanPayload);
}

async function approveMilestoneIssuePlan() {
  return approveMilestoneIssuePlanSection(activeProjectId);
}

async function prepareGithubApplyPlan() {
  const payload = await fetchJson("/api/project-factory/github-apply-plan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(prunePayload({ project_id: activeProjectId() })),
  });
  return payload;
}

async function saveGithubApplyPlanDraft() {
  const payload = await fetchJson("/api/project-factory/github-apply-plan", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(buildGithubApplyPlanPayload()),
  });
  return payload;
}

async function approveGithubApplyPlan() {
  const payload = await fetchJson("/api/project-factory/github-apply-plan/approve", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(prunePayload({ project_id: activeProjectId() })),
  });
  return payload;
}

async function prepareAgentDispatchPlan() {
  return prepareAgentDispatchPlanSection(activeProjectId);
}

async function saveAgentDispatchPlanDraft() {
  return saveAgentDispatchPlanDraftSection(buildAgentDispatchPlanPayload);
}

async function approveAgentDispatchPlan() {
  return approveAgentDispatchPlanSection(activeProjectId);
}

async function prepareValidationExecutionPlan() {
  return prepareValidationExecutionPlanSection(activeProjectId);
}

async function saveValidationExecutionPlanDraft() {
  return saveValidationExecutionPlanDraftSection(buildValidationExecutionPlanPayload);
}

async function approveValidationExecutionPlan() {
  return approveValidationExecutionPlanSection(activeProjectId);
}

async function prepareDocumentationCloseoutPlan() {
  return prepareDocumentationCloseoutPlanSection(activeProjectId);
}

async function saveDocumentationCloseoutPlanDraft() {
  return saveDocumentationCloseoutPlanDraftSection(buildDocumentationCloseoutPlanPayload);
}

async function approveDocumentationCloseoutPlan() {
  return approveDocumentationCloseoutPlanSection(activeProjectId);
}

async function prepareExecutionPhaseApproval() {
  return prepareExecutionPhaseApprovalSection(activeProjectId);
}

async function saveExecutionPhaseApprovalDraft() {
  return saveExecutionPhaseApprovalDraftSection(buildExecutionPhaseApprovalPayload);
}

async function approveExecutionPhaseApproval() {
  return approveExecutionPhaseApprovalSection(activeProjectId);
}

async function setActiveProject(projectId) {
  return setActiveProjectSection(projectId, { renderActiveProjectSummary });
}

async function loadProjects() {
  return loadProjectsSection(state, {
    loadActiveProject,
    renderActiveProjectSummary,
    activeProjectId,
    loadProjectFactoryDossier,
    loadScopePackage,
    loadArchitectureContract,
    loadMilestoneIssuePlan,
    loadGithubApplyPlan,
    loadAgentDispatchPlan,
    loadValidationExecutionPlan,
    loadDocumentationCloseoutPlan,
    loadExecutionPhaseApproval,
  });
}

async function loadReposForSelectedProject() {
  return loadReposSection(state, {
    loadProjects,
    refreshSummaryAndReport,
  });
}

async function inspectRepoGitHubLink(repoId, inspectLocalGit) {
  return inspectRepoGitHubLinkSection(state, repoId, inspectLocalGit, {
    loadProjects,
    refreshSummaryAndReport,
  });
}

async function loadQueue() {
  return loadQueueSection({
    state,
    countLines,
    setLocalQueueLifecycleItemId,
    loadDashboardReport,
  });
}

async function loadAutonomyControlCenter(filters) {
  return loadAutonomyControlCenterSection(filters || {
    project_id: "aresforge",
    item_id: "m167-hub-autonomy-control-center-v1",
    autonomy_profile: "github_sync_dry_run",
  });
}

async function loadGitHubSyncControlPanel(filters) {
  return loadGitHubSyncControlPanelSection(filters || {
    project_id: "aresforge",
    item_id: "m180-hub-github-sync-control-panel",
    autonomy_profile: "github_sync_dry_run",
  });
}

async function loadAgents() {
  setMessage("agents-message", "Loading agents...", "loading");
  const payload = await fetchJson("/api/agents");
  renderAgents(payload.agents || []);
  setMessage("agents-message", payload.warnings && payload.warnings.length ? payload.warnings.join(" | ") : "Agents loaded.", payload.warnings && payload.warnings.length ? "warn" : "success");
}

async function loadHandoffTargets() {
  const payload = await fetchJson("/api/handoff-targets");
  renderHandoffTargets(payload.handoff_targets || []);
}

async function loadHandoffPreview() {
  setMessage("handoff-message", "Generating local handoff preview...", "loading");
  const payload = await fetchJson("/api/handoff/preview");
  setCodeBlock("handoff-preview", "handoff-preview-empty", payload.preview || "");
  setMessage("handoff-message", payload.warnings && payload.warnings.length ? payload.warnings.join(" | ") : "Handoff preview loaded. Local-only and not posted anywhere.", payload.warnings && payload.warnings.length ? "warn" : "success");
}

function buildLocalProjectHandoffPayload() {
  return prunePayload({
    project_id: byId("local-project-handoff-project-id").value.trim(),
    include_queue: byId("local-project-handoff-include-queue").checked,
    include_reports: byId("local-project-handoff-include-reports").checked,
    include_evidence: byId("local-project-handoff-include-evidence").checked,
    next_milestone: byId("local-project-handoff-next-milestone").value.trim(),
    next_instruction: byId("local-project-handoff-next-instruction").value.trim(),
    output: byId("local-project-handoff-output").value.trim(),
    force: byId("local-project-handoff-force").checked,
  });
}

function renderLocalProjectHandoffResult(payload) {
  const summary = (payload && payload.summary) || {};
  setList("local-project-handoff-summary", "local-project-handoff-summary-empty", payload ? [
    `project_id: ${payload.project_id || "-"}`,
    `project_name: ${payload.project_name || "-"}`,
    `queue_total: ${summary.queue_total || 0}`,
    `ready_count: ${summary.ready_count || 0}`,
    `blocked_count: ${summary.blocked_count || 0}`,
    `evidence_captured_count: ${summary.evidence_captured_count || 0}`,
    `closeout_eligible_count: ${summary.closeout_eligible_count || 0}`,
    `output_path: ${payload.output_path || "-"}`,
    `next_safe_action: ${payload.next_safe_action || "-"}`,
  ] : []);
  setCodeBlock("local-project-handoff-preview", "local-project-handoff-preview-empty", payload ? payload.handoff_markdown || "" : "");
}

async function loadDashboardReport() {
  return loadDashboardReportSection(state, {
    countLines,
    queueEntries,
    statusBadgeText,
    renderActiveProjectSummary,
    renderActiveProjectWorkbench,
    renderWorkflowCards,
    renderBootstrapStatus,
  });
}

async function loadLocalProjectReportFoundation() {
  return loadLocalProjectReportFoundationSection(countLines);
}

async function loadReportSlices() {
  return loadReportSlicesSection();
}

async function loadExportPreview(formatName) {
  return loadExportPreviewSection(state, formatName);
}

async function copyExportText() {
  return copyExportTextSection(state, loadExportPreview);
}

async function refreshSummaryAndReport() {
  try {
    await loadLocalHomeDashboard();
  } catch (_error) {
    renderLocalHomeDashboardUnavailable();
  }
  try {
    await loadLocalProjectReportFoundation();
  } catch (_error) {
    renderLocalProjectReportFoundationUnavailable();
  }
  try {
    await loadWorkspace(state);
  } catch (_error) {
    renderWorkspaceUnavailable();
  }
  await loadDashboardReport();
  await loadReportSlices();
  await loadProjectFactoryDossier(activeProjectId());
  await loadArchitectureContract(activeProjectId());
  await loadMilestoneIssuePlan(activeProjectId());
  await loadGithubApplyPlan(activeProjectId());
  await loadDocumentationCloseoutPlan(activeProjectId());
}

async function loadSettings() {
  try {
    const payload = await fetchJson("/api/settings");
    byId("settings-registry-path").textContent = payload.registry_path || "(unavailable)";
    byId("settings-queue-path").textContent = payload.queue_path || "(unavailable)";
    byId("settings-agents-path").textContent = payload.agents_path || "(unavailable)";
    byId("settings-active-project-path").textContent = payload.active_project_path || "(unavailable)";
    const artifacts = payload.default_artifact_paths || {};
    byId("settings-handoff-artifacts-path").textContent = artifacts.handoff || "(unavailable)";
    byId("settings-orchestration-artifacts-path").textContent = artifacts.orchestration || "(unavailable)";
    byId("settings-escalation-artifacts-path").textContent = artifacts.escalation || "(unavailable)";
    byId("settings-dashboard-artifacts-path").textContent = artifacts.dashboard || "(unavailable)";
    const hubServer = payload.hub_server || {};
    byId("settings-hub-host").textContent = hubServer.current_host_hint || hubServer.default_host || "127.0.0.1";
    byId("settings-hub-port").textContent = String(hubServer.current_port_hint || hubServer.default_port || 8765);
    setList("settings-m39-boundaries", "settings-m39-boundaries-empty", payload.m39_boundary_confirmations || []);
    setList("settings-m40-boundaries", "settings-m40-boundaries-empty", payload.m40_boundary_confirmations || []);
    setList("settings-m41-boundaries", "settings-m41-boundaries-empty", payload.m41_boundary_confirmations || []);
    setList("settings-known-limitations", "settings-known-limitations-empty", payload.known_limitations || []);
    setList("settings-next-milestone", "settings-next-milestone-empty", payload.next_milestone_scope || []);
  } catch (_error) {
    byId("settings-registry-path").textContent = "(unavailable)";
    byId("settings-queue-path").textContent = "(unavailable)";
    byId("settings-agents-path").textContent = "(unavailable)";
  }
}

function buildNewProjectWizardPayload() {
  return prunePayload({
    name: byId("wizard-project-name").value.trim(),
    project_id: byId("wizard-project-id").value.trim(),
    description: byId("wizard-description").value.trim(),
    project_type: byId("wizard-project-type").value.trim() || "other",
    preferred_stack: byId("wizard-preferred-stack").value.trim(),
    root_path: byId("wizard-root-path").value.trim(),
    github_owner: byId("wizard-github-owner").value.trim(),
    github_repo: byId("wizard-github-repo").value.trim(),
    github_mode: byId("wizard-github-mode").value.trim() || "create-later",
    default_branch: byId("wizard-default-branch").value.trim() || "main",
    initial_requirements: byId("wizard-initial-requirements").value.trim(),
    tags: parseCommaList(byId("wizard-tags").value),
  });
}

function focusNewProjectWizard() {
  focusNewProjectWizardSection(activateSection);
}

function applyActiveProjectDefaultsToQueueForm() {
  const projectId = activeProjectId();
  const repoId = activeRepoId();
  if (projectId && byId("queue-project-id")) {
    byId("queue-project-id").value = projectId;
  }
  if (repoId && byId("queue-repo-id")) {
    byId("queue-repo-id").value = repoId;
  }
}

function buildQueuePayload() {
  return buildQueuePayloadSection({
    activeProjectId,
    activeRepoId,
    parseCommaList,
  });
}

function setLocalQueueLifecycleItemId(itemId) {
  setLocalQueueLifecycleItemIdSection(itemId);
}

function renderLocalQueueAddResult(payload) {
  renderLocalQueueAddResultSection(payload);
}

function renderActiveProjectIntakeResult(payload) {
  renderActiveProjectIntakeResultSection(state, setLocalQueueLifecycleItemId, payload);
}

function buildIntakePayload() {
  // Static-contract compatibility markers for intake routing and tags:
  // active-project-intake
  // intakeType === "direction" || intakeType === "ui" || intakeType === "refactor"
  // intakeType === "docs"
  return buildIntakePayloadSection({
    activeProjectId,
    activeRepoId,
    parseCommaList,
  });
}

function clearIntakeForm() {
  [
    "intake-title",
    "intake-tags",
    "intake-description",
    "intake-requested-outcome",
    "intake-acceptance-notes",
    "intake-validation-notes",
  ].forEach((id) => {
    if (byId(id)) {
      byId(id).value = "";
    }
  });
  if (byId("intake-type")) {
    byId("intake-type").value = "task";
  }
  if (byId("intake-priority")) {
    byId("intake-priority").value = "normal";
  }
  if (byId("intake-source")) {
    byId("intake-source").value = "active_project_workspace";
  }
}

function buildAgentPayload() {
  const escalationRaw = byId("agent-escalation-allowed").value.trim();
  let escalationAllowed;
  if (escalationRaw === "true") {
    escalationAllowed = true;
  } else if (escalationRaw === "false") {
    escalationAllowed = false;
  }
  return prunePayload({
    agent_id: byId("agent-agent-id").value.trim(),
    name: byId("agent-name").value.trim(),
    role: byId("agent-role").value.trim(),
    description: byId("agent-description").value.trim(),
    execution_mode: byId("agent-execution-mode").value.trim(),
    model_preference: byId("agent-model-preference").value.trim(),
    strengths: parseCommaList(byId("agent-strengths").value),
    constraints: parseCommaList(byId("agent-constraints").value),
    allowed_item_types: parseCommaList(byId("agent-allowed-item-types").value),
    escalation_allowed: escalationAllowed,
    handoff_target_id: byId("agent-handoff-target-id").value.trim(),
    status: byId("agent-status").value.trim(),
    tags: parseCommaList(byId("agent-tags").value),
    notes: byId("agent-notes").value.trim(),
  });
}

function buildHandoffTargetPayload() {
  return prunePayload({
    target_id: byId("target-target-id").value.trim(),
    name: byId("target-name").value.trim(),
    target_type: byId("target-type").value.trim(),
    description: byId("target-description").value.trim(),
    local_command: byId("target-local-command").value.trim(),
    input_format: byId("target-input-format").value.trim(),
    output_format: byId("target-output-format").value.trim(),
    safety_notes: parseCommaList(byId("target-safety-notes").value),
    status: byId("target-status").value.trim(),
    tags: parseCommaList(byId("target-tags").value),
    notes: byId("target-notes").value.trim(),
  });
}

function bindForms() {
  on("scope-authoring-form", "submit", (event) => {
    event.preventDefault();
  });
  on("architecture-authoring-form", "submit", (event) => {
    event.preventDefault();
  });
  on("milestone-plan-form", "submit", (event) => {
    event.preventDefault();
  });

  on("intake-form", "submit", async (event) => {
    event.preventDefault();
    const intakeSubmit = byId("intake-submit");
    const originalIntakeSubmitLabel = intakeSubmit ? intakeSubmit.textContent : "";
    if (!activeProjectId()) {
      setMessage("intake-message", "Select an active project before adding intake work.", "warn");
      renderActiveProjectIntakeResult({
        project_id: "-",
        repo_id: "-",
        status: "not_created",
        warnings: ["No active project selected."],
        next_safe_action: "Select an active project from Projects.",
      });
      return;
    }
    try {
      if (intakeSubmit) {
        intakeSubmit.disabled = true;
        intakeSubmit.textContent = "Adding...";
      }
      setMessage("intake-message", "Creating local queue item for the active project...", "loading");
      const payload = await fetchJson("/api/local-queue/items", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildIntakePayload()),
      });
      renderActiveProjectIntakeResult(payload);
      renderLocalQueueAddResult(payload);
      clearIntakeForm();
      state.queueFilters.project_id = activeProjectId();
      state.queueFilters.repo_id = activeRepoId();
      if (byId("filter-project-id")) {
        byId("filter-project-id").value = activeProjectId();
      }
      if (byId("filter-repo-id")) {
        byId("filter-repo-id").value = activeRepoId();
      }
      await loadQueue();
      await refreshSummaryAndReport();
      setMessage("intake-message", `Created local queue item ${payload.item_id} for the active project. Continue in Queue lifecycle controls when ready.`, "success");
    } catch (error) {
      renderActiveProjectIntakeResult((error && error.payload) || null);
      setMessage("intake-message", String(error.message || error), "error");
    } finally {
      if (intakeSubmit) {
        intakeSubmit.disabled = false;
        intakeSubmit.textContent = originalIntakeSubmitLabel || "Create Local Queue Item";
      }
    }
  });

  on("new-project-wizard-form", "submit", async (event) => {
    event.preventDefault();
    const submitButton = byId("new-project-wizard-submit");
    const originalLabel = submitButton ? submitButton.textContent : "";
    try {
      if (submitButton) {
        submitButton.disabled = true;
        submitButton.textContent = "Creating...";
      }
      setMessage("projects-message", "Creating local project-factory start...", "loading");
      const payload = await fetchJson("/api/project-factory/new-project", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildNewProjectWizardPayload()),
      });
      await loadProjects();
      await loadProjectFactoryDossier(payload.active_project_id || activeProjectId());
      await loadScopePackage(payload.active_project_id || activeProjectId());
      await loadArchitectureContract(payload.active_project_id || activeProjectId());
      await loadMilestoneIssuePlan(payload.active_project_id || activeProjectId());
      applyActiveProjectDefaultsToQueueForm();
      await loadQueue();
      await refreshSummaryAndReport();
      setMessage("projects-message", `Local-only project wizard completed for ${payload.active_project_id}.`, "success");
    } catch (error) {
      setMessage("projects-message", String(error.message || error), "error");
    } finally {
      if (submitButton) {
        submitButton.disabled = false;
        submitButton.textContent = originalLabel || "Create Local Project Factory Start";
      }
    }
  });

  on("agent-form", "submit", async (event) => {
    event.preventDefault();
    try {
      setMessage("agents-message", "Saving agent...", "loading");
      await fetchJson("/api/agents", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildAgentPayload()),
      });
      await loadAgents();
      await refreshSummaryAndReport();
      setMessage("agents-message", "Agent saved.", "success");
    } catch (error) {
      setMessage("agents-message", String(error.message || error), "error");
    }
  });

  on("handoff-target-form", "submit", async (event) => {
    event.preventDefault();
    try {
      setMessage("agents-message", "Saving handoff target...", "loading");
      await fetchJson("/api/handoff-targets", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildHandoffTargetPayload()),
      });
      await loadHandoffTargets();
      await refreshSummaryAndReport();
      setMessage("agents-message", "Handoff target saved.", "success");
    } catch (error) {
      setMessage("agents-message", String(error.message || error), "error");
    }
  });

  on("handoff-refresh", "click", async () => {
    try {
      await loadHandoffPreview();
    } catch (error) {
      setMessage("handoff-message", String(error.message || error), "error");
    }
  });

  on("local-project-handoff-form", "submit", async (event) => {
    event.preventDefault();
    try {
      setMessage("handoff-message", "Generating local project handoff...", "loading");
      const payload = await fetchJson("/api/local-project/handoff", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildLocalProjectHandoffPayload()),
      });
      renderLocalProjectHandoffResult(payload);
      setMessage("handoff-message", payload.warnings && payload.warnings.length ? payload.warnings.join(" | ") : "Local project handoff generated.", payload.warnings && payload.warnings.length ? "warn" : "success");
    } catch (error) {
      renderLocalProjectHandoffResult((error && error.payload) || null);
      setMessage("handoff-message", String(error.message || error), "error");
    }
  });

  on("home-refresh-execution-readiness", "click", async () => {
    try {
      await loadExecutionReadiness(activeProjectId());
      setMessage("projects-message", "Execution readiness refreshed.", "success");
    } catch (error) {
      setMessage("projects-message", String(error.message || error), "error");
    }
  });

  on("projects-focus-new-project-wizard", "click", () => {
    focusNewProjectWizard();
  });

  on("bootstrap-refresh-status", "click", async () => {
    try {
      await loadBootstrapStatus();
      await refreshSummaryAndReport();
    } catch (error) {
      setMessage("bootstrap-message", String(error.message || error), "error");
    }
  });

  on("bootstrap-refresh-plan", "click", async () => {
    try {
      await loadBootstrapPlan();
    } catch (error) {
      setMessage("bootstrap-message", String(error.message || error), "error");
    }
  });

  on("bootstrap-apply", "click", async () => {
    try {
      await applyBootstrap();
      await loadBootstrapStatus();
      await loadBootstrapPlan();
      await loadProjects();
      await loadQueue();
      await loadAgents();
      await loadHandoffTargets();
      await refreshSummaryAndReport();
    } catch (error) {
      setMessage("bootstrap-message", String(error.message || error), "error");
    }
  });

  on("home-prepare-github-apply-plan", "click", async () => {
    try {
      setMessage("projects-message", "Preparing local GitHub apply plan placeholder...", "loading");
      await prepareGithubApplyPlan();
      await loadGithubApplyPlan(activeProjectId());
      await loadAgentDispatchPlan(activeProjectId());
      await loadValidationExecutionPlan(activeProjectId());
      await loadDocumentationCloseoutPlan(activeProjectId());
      await loadProjectFactoryDossier(activeProjectId());
      await refreshSummaryAndReport();
      setMessage("projects-message", "GitHub apply plan prepared locally.", "success");
    } catch (error) {
      setMessage("projects-message", String(error.message || error), "error");
    }
  });

  on("github-apply-plan-save-draft", "click", async () => {
    try {
      setMessage("projects-message", "Saving local GitHub apply plan draft...", "loading");
      await saveGithubApplyPlanDraft();
      await loadGithubApplyPlan(activeProjectId());
      await loadAgentDispatchPlan(activeProjectId());
      await loadValidationExecutionPlan(activeProjectId());
      await loadDocumentationCloseoutPlan(activeProjectId());
      await loadProjectFactoryDossier(activeProjectId());
      await refreshSummaryAndReport();
      setMessage("projects-message", "GitHub apply plan draft saved.", "success");
    } catch (error) {
      setMessage("projects-message", String(error.message || error), "error");
    }
  });

  on("github-apply-plan-approve", "click", async () => {
    try {
      setMessage("projects-message", "Approving local GitHub apply plan...", "loading");
      await approveGithubApplyPlan();
      await loadGithubApplyPlan(activeProjectId());
      await loadAgentDispatchPlan(activeProjectId());
      await loadValidationExecutionPlan(activeProjectId());
      await loadDocumentationCloseoutPlan(activeProjectId());
      await loadProjectFactoryDossier(activeProjectId());
      await refreshSummaryAndReport();
      setMessage("projects-message", "GitHub apply plan approved.", "success");
    } catch (error) {
      setMessage("projects-message", String(error.message || error), "error");
    }
  });

}

async function init() {
  bindNavigation();
  bindHomeQuickNavActions({ activateSection });
  bindForms();
  bindProjectFactoryScopeActions({
    activeProjectId,
    prepareScopePackageForState: prepareScopePackage,
    saveScopeDraftForState: saveScopeDraft,
    approveScopeForState: approveScope,
    loadProjectFactoryDossier,
    loadScopePackageForState: loadScopePackage,
    loadArchitectureContractForState: loadArchitectureContract,
    refreshSummaryAndReport,
  });
  bindProjectFactoryArchitectureActions({
    activeProjectId,
    prepareArchitectureContractForState: prepareArchitectureContract,
    saveArchitectureDraftForState: saveArchitectureDraft,
    approveArchitectureForState: approveArchitecture,
    loadArchitectureContractForState: loadArchitectureContract,
    loadProjectFactoryDossier,
    loadMilestoneIssuePlan,
    loadGithubApplyPlan,
    refreshSummaryAndReport,
  });
  bindProjectFactoryMilestonePlanActions({
    activeProjectId,
    prepareMilestoneIssuePlanForState: prepareMilestoneIssuePlan,
    saveMilestoneIssuePlanDraftForState: saveMilestoneIssuePlanDraft,
    approveMilestoneIssuePlanForState: approveMilestoneIssuePlan,
    loadMilestoneIssuePlanForState: loadMilestoneIssuePlan,
    loadGithubApplyPlan,
    loadProjectFactoryDossier,
    refreshSummaryAndReport,
  });
  bindProjectFactoryValidationActions({
    activeProjectId,
    prepareValidationExecutionPlanForState: prepareValidationExecutionPlan,
    saveValidationExecutionPlanDraftForState: saveValidationExecutionPlanDraft,
    approveValidationExecutionPlanForState: approveValidationExecutionPlan,
    loadValidationExecutionPlanForState: loadValidationExecutionPlan,
    loadDocumentationCloseoutPlan,
    loadProjectFactoryDossier,
    refreshSummaryAndReport,
  });
  bindProjectFactoryAgentDispatchActions({
    activeProjectId,
    prepareAgentDispatchPlanForState: prepareAgentDispatchPlan,
    saveAgentDispatchPlanDraftForState: saveAgentDispatchPlanDraft,
    approveAgentDispatchPlanForState: approveAgentDispatchPlan,
    loadAgentDispatchPlanForState: loadAgentDispatchPlan,
    loadValidationExecutionPlan,
    loadDocumentationCloseoutPlan,
    loadProjectFactoryDossier,
    refreshSummaryAndReport,
  });
  bindProjectFactoryCloseoutActions({
    activeProjectId,
    prepareDocumentationCloseoutPlanForState: prepareDocumentationCloseoutPlan,
    saveDocumentationCloseoutPlanDraftForState: saveDocumentationCloseoutPlanDraft,
    approveDocumentationCloseoutPlanForState: approveDocumentationCloseoutPlan,
    loadDocumentationCloseoutPlanForState: loadDocumentationCloseoutPlan,
    loadProjectFactoryDossier,
    refreshSummaryAndReport,
  });
  bindProjectFactoryExecutionApprovalActions({
    activeProjectId,
    prepareExecutionPhaseApprovalForState: prepareExecutionPhaseApproval,
    saveExecutionPhaseApprovalDraftForState: saveExecutionPhaseApprovalDraft,
    approveExecutionPhaseApprovalForState: approveExecutionPhaseApproval,
    loadExecutionPhaseApprovalForState: loadExecutionPhaseApproval,
    loadExecutionReadinessForState: loadExecutionReadiness,
    loadProjectFactoryDossier,
    refreshSummaryAndReport,
  });
  bindProjectsActions({
    parseCommaList,
    reloadProjects: loadProjects,
    refreshSummaryAndReport,
    loadReposForSelectedProject,
    setActiveProject,
    activeProjectId,
    loadProjectFactoryDossier,
    loadScopePackage,
    loadArchitectureContract,
    applyActiveProjectDefaultsToQueueForm,
  });
  bindQueueActions({
    state,
    loadQueueData: loadQueue,
    applyActiveProjectDefaultsToQueueForm,
    activeProjectId,
    activeRepoId,
    buildQueuePayload,
    refreshSummaryAndReport,
  });
  bindQueueLifecycleActions({
    parseCommaList,
    parseLineList,
    loadQueueData: loadQueue,
    refreshSummaryAndReport,
  });
  bindReposActions({
    state,
    parseCommaList,
    reloadReposForSelectedProject: loadReposForSelectedProject,
    reloadProjects: loadProjects,
    refreshSummaryAndReport,
    inspectRepoGitHubLink,
  });
  bindReportsActions({
    refreshSummaryAndReport,
    copyExportTextForState: copyExportText,
    loadExportPreviewForState: loadExportPreview,
    loadHandoffPreview,
    loadOrchestrationPlan: loadOrchestrationPlanSection,
    loadEscalationPlan: loadEscalationPlanSection,
  });
  bindOrchestrationActions({
    loadOrchestrationPlanForState: loadOrchestrationPlanSection,
    refreshSummaryAndReport,
  });
  bindAutonomyActions({
    loadAutonomyControlCenterForState: loadAutonomyControlCenter,
  });
  bindGitHubSyncActions({
    loadGitHubSyncControlPanelForState: loadGitHubSyncControlPanel,
  });
  bindEscalationActions({
    loadEscalationPlanForState: loadEscalationPlanSection,
    refreshSummaryAndReport,
  });
  bindHomeActions({
    refreshSummaryAndReport,
    loadExecutionReadiness,
    activeProjectId,
    activateSection,
    activateQueueIntakeFocus,
    focusNewProjectWizard,
  });
  bindWorkspaceActions({
    refreshSummaryAndReport,
    loadWorkspaceData: () => loadWorkspace(state),
    activateQueueIntakeFocus,
    activateSection,
  });
  renderRepos([], true);

  try {
    await loadActiveProject();
    await refreshSummaryAndReport();
  } catch (error) {
    setMessage("reports-message", String(error.message || error), "error");
    setList("warnings-list", "warnings-empty-state", ["Hub report API is unavailable."]);
  }

  try {
    await loadBootstrapStatus();
    await loadBootstrapPlan();
  } catch (error) {
    setMessage("bootstrap-message", String(error.message || error), "error");
  }

  try {
    await loadProjects();
  } catch (error) {
    setMessage("projects-message", String(error.message || error), "error");
  }

  try {
    await loadScopePackage(activeProjectId());
  } catch (_error) {
    renderScopeAuthoring({ ok: true, scope_package_exists: false, scope_package: {} });
  }

  try {
    await loadArchitectureContract(activeProjectId());
  } catch (_error) {
    renderArchitectureAuthoring({ ok: true, architecture_contract_exists: false, architecture_contract: {} });
  }

  try {
    await loadMilestoneIssuePlan(activeProjectId());
  } catch (_error) {
    renderMilestoneIssuePlan({ ok: true, milestone_issue_plan_exists: false, milestone_issue_plan: {} });
  }
  try {
    await loadGithubApplyPlan(activeProjectId());
  } catch (_error) {
    renderGithubApplyPlan({ ok: true, github_apply_plan_exists: false, github_apply_plan: {} });
  }
  try {
    await loadAgentDispatchPlan(activeProjectId());
  } catch (_error) {
    renderAgentDispatchPlan({ ok: true, agent_dispatch_plan_exists: false, agent_dispatch_plan: {} });
  }
  try {
    await loadValidationExecutionPlan(activeProjectId());
  } catch (_error) {
    renderValidationExecutionPlan({ ok: true, validation_execution_plan_exists: false, validation_execution_plan: {} });
  }
  try {
    await loadDocumentationCloseoutPlan(activeProjectId());
  } catch (_error) {
    renderDocumentationCloseoutPlan({ ok: true, documentation_closeout_plan_exists: false, documentation_closeout_plan: {} });
  }
  try {
    await loadExecutionPhaseApproval(activeProjectId());
  } catch (_error) {
    renderExecutionPhaseApproval({ ok: true, execution_phase_approval_exists: false, execution_phase_approval: {} });
  }
  try {
    await loadExecutionReadiness(activeProjectId());
  } catch (_error) {
    renderExecutionReadiness({ ok: true, overall_status: "blocked", next_safe_action: "select_or_create_active_project", blockers: [], warnings: [], artifact_summary: {}, lane_summary: {} });
  }

  try {
    await loadQueue();
  } catch (error) {
    setMessage("queue-message", String(error.message || error), "error");
  }

  try {
    await loadAgents();
    await loadHandoffTargets();
  } catch (error) {
    setMessage("agents-message", String(error.message || error), "error");
  }

  try {
    await loadHandoffPreview();
  } catch (error) {
    setMessage("handoff-message", String(error.message || error), "error");
  }

  try {
    await loadOrchestrationPlanSection({}, false);
  } catch (error) {
    setMessage("orchestration-message", String(error.message || error), "error");
  }

  try {
    await loadAutonomyControlCenter();
  } catch (error) {
    setMessage("autonomy-message", String(error.message || error), "error");
  }

  try {
    await loadGitHubSyncControlPanel();
  } catch (error) {
    setMessage("github-sync-message", String(error.message || error), "error");
  }

  try {
    await loadEscalationPlanSection({}, false);
  } catch (error) {
    setMessage("escalation-message", String(error.message || error), "error");
  }

  try {
    await loadExportPreview("json");
  } catch (_error) {
    setCodeBlock("reports-export-content", "reports-export-content-empty", "");
  }

  await loadSettings();
}

init();
