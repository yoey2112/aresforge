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
  const payload = await fetchJson("/api/project-factory/scope-package", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(prunePayload({ project_id: activeProjectId() })),
  });
  return payload;
}

function buildScopeAuthoringPayload() {
  return prunePayload({
    project_id: activeProjectId(),
    requirements: parseLineList(byId("scope-requirements").value),
    constraints: parseLineList(byId("scope-constraints").value),
    assumptions: parseLineList(byId("scope-assumptions").value),
    acceptance_criteria: parseLineList(byId("scope-acceptance-criteria").value),
    risks: parseLineList(byId("scope-risks").value),
    out_of_scope: parseLineList(byId("scope-out-of-scope").value),
    stakeholders: parseLineList(byId("scope-stakeholders").value),
    notes: byId("scope-notes").value.trim(),
  });
}

function renderScopeAuthoring(payload) {
  state.scopePackage = payload || null;
  const message = byId("home-scope-authoring-message");
  const stateLine = byId("home-scope-authoring-state");
  const scopeExists = Boolean(payload && payload.scope_package_exists);
  const scopePackage = (payload && payload.scope_package) || {};
  if (!scopeExists) {
    byId("scope-requirements").value = "";
    byId("scope-constraints").value = "";
    byId("scope-assumptions").value = "";
    byId("scope-acceptance-criteria").value = "";
    byId("scope-risks").value = "";
    byId("scope-out-of-scope").value = "";
    byId("scope-stakeholders").value = "";
    byId("scope-notes").value = "";
    setList("home-scope-audit-trail", "home-scope-audit-trail-empty", []);
    if (message) {
      message.textContent = "No scope package found. Use Prepare Scope Package first for the active project.";
    }
    if (stateLine) {
      stateLine.textContent = "Scope lifecycle state: not_started";
    }
    return;
  }

  byId("scope-requirements").value = toTextareaList(scopePackage.requirements);
  byId("scope-constraints").value = toTextareaList(scopePackage.constraints);
  byId("scope-assumptions").value = toTextareaList(scopePackage.assumptions);
  byId("scope-acceptance-criteria").value = toTextareaList(scopePackage.acceptance_criteria);
  byId("scope-risks").value = toTextareaList(scopePackage.risks);
  byId("scope-out-of-scope").value = toTextareaList(scopePackage.out_of_scope);
  byId("scope-stakeholders").value = toTextareaList(scopePackage.stakeholders);
  byId("scope-notes").value = String(scopePackage.notes || "");
  setList(
    "home-scope-audit-trail",
    "home-scope-audit-trail-empty",
    (scopePackage.audit_trail || []).map((entry) => `${entry.timestamp || "-"} | ${entry.event_type || "-"} | state=${entry.lifecycle_state || "-"} | actor=${entry.actor || "-"}`)
  );
  if (message) {
    message.textContent = "Scope authoring is local-only. No GitHub or model execution is triggered.";
  }
  if (stateLine) {
    stateLine.textContent = `Scope lifecycle state: ${scopePackage.lifecycle_state || "not_started"}`;
  }
}

function buildArchitectureAuthoringPayload() {
  return prunePayload({
    project_id: activeProjectId(),
    architecture_summary: byId("architecture-summary").value.trim(),
    system_components: parseLineList(byId("architecture-system-components").value),
    data_model_notes: parseLineList(byId("architecture-data-model-notes").value),
    integration_points: parseLineList(byId("architecture-integration-points").value),
    security_considerations: parseLineList(byId("architecture-security-considerations").value),
    deployment_notes: parseLineList(byId("architecture-deployment-notes").value),
    testing_strategy: parseLineList(byId("architecture-testing-strategy").value),
    documentation_plan: parseLineList(byId("architecture-documentation-plan").value),
    open_questions: parseLineList(byId("architecture-open-questions").value),
    milestone_planning_notes: byId("architecture-milestone-planning-notes").value.trim(),
  });
}

function renderArchitectureAuthoring(payload) {
  state.architectureContract = payload || null;
  const message = byId("home-architecture-authoring-message");
  const stateLine = byId("home-architecture-authoring-state");
  const exists = Boolean(payload && payload.architecture_contract_exists);
  const contract = (payload && payload.architecture_contract) || {};
  if (!exists) {
    byId("architecture-summary").value = "";
    byId("architecture-system-components").value = "";
    byId("architecture-data-model-notes").value = "";
    byId("architecture-integration-points").value = "";
    byId("architecture-security-considerations").value = "";
    byId("architecture-deployment-notes").value = "";
    byId("architecture-testing-strategy").value = "";
    byId("architecture-documentation-plan").value = "";
    byId("architecture-open-questions").value = "";
    byId("architecture-milestone-planning-notes").value = "";
    setList("home-architecture-audit-trail", "home-architecture-audit-trail-empty", []);
    if (message) {
      message.textContent = "No architecture contract found. Approve scope first, then prepare architecture contract.";
    }
    if (stateLine) {
      stateLine.textContent = "Architecture lifecycle state: not_started";
    }
    return;
  }

  byId("architecture-summary").value = String(contract.architecture_summary || "");
  byId("architecture-system-components").value = toTextareaList(contract.system_components);
  byId("architecture-data-model-notes").value = toTextareaList(contract.data_model_notes);
  byId("architecture-integration-points").value = toTextareaList(contract.integration_points);
  byId("architecture-security-considerations").value = toTextareaList(contract.security_considerations);
  byId("architecture-deployment-notes").value = toTextareaList(contract.deployment_notes);
  byId("architecture-testing-strategy").value = toTextareaList(contract.testing_strategy);
  byId("architecture-documentation-plan").value = toTextareaList(contract.documentation_plan);
  byId("architecture-open-questions").value = toTextareaList(contract.open_questions);
  byId("architecture-milestone-planning-notes").value = String(contract.milestone_planning_notes || "");
  setList(
    "home-architecture-audit-trail",
    "home-architecture-audit-trail-empty",
    (contract.audit_trail || []).map((entry) => `${entry.timestamp || "-"} | ${entry.event_type || "-"} | state=${entry.lifecycle_state || "-"} | actor=${entry.actor || "-"}`)
  );
  if (message) {
    message.textContent = "Architecture authoring is local-only. No GitHub or model execution is triggered.";
  }
  if (stateLine) {
    stateLine.textContent = `Architecture lifecycle state: ${contract.lifecycle_state || "not_started"}`;
  }
}

function _parseJsonArray(text, fieldName) {
  const raw = String(text || "").trim();
  if (!raw) {
    return [];
  }
  let decoded;
  try {
    decoded = JSON.parse(raw);
  } catch (_error) {
    throw new Error(`${fieldName} must be valid JSON array.`);
  }
  if (!Array.isArray(decoded)) {
    throw new Error(`${fieldName} must be a JSON array.`);
  }
  return decoded;
}

function buildMilestoneIssuePlanPayload() {
  return prunePayload({
    project_id: activeProjectId(),
    planning_summary: byId("milestone-plan-summary").value.trim(),
    milestones: _parseJsonArray(byId("milestone-plan-milestones").value, "milestones"),
    issues: _parseJsonArray(byId("milestone-plan-issues").value, "issues"),
    cross_cutting_tasks: parseLineList(byId("milestone-plan-cross-cutting-tasks").value),
    validation_plan: parseLineList(byId("milestone-plan-validation-plan").value),
    documentation_plan: parseLineList(byId("milestone-plan-documentation-plan").value),
    release_notes: parseLineList(byId("milestone-plan-release-notes").value),
    open_questions: parseLineList(byId("milestone-plan-open-questions").value),
    github_apply_notes: byId("milestone-plan-github-apply-notes").value.trim(),
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
  return prunePayload({
    project_id: activeProjectId(),
    dispatch_summary: byId("agent-dispatch-summary").value.trim(),
    operator_notes: byId("agent-dispatch-operator-notes").value.trim(),
    sequencing_notes: parseLineList(byId("agent-dispatch-sequencing-notes").value),
    dependency_notes: parseLineList(byId("agent-dispatch-dependency-notes").value),
    approval_conditions: parseLineList(byId("agent-dispatch-approval-conditions").value),
    known_risks: parseLineList(byId("agent-dispatch-known-risks").value),
  });
}

function buildValidationExecutionPlanPayload() {
  return prunePayload({
    project_id: activeProjectId(),
    validation_summary: byId("validation-execution-summary").value.trim(),
    operator_notes: byId("validation-execution-operator-notes").value.trim(),
    sequencing_notes: parseLineList(byId("validation-execution-sequencing-notes").value),
    dependency_notes: parseLineList(byId("validation-execution-dependency-notes").value),
    approval_conditions: parseLineList(byId("validation-execution-approval-conditions").value),
    known_risks: parseLineList(byId("validation-execution-known-risks").value),
    manual_validation_notes: parseLineList(byId("validation-execution-manual-notes").value),
  });
}

function buildDocumentationCloseoutPlanPayload() {
  return prunePayload({
    project_id: activeProjectId(),
    closeout_summary: byId("documentation-closeout-summary").value.trim(),
    operator_notes: byId("documentation-closeout-operator-notes").value.trim(),
    sequencing_notes: parseLineList(byId("documentation-closeout-sequencing-notes").value),
    dependency_notes: parseLineList(byId("documentation-closeout-dependency-notes").value),
    approval_conditions: parseLineList(byId("documentation-closeout-approval-conditions").value),
    known_risks: parseLineList(byId("documentation-closeout-known-risks").value),
    documentation_update_notes: parseLineList(byId("documentation-closeout-update-notes").value),
    evidence_collection_notes: parseLineList(byId("documentation-closeout-evidence-notes").value),
  });
}

function buildExecutionPhaseApprovalPayload() {
  const laneFromField = (laneId, fieldId) => {
    const acknowledgementText = byId(fieldId).value.trim();
    return {
      lane_id: laneId,
      status: acknowledgementText ? "approved" : "blocked",
      acknowledgement_text: acknowledgementText,
    };
  };
  return prunePayload({
    project_id: activeProjectId(),
    approval_summary: byId("execution-phase-approval-summary").value.trim(),
    operator_notes: byId("execution-phase-approval-operator-notes").value.trim(),
    overall_acknowledgement: byId("execution-phase-overall-acknowledgement").value.trim(),
    execution_lanes: [
      laneFromField("github_mutation_execution", "execution-phase-ack-github-mutation-execution"),
      laneFromField("validation_command_execution", "execution-phase-ack-validation-command-execution"),
      laneFromField("documentation_update_execution", "execution-phase-ack-documentation-update-execution"),
      laneFromField("agent_model_execution", "execution-phase-ack-agent-model-execution"),
      laneFromField("project_closeout_execution", "execution-phase-ack-project-closeout-execution"),
    ],
  });
}

function renderMilestoneIssuePlan(payload) {
  state.milestoneIssuePlan = payload || null;
  const message = byId("home-milestone-plan-message");
  const stateLine = byId("home-milestone-plan-state");
  const exists = Boolean(payload && payload.milestone_issue_plan_exists);
  const plan = (payload && payload.milestone_issue_plan) || {};
  if (!exists) {
    byId("milestone-plan-summary").value = "";
    byId("milestone-plan-milestones").value = "";
    byId("milestone-plan-issues").value = "";
    byId("milestone-plan-cross-cutting-tasks").value = "";
    byId("milestone-plan-validation-plan").value = "";
    byId("milestone-plan-documentation-plan").value = "";
    byId("milestone-plan-release-notes").value = "";
    byId("milestone-plan-open-questions").value = "";
    byId("milestone-plan-github-apply-notes").value = "";
    setList("home-milestone-plan-audit-trail", "home-milestone-plan-audit-trail-empty", []);
    if (message) {
      message.textContent = "No milestone/issue plan found. Approve architecture first, then prepare milestone/issue plan.";
    }
    if (stateLine) {
      stateLine.textContent = "Milestone/Issue Plan lifecycle state: not_started";
    }
    return;
  }
  byId("milestone-plan-summary").value = String(plan.planning_summary || "");
  byId("milestone-plan-milestones").value = JSON.stringify(Array.isArray(plan.milestones) ? plan.milestones : [], null, 2);
  byId("milestone-plan-issues").value = JSON.stringify(Array.isArray(plan.issues) ? plan.issues : [], null, 2);
  byId("milestone-plan-cross-cutting-tasks").value = toTextareaList(plan.cross_cutting_tasks);
  byId("milestone-plan-validation-plan").value = toTextareaList(plan.validation_plan);
  byId("milestone-plan-documentation-plan").value = toTextareaList(plan.documentation_plan);
  byId("milestone-plan-release-notes").value = toTextareaList(plan.release_notes);
  byId("milestone-plan-open-questions").value = toTextareaList(plan.open_questions);
  byId("milestone-plan-github-apply-notes").value = String(plan.github_apply_notes || "");
  setList(
    "home-milestone-plan-audit-trail",
    "home-milestone-plan-audit-trail-empty",
    (plan.audit_trail || []).map((entry) => `${entry.timestamp || "-"} | ${entry.event_type || "-"} | state=${entry.lifecycle_state || "-"} | actor=${entry.actor || "-"}`)
  );
  if (message) {
    message.textContent = "Milestone/issue planning is local-only. No GitHub or model execution is triggered.";
  }
  if (stateLine) {
    stateLine.textContent = `Milestone/Issue Plan lifecycle state: ${plan.lifecycle_state || "not_started"}`;
  }
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
  state.agentDispatchPlan = payload || null;
  const message = byId("home-agent-dispatch-plan-message");
  const stateLine = byId("home-agent-dispatch-plan-state");
  const statusLine = byId("home-agent-dispatch-plan-status");
  const exists = Boolean(payload && payload.agent_dispatch_plan_exists);
  const plan = (payload && payload.agent_dispatch_plan) || {};
  if (!exists) {
    byId("agent-dispatch-summary").value = "";
    byId("agent-dispatch-operator-notes").value = "";
    byId("agent-dispatch-sequencing-notes").value = "";
    byId("agent-dispatch-dependency-notes").value = "";
    byId("agent-dispatch-approval-conditions").value = "";
    byId("agent-dispatch-known-risks").value = "";
    setCodeBlock("home-agent-dispatch-items", "home-agent-dispatch-items-empty", "");
    setCodeBlock("home-agent-dispatch-queues", "home-agent-dispatch-queues-empty", "");
    setList("home-agent-dispatch-audit-trail", "home-agent-dispatch-audit-trail-empty", []);
    if (message) {
      message.textContent = "No Agent Dispatch Plan found. Approve the local GitHub Apply Plan first, then prepare Agent Dispatch Plan.";
    }
    if (stateLine) {
      stateLine.textContent = "Agent Dispatch Plan lifecycle state: not_started";
    }
    if (statusLine) {
      statusLine.textContent = "agent_execution=not_requested | model_execution=not_requested";
    }
    return;
  }
  byId("agent-dispatch-summary").value = String(plan.dispatch_summary || "");
  byId("agent-dispatch-operator-notes").value = String(plan.operator_notes || "");
  byId("agent-dispatch-sequencing-notes").value = toTextareaList(plan.sequencing_notes);
  byId("agent-dispatch-dependency-notes").value = toTextareaList(plan.dependency_notes);
  byId("agent-dispatch-approval-conditions").value = toTextareaList(plan.approval_conditions);
  byId("agent-dispatch-known-risks").value = toTextareaList(plan.known_risks);
  const dispatchPlan = plan.dispatch_plan || {};
  setCodeBlock("home-agent-dispatch-items", "home-agent-dispatch-items-empty", JSON.stringify(dispatchPlan.dispatch_items || [], null, 2));
  setCodeBlock("home-agent-dispatch-queues", "home-agent-dispatch-queues-empty", JSON.stringify(dispatchPlan.agent_queues || [], null, 2));
  setList(
    "home-agent-dispatch-audit-trail",
    "home-agent-dispatch-audit-trail-empty",
    (plan.audit_trail || []).map((entry) => `${entry.timestamp || "-"} | ${entry.event_type || "-"} | state=${entry.lifecycle_state || "-"} | actor=${entry.actor || "-"}`)
  );
  if (message) {
    message.textContent = "This is a local dispatch plan only. It does not execute agents or models.";
  }
  if (stateLine) {
    stateLine.textContent = `Agent Dispatch Plan lifecycle state: ${plan.lifecycle_state || "not_started"}`;
  }
  if (statusLine) {
    statusLine.textContent = `agent_execution=${plan.agent_execution_status || "not_requested"} | model_execution=${plan.model_execution_status || "not_requested"}`;
  }
}

function renderValidationExecutionPlan(payload) {
  state.validationExecutionPlan = payload || null;
  const message = byId("home-validation-execution-plan-message");
  const stateLine = byId("home-validation-execution-plan-state");
  const statusLine = byId("home-validation-execution-plan-status");
  const exists = Boolean(payload && payload.validation_execution_plan_exists);
  const plan = (payload && payload.validation_execution_plan) || {};
  if (!exists) {
    byId("validation-execution-summary").value = "";
    byId("validation-execution-operator-notes").value = "";
    byId("validation-execution-sequencing-notes").value = "";
    byId("validation-execution-dependency-notes").value = "";
    byId("validation-execution-approval-conditions").value = "";
    byId("validation-execution-known-risks").value = "";
    byId("validation-execution-manual-notes").value = "";
    setCodeBlock("home-validation-execution-items", "home-validation-execution-items-empty", "");
    setCodeBlock("home-validation-execution-groups", "home-validation-execution-groups-empty", "");
    setCodeBlock("home-validation-execution-evidence", "home-validation-execution-evidence-empty", "");
    setList("home-validation-execution-audit-trail", "home-validation-execution-audit-trail-empty", []);
    if (message) {
      message.textContent = "No Validation Execution Plan found. Approve the local Agent Dispatch Plan first, then prepare Validation Execution Plan.";
    }
    if (stateLine) {
      stateLine.textContent = "Validation Execution Plan lifecycle state: not_started";
    }
    if (statusLine) {
      statusLine.textContent = "validation_execution=not_requested | agent_execution=not_requested | model_execution=not_requested";
    }
    return;
  }
  byId("validation-execution-summary").value = String(plan.validation_summary || "");
  byId("validation-execution-operator-notes").value = String(plan.operator_notes || "");
  byId("validation-execution-sequencing-notes").value = toTextareaList(plan.sequencing_notes);
  byId("validation-execution-dependency-notes").value = toTextareaList(plan.dependency_notes);
  byId("validation-execution-approval-conditions").value = toTextareaList(plan.approval_conditions);
  byId("validation-execution-known-risks").value = toTextareaList(plan.known_risks);
  byId("validation-execution-manual-notes").value = toTextareaList(plan.manual_validation_notes);
  const validationPlan = plan.validation_plan || {};
  setCodeBlock("home-validation-execution-items", "home-validation-execution-items-empty", JSON.stringify(validationPlan.validation_items || [], null, 2));
  setCodeBlock("home-validation-execution-groups", "home-validation-execution-groups-empty", JSON.stringify(validationPlan.validation_groups || [], null, 2));
  setCodeBlock("home-validation-execution-evidence", "home-validation-execution-evidence-empty", JSON.stringify(validationPlan.evidence_expectations || [], null, 2));
  setList(
    "home-validation-execution-audit-trail",
    "home-validation-execution-audit-trail-empty",
    (plan.audit_trail || []).map((entry) => `${entry.timestamp || "-"} | ${entry.event_type || "-"} | state=${entry.lifecycle_state || "-"} | actor=${entry.actor || "-"}`)
  );
  if (message) {
    message.textContent = "This is a local validation plan only. It does not execute validation commands, agents, models, or GitHub actions.";
  }
  if (stateLine) {
    stateLine.textContent = `Validation Execution Plan lifecycle state: ${plan.lifecycle_state || "not_started"}`;
  }
  if (statusLine) {
    statusLine.textContent = `validation_execution=${plan.validation_execution_status || "not_requested"} | agent_execution=${plan.agent_execution_status || "not_requested"} | model_execution=${plan.model_execution_status || "not_requested"}`;
  }
}

function renderDocumentationCloseoutPlan(payload) {
  state.documentationCloseoutPlan = payload || null;
  const message = byId("home-documentation-closeout-plan-message");
  const stateLine = byId("home-documentation-closeout-plan-state");
  const statusLine = byId("home-documentation-closeout-plan-status");
  const exists = Boolean(payload && payload.documentation_closeout_plan_exists);
  const plan = (payload && payload.documentation_closeout_plan) || {};
  if (!exists) {
    byId("documentation-closeout-summary").value = "";
    byId("documentation-closeout-operator-notes").value = "";
    byId("documentation-closeout-sequencing-notes").value = "";
    byId("documentation-closeout-dependency-notes").value = "";
    byId("documentation-closeout-approval-conditions").value = "";
    byId("documentation-closeout-known-risks").value = "";
    byId("documentation-closeout-update-notes").value = "";
    byId("documentation-closeout-evidence-notes").value = "";
    setCodeBlock("home-documentation-closeout-items", "home-documentation-closeout-items-empty", "");
    setCodeBlock("home-documentation-closeout-evidence-packages", "home-documentation-closeout-evidence-packages-empty", "");
    setCodeBlock("home-documentation-closeout-checks", "home-documentation-closeout-checks-empty", "");
    setList("home-documentation-closeout-audit-trail", "home-documentation-closeout-audit-trail-empty", []);
    if (message) {
      message.textContent = "No Documentation Closeout Plan found. Approve the local Validation Execution Plan first.";
    }
    if (stateLine) {
      stateLine.textContent = "Documentation Closeout Plan lifecycle state: not_started";
    }
    if (statusLine) {
      statusLine.textContent = "documentation_execution=not_requested | validation_execution=not_requested | agent_execution=not_requested | model_execution=not_requested";
    }
    return;
  }
  byId("documentation-closeout-summary").value = String(plan.closeout_summary || "");
  byId("documentation-closeout-operator-notes").value = String(plan.operator_notes || "");
  byId("documentation-closeout-sequencing-notes").value = toTextareaList(plan.sequencing_notes);
  byId("documentation-closeout-dependency-notes").value = toTextareaList(plan.dependency_notes);
  byId("documentation-closeout-approval-conditions").value = toTextareaList(plan.approval_conditions);
  byId("documentation-closeout-known-risks").value = toTextareaList(plan.known_risks);
  byId("documentation-closeout-update-notes").value = toTextareaList(plan.documentation_update_notes);
  byId("documentation-closeout-evidence-notes").value = toTextareaList(plan.evidence_collection_notes);
  const closeoutPlan = plan.documentation_plan || {};
  setCodeBlock("home-documentation-closeout-items", "home-documentation-closeout-items-empty", JSON.stringify(closeoutPlan.documentation_items || [], null, 2));
  setCodeBlock("home-documentation-closeout-evidence-packages", "home-documentation-closeout-evidence-packages-empty", JSON.stringify(closeoutPlan.evidence_packages || [], null, 2));
  setCodeBlock("home-documentation-closeout-checks", "home-documentation-closeout-checks-empty", JSON.stringify(closeoutPlan.closeout_checks || [], null, 2));
  setList(
    "home-documentation-closeout-audit-trail",
    "home-documentation-closeout-audit-trail-empty",
    (plan.audit_trail || []).map((entry) => `${entry.timestamp || "-"} | ${entry.event_type || "-"} | state=${entry.lifecycle_state || "-"} | actor=${entry.actor || "-"}`)
  );
  if (message) {
    message.textContent = "This is a local documentation closeout plan only. It does not update docs, execute validation, run agents/models, or perform GitHub actions.";
  }
  if (stateLine) {
    stateLine.textContent = `Documentation Closeout Plan lifecycle state: ${plan.lifecycle_state || "not_started"}`;
  }
  if (statusLine) {
    statusLine.textContent = `documentation_execution=${plan.documentation_execution_status || "not_requested"} | validation_execution=${plan.validation_execution_status || "not_requested"} | agent_execution=${plan.agent_execution_status || "not_requested"} | model_execution=${plan.model_execution_status || "not_requested"}`;
  }
}

function renderExecutionPhaseApproval(payload) {
  state.executionPhaseApproval = payload || null;
  const message = byId("home-execution-phase-approval-message");
  const stateLine = byId("home-execution-phase-approval-state");
  const exists = Boolean(payload && payload.execution_phase_approval_exists);
  const plan = (payload && payload.execution_phase_approval) || {};
  if (!exists) {
    byId("execution-phase-approval-summary").value = "";
    byId("execution-phase-approval-operator-notes").value = "";
    byId("execution-phase-overall-acknowledgement").value = "";
    byId("execution-phase-ack-github-mutation-execution").value = "";
    byId("execution-phase-ack-validation-command-execution").value = "";
    byId("execution-phase-ack-documentation-update-execution").value = "";
    byId("execution-phase-ack-agent-model-execution").value = "";
    byId("execution-phase-ack-project-closeout-execution").value = "";
    setCodeBlock("home-execution-phase-lanes", "home-execution-phase-lanes-empty", "");
    setList("home-execution-phase-audit-trail", "home-execution-phase-audit-trail-empty", []);
    if (message) {
      message.textContent = "No Execution Phase Approval found. Approve the local Documentation Closeout Plan first.";
    }
    if (stateLine) {
      stateLine.textContent = "Execution Phase Approval lifecycle state: not_started";
    }
    return;
  }
  byId("execution-phase-approval-summary").value = String(plan.approval_summary || "");
  byId("execution-phase-approval-operator-notes").value = String(plan.operator_notes || "");
  byId("execution-phase-overall-acknowledgement").value = String(plan.overall_acknowledgement || "");
  const lanes = Array.isArray(plan.execution_lanes) ? plan.execution_lanes : [];
  const laneMap = {};
  lanes.forEach((lane) => {
    laneMap[String(lane.lane_id || "")] = lane;
  });
  byId("execution-phase-ack-github-mutation-execution").value = String((laneMap.github_mutation_execution || {}).acknowledgement_text || "");
  byId("execution-phase-ack-validation-command-execution").value = String((laneMap.validation_command_execution || {}).acknowledgement_text || "");
  byId("execution-phase-ack-documentation-update-execution").value = String((laneMap.documentation_update_execution || {}).acknowledgement_text || "");
  byId("execution-phase-ack-agent-model-execution").value = String((laneMap.agent_model_execution || {}).acknowledgement_text || "");
  byId("execution-phase-ack-project-closeout-execution").value = String((laneMap.project_closeout_execution || {}).acknowledgement_text || "");
  setCodeBlock("home-execution-phase-lanes", "home-execution-phase-lanes-empty", JSON.stringify(lanes, null, 2));
  setList(
    "home-execution-phase-audit-trail",
    "home-execution-phase-audit-trail-empty",
    (plan.audit_trail || []).map((entry) => `${entry.timestamp || "-"} | ${entry.event_type || "-"} | state=${entry.lifecycle_state || "-"} | actor=${entry.actor || "-"}`)
  );
  if (message) {
    message.textContent = "This is a local execution approval gate only. It does not execute GitHub mutations, validation commands, documentation updates, agents/models, or closeout.";
  }
  if (stateLine) {
    stateLine.textContent = `Execution Phase Approval lifecycle state: ${plan.lifecycle_state || "not_started"}`;
  }
}

function renderExecutionReadiness(payload) {
  state.executionReadiness = payload || null;
  const statusLine = byId("home-execution-readiness-overall-status");
  const nextActionLine = byId("home-execution-readiness-next-safe-action");
  const overallStatus = String((payload && payload.overall_status) || "blocked");
  const nextSafeAction = String((payload && payload.next_safe_action) || "select_or_create_active_project");
  if (statusLine) {
    statusLine.textContent = `overall_status: ${overallStatus}`;
  }
  if (nextActionLine) {
    nextActionLine.textContent = `next_safe_action: ${nextSafeAction}`;
  }
  setList("home-execution-readiness-blockers", "home-execution-readiness-blockers-empty", (payload && payload.blockers) || []);
  setList("home-execution-readiness-warnings", "home-execution-readiness-warnings-empty", (payload && payload.warnings) || []);
  const artifacts = (payload && payload.artifact_summary) || {};
  const artifactLines = Object.keys(artifacts).sort().map((key) => {
    const item = artifacts[key] || {};
    return `${key}: exists=${Boolean(item.exists)} approved=${Boolean(item.approved)} lifecycle=${item.lifecycle_state || "not_started"}`;
  });
  setList("home-execution-readiness-artifacts", "home-execution-readiness-artifacts-empty", artifactLines);
  const lanes = (payload && payload.lane_summary) || {};
  const laneLines = Object.keys(lanes).sort().map((key) => {
    const lane = lanes[key] || {};
    return `${key}: status=${lane.status || "blocked"} approved=${Boolean(lane.approved)} acknowledgement_present=${Boolean(lane.acknowledgement_present)}`;
  });
  setList("home-execution-readiness-lanes", "home-execution-readiness-lanes-empty", laneLines);
}

async function loadScopePackage(projectId) {
  const query = toQuery({ project_id: projectId || "" });
  const payload = await fetchJson(`/api/project-factory/scope-package${query}`, { method: "GET" });
  renderScopeAuthoring(payload);
  return payload;
}

async function loadArchitectureContract(projectId) {
  const query = toQuery({ project_id: projectId || "" });
  const payload = await fetchJson(`/api/project-factory/architecture-contract${query}`, { method: "GET" });
  renderArchitectureAuthoring(payload);
  return payload;
}

async function loadMilestoneIssuePlan(projectId) {
  const query = toQuery({ project_id: projectId || "" });
  const payload = await fetchJson(`/api/project-factory/milestone-issue-plan${query}`, { method: "GET" });
  renderMilestoneIssuePlan(payload);
  return payload;
}

async function loadGithubApplyPlan(projectId) {
  const query = toQuery({ project_id: projectId || "" });
  const payload = await fetchJson(`/api/project-factory/github-apply-plan${query}`, { method: "GET" });
  renderGithubApplyPlan(payload);
  return payload;
}

async function loadAgentDispatchPlan(projectId) {
  const query = toQuery({ project_id: projectId || "" });
  const payload = await fetchJson(`/api/project-factory/agent-dispatch-plan${query}`, { method: "GET" });
  renderAgentDispatchPlan(payload);
  return payload;
}

async function loadValidationExecutionPlan(projectId) {
  const query = toQuery({ project_id: projectId || "" });
  const payload = await fetchJson(`/api/project-factory/validation-execution-plan${query}`, { method: "GET" });
  renderValidationExecutionPlan(payload);
  return payload;
}

async function loadDocumentationCloseoutPlan(projectId) {
  const query = toQuery({ project_id: projectId || "" });
  const payload = await fetchJson(`/api/project-factory/documentation-closeout-plan${query}`, { method: "GET" });
  renderDocumentationCloseoutPlan(payload);
  return payload;
}

async function loadExecutionPhaseApproval(projectId) {
  const query = toQuery({ project_id: projectId || "" });
  const payload = await fetchJson(`/api/project-factory/execution-phase-approval${query}`, { method: "GET" });
  renderExecutionPhaseApproval(payload);
  return payload;
}

async function loadExecutionReadiness(projectId) {
  const query = toQuery({ project_id: projectId || "" });
  const payload = await fetchJson(`/api/project-factory/execution-readiness${query}`, { method: "GET" });
  renderExecutionReadiness(payload);
  return payload;
}

async function saveScopeDraft() {
  const payload = await fetchJson("/api/project-factory/scope-package", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(buildScopeAuthoringPayload()),
  });
  return payload;
}

async function approveScope() {
  const payload = await fetchJson("/api/project-factory/scope-package/approve", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(prunePayload({ project_id: activeProjectId() })),
  });
  return payload;
}

async function prepareArchitectureContract() {
  const payload = await fetchJson("/api/project-factory/architecture-contract", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(prunePayload({ project_id: activeProjectId() })),
  });
  return payload;
}

async function saveArchitectureDraft() {
  const payload = await fetchJson("/api/project-factory/architecture-contract", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(buildArchitectureAuthoringPayload()),
  });
  return payload;
}

async function approveArchitecture() {
  const payload = await fetchJson("/api/project-factory/architecture-contract/approve", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(prunePayload({ project_id: activeProjectId() })),
  });
  return payload;
}

async function prepareMilestoneIssuePlan() {
  const payload = await fetchJson("/api/project-factory/milestone-issue-plan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(prunePayload({ project_id: activeProjectId() })),
  });
  return payload;
}

async function saveMilestoneIssuePlanDraft() {
  const payload = await fetchJson("/api/project-factory/milestone-issue-plan", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(buildMilestoneIssuePlanPayload()),
  });
  return payload;
}

async function approveMilestoneIssuePlan() {
  const payload = await fetchJson("/api/project-factory/milestone-issue-plan/approve", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(prunePayload({ project_id: activeProjectId() })),
  });
  return payload;
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
  const payload = await fetchJson("/api/project-factory/agent-dispatch-plan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(prunePayload({ project_id: activeProjectId() })),
  });
  return payload;
}

async function saveAgentDispatchPlanDraft() {
  const payload = await fetchJson("/api/project-factory/agent-dispatch-plan", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(buildAgentDispatchPlanPayload()),
  });
  return payload;
}

async function approveAgentDispatchPlan() {
  const payload = await fetchJson("/api/project-factory/agent-dispatch-plan/approve", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(prunePayload({ project_id: activeProjectId() })),
  });
  return payload;
}

async function prepareValidationExecutionPlan() {
  const payload = await fetchJson("/api/project-factory/validation-execution-plan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(prunePayload({ project_id: activeProjectId() })),
  });
  return payload;
}

async function saveValidationExecutionPlanDraft() {
  const payload = await fetchJson("/api/project-factory/validation-execution-plan", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(buildValidationExecutionPlanPayload()),
  });
  return payload;
}

async function approveValidationExecutionPlan() {
  const payload = await fetchJson("/api/project-factory/validation-execution-plan/approve", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(prunePayload({ project_id: activeProjectId() })),
  });
  return payload;
}

async function prepareDocumentationCloseoutPlan() {
  const payload = await fetchJson("/api/project-factory/documentation-closeout-plan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(prunePayload({ project_id: activeProjectId() })),
  });
  return payload;
}

async function saveDocumentationCloseoutPlanDraft() {
  const payload = await fetchJson("/api/project-factory/documentation-closeout-plan", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(buildDocumentationCloseoutPlanPayload()),
  });
  return payload;
}

async function approveDocumentationCloseoutPlan() {
  const payload = await fetchJson("/api/project-factory/documentation-closeout-plan/approve", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(prunePayload({ project_id: activeProjectId() })),
  });
  return payload;
}

async function prepareExecutionPhaseApproval() {
  const payload = await fetchJson("/api/project-factory/execution-phase-approval", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(prunePayload({ project_id: activeProjectId() })),
  });
  return payload;
}

async function saveExecutionPhaseApprovalDraft() {
  const payload = await fetchJson("/api/project-factory/execution-phase-approval", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(buildExecutionPhaseApprovalPayload()),
  });
  return payload;
}

async function approveExecutionPhaseApproval() {
  const payload = await fetchJson("/api/project-factory/execution-phase-approval/approve", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(prunePayload({ project_id: activeProjectId() })),
  });
  return payload;
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
  ["intake-title", "intake-tags", "intake-description"].forEach((id) => {
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

  on("home-prepare-scope-package", "click", async () => {
    try {
      setMessage("projects-message", "Preparing local scope package placeholder...", "loading");
      await prepareScopePackage();
      await loadProjectFactoryDossier(activeProjectId());
      await loadScopePackage(activeProjectId());
      await refreshSummaryAndReport();
      setMessage("projects-message", "Scope package prepared locally.", "success");
    } catch (error) {
      setMessage("projects-message", String(error.message || error), "error");
    }
  });

  on("scope-save-draft", "click", async () => {
    try {
      setMessage("projects-message", "Saving local scope draft...", "loading");
      await saveScopeDraft();
      await loadScopePackage(activeProjectId());
      await loadProjectFactoryDossier(activeProjectId());
      await refreshSummaryAndReport();
      setMessage("projects-message", "Scope draft saved.", "success");
    } catch (error) {
      setMessage("projects-message", String(error.message || error), "error");
    }
  });

  on("scope-approve", "click", async () => {
    try {
      setMessage("projects-message", "Approving local scope package...", "loading");
      await approveScope();
      await loadScopePackage(activeProjectId());
      await loadProjectFactoryDossier(activeProjectId());
      await loadArchitectureContract(activeProjectId());
      await refreshSummaryAndReport();
      setMessage("projects-message", "Scope approved.", "success");
    } catch (error) {
      setMessage("projects-message", String(error.message || error), "error");
    }
  });

  on("home-prepare-architecture-contract", "click", async () => {
    try {
      setMessage("projects-message", "Preparing local architecture contract placeholder...", "loading");
      await prepareArchitectureContract();
      await loadArchitectureContract(activeProjectId());
      await loadProjectFactoryDossier(activeProjectId());
      await refreshSummaryAndReport();
      setMessage("projects-message", "Architecture contract prepared locally.", "success");
    } catch (error) {
      setMessage("projects-message", String(error.message || error), "error");
    }
  });

  on("architecture-save-draft", "click", async () => {
    try {
      setMessage("projects-message", "Saving local architecture draft...", "loading");
      await saveArchitectureDraft();
      await loadArchitectureContract(activeProjectId());
      await loadProjectFactoryDossier(activeProjectId());
      await refreshSummaryAndReport();
      setMessage("projects-message", "Architecture draft saved.", "success");
    } catch (error) {
      setMessage("projects-message", String(error.message || error), "error");
    }
  });

  on("architecture-approve", "click", async () => {
    try {
      setMessage("projects-message", "Approving local architecture contract...", "loading");
      await approveArchitecture();
      await loadArchitectureContract(activeProjectId());
      await loadProjectFactoryDossier(activeProjectId());
      await loadMilestoneIssuePlan(activeProjectId());
      await loadGithubApplyPlan(activeProjectId());
      await refreshSummaryAndReport();
      setMessage("projects-message", "Architecture approved.", "success");
    } catch (error) {
      setMessage("projects-message", String(error.message || error), "error");
    }
  });

  on("home-prepare-milestone-issue-plan", "click", async () => {
    try {
      setMessage("projects-message", "Preparing local milestone/issue plan placeholder...", "loading");
      await prepareMilestoneIssuePlan();
      await loadMilestoneIssuePlan(activeProjectId());
      await loadGithubApplyPlan(activeProjectId());
      await loadProjectFactoryDossier(activeProjectId());
      await refreshSummaryAndReport();
      setMessage("projects-message", "Milestone/issue plan prepared locally.", "success");
    } catch (error) {
      setMessage("projects-message", String(error.message || error), "error");
    }
  });

  on("milestone-plan-save-draft", "click", async () => {
    try {
      setMessage("projects-message", "Saving local milestone/issue plan draft...", "loading");
      await saveMilestoneIssuePlanDraft();
      await loadMilestoneIssuePlan(activeProjectId());
      await loadGithubApplyPlan(activeProjectId());
      await loadProjectFactoryDossier(activeProjectId());
      await refreshSummaryAndReport();
      setMessage("projects-message", "Milestone/issue plan draft saved.", "success");
    } catch (error) {
      setMessage("projects-message", String(error.message || error), "error");
    }
  });

  on("milestone-plan-approve", "click", async () => {
    try {
      setMessage("projects-message", "Approving local milestone/issue plan...", "loading");
      await approveMilestoneIssuePlan();
      await loadMilestoneIssuePlan(activeProjectId());
      await loadGithubApplyPlan(activeProjectId());
      await loadProjectFactoryDossier(activeProjectId());
      await refreshSummaryAndReport();
      setMessage("projects-message", "Milestone/issue plan approved.", "success");
    } catch (error) {
      setMessage("projects-message", String(error.message || error), "error");
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

  on("home-prepare-agent-dispatch-plan", "click", async () => {
    try {
      setMessage("projects-message", "Preparing local Agent Dispatch Plan...", "loading");
      await prepareAgentDispatchPlan();
      await loadAgentDispatchPlan(activeProjectId());
      await loadProjectFactoryDossier(activeProjectId());
      await refreshSummaryAndReport();
      setMessage("projects-message", "Agent dispatch plan prepared locally.", "success");
    } catch (error) {
      setMessage("projects-message", String(error.message || error), "error");
    }
  });

  on("agent-dispatch-plan-save-draft", "click", async () => {
    try {
      setMessage("projects-message", "Saving local Agent Dispatch Plan draft...", "loading");
      await saveAgentDispatchPlanDraft();
      await loadAgentDispatchPlan(activeProjectId());
      await loadProjectFactoryDossier(activeProjectId());
      await refreshSummaryAndReport();
      setMessage("projects-message", "Agent dispatch plan draft saved.", "success");
    } catch (error) {
      setMessage("projects-message", String(error.message || error), "error");
    }
  });

  on("agent-dispatch-plan-approve", "click", async () => {
    try {
      setMessage("projects-message", "Approving local Agent Dispatch Plan...", "loading");
      await approveAgentDispatchPlan();
      await loadAgentDispatchPlan(activeProjectId());
      await loadValidationExecutionPlan(activeProjectId());
      await loadDocumentationCloseoutPlan(activeProjectId());
      await loadProjectFactoryDossier(activeProjectId());
      await refreshSummaryAndReport();
      setMessage("projects-message", "Agent dispatch plan approved.", "success");
    } catch (error) {
      setMessage("projects-message", String(error.message || error), "error");
    }
  });

  on("home-prepare-validation-execution-plan", "click", async () => {
    try {
      setMessage("projects-message", "Preparing local Validation Execution Plan...", "loading");
      await prepareValidationExecutionPlan();
      await loadValidationExecutionPlan(activeProjectId());
      await loadDocumentationCloseoutPlan(activeProjectId());
      await loadProjectFactoryDossier(activeProjectId());
      await refreshSummaryAndReport();
      setMessage("projects-message", "Validation execution plan prepared locally.", "success");
    } catch (error) {
      setMessage("projects-message", String(error.message || error), "error");
    }
  });

  on("validation-execution-plan-save-draft", "click", async () => {
    try {
      setMessage("projects-message", "Saving local Validation Execution Plan draft...", "loading");
      await saveValidationExecutionPlanDraft();
      await loadValidationExecutionPlan(activeProjectId());
      await loadDocumentationCloseoutPlan(activeProjectId());
      await loadProjectFactoryDossier(activeProjectId());
      await refreshSummaryAndReport();
      setMessage("projects-message", "Validation execution plan draft saved.", "success");
    } catch (error) {
      setMessage("projects-message", String(error.message || error), "error");
    }
  });

  on("validation-execution-plan-approve", "click", async () => {
    try {
      setMessage("projects-message", "Approving local Validation Execution Plan...", "loading");
      await approveValidationExecutionPlan();
      await loadValidationExecutionPlan(activeProjectId());
      await loadDocumentationCloseoutPlan(activeProjectId());
      await loadProjectFactoryDossier(activeProjectId());
      await refreshSummaryAndReport();
      setMessage("projects-message", "Validation execution plan approved.", "success");
    } catch (error) {
      setMessage("projects-message", String(error.message || error), "error");
    }
  });

  on("home-prepare-documentation-closeout-plan", "click", async () => {
    try {
      setMessage("projects-message", "Preparing local Documentation Closeout Plan...", "loading");
      await prepareDocumentationCloseoutPlan();
      await loadDocumentationCloseoutPlan(activeProjectId());
      await loadProjectFactoryDossier(activeProjectId());
      await refreshSummaryAndReport();
      setMessage("projects-message", "Documentation closeout plan prepared locally.", "success");
    } catch (error) {
      setMessage("projects-message", String(error.message || error), "error");
    }
  });

  on("documentation-closeout-plan-save-draft", "click", async () => {
    try {
      setMessage("projects-message", "Saving local Documentation Closeout Plan draft...", "loading");
      await saveDocumentationCloseoutPlanDraft();
      await loadDocumentationCloseoutPlan(activeProjectId());
      await loadProjectFactoryDossier(activeProjectId());
      await refreshSummaryAndReport();
      setMessage("projects-message", "Documentation closeout plan draft saved.", "success");
    } catch (error) {
      setMessage("projects-message", String(error.message || error), "error");
    }
  });

  on("documentation-closeout-plan-approve", "click", async () => {
    try {
      setMessage("projects-message", "Approving local Documentation Closeout Plan...", "loading");
      await approveDocumentationCloseoutPlan();
      await loadDocumentationCloseoutPlan(activeProjectId());
      await loadProjectFactoryDossier(activeProjectId());
      await refreshSummaryAndReport();
      setMessage("projects-message", "Documentation closeout plan approved.", "success");
    } catch (error) {
      setMessage("projects-message", String(error.message || error), "error");
    }
  });
  on("home-prepare-execution-phase-approval", "click", async () => {
    try {
      setMessage("projects-message", "Preparing local Execution Phase Approval...", "loading");
      await prepareExecutionPhaseApproval();
      await loadExecutionPhaseApproval(activeProjectId());
      await loadProjectFactoryDossier(activeProjectId());
      await refreshSummaryAndReport();
      setMessage("projects-message", "Execution phase approval prepared locally.", "success");
    } catch (error) {
      setMessage("projects-message", String(error.message || error), "error");
    }
  });
  on("execution-phase-approval-save-draft", "click", async () => {
    try {
      setMessage("projects-message", "Saving local Execution Phase Approval draft...", "loading");
      await saveExecutionPhaseApprovalDraft();
      await loadExecutionPhaseApproval(activeProjectId());
      await loadProjectFactoryDossier(activeProjectId());
      await refreshSummaryAndReport();
      setMessage("projects-message", "Execution phase approval draft saved.", "success");
    } catch (error) {
      setMessage("projects-message", String(error.message || error), "error");
    }
  });
  on("execution-phase-approval-approve", "click", async () => {
    try {
      setMessage("projects-message", "Approving local Execution Phase Approval...", "loading");
      await approveExecutionPhaseApproval();
      await loadExecutionPhaseApproval(activeProjectId());
      await loadExecutionReadiness(activeProjectId());
      await loadProjectFactoryDossier(activeProjectId());
      await refreshSummaryAndReport();
      setMessage("projects-message", "Execution phase approval approved.", "success");
    } catch (error) {
      setMessage("projects-message", String(error.message || error), "error");
    }
  });
}

async function init() {
  bindNavigation();
  bindHomeQuickNavActions({ activateSection });
  bindForms();
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
