function byId(id) {
  return document.getElementById(id);
}

function on(id, eventName, handler) {
  const element = byId(id);
  if (!element) {
    return;
  }
  element.addEventListener(eventName, handler);
}

function setMessage(id, text, tone) {
  const element = byId(id);
  if (!element) {
    return;
  }
  element.className = "message";
  element.textContent = text || "";
  if (tone) {
    element.classList.add(`message-${tone}`);
  }
}

function setList(listId, emptyId, values) {
  const list = byId(listId);
  const empty = byId(emptyId);
  if (!list || !empty) {
    return;
  }
  list.innerHTML = "";
  if (!values || values.length === 0) {
    empty.style.display = "block";
    return;
  }
  empty.style.display = "none";
  values.forEach((value) => {
    const item = document.createElement("li");
    item.textContent = value;
    list.appendChild(item);
  });
}

function setCodeBlock(blockId, emptyId, value) {
  const block = byId(blockId);
  const empty = byId(emptyId);
  if (!block || !empty) {
    return;
  }
  if (!value) {
    block.textContent = "";
    empty.style.display = "block";
    return;
  }
  block.textContent = value;
  empty.style.display = "none";
}

function setText(id, value) {
  const element = byId(id);
  if (!element) {
    return;
  }
  element.textContent = String(value || "");
}

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

function toQuery(params) {
  const query = new URLSearchParams();
  Object.keys(params || {}).forEach((key) => {
    const value = params[key];
    if (value !== undefined && value !== null && String(value).trim()) {
      query.set(key, String(value).trim());
    }
  });
  const rendered = query.toString();
  return rendered ? `?${rendered}` : "";
}

function prunePayload(payload) {
  Object.keys(payload).forEach((key) => {
    const value = payload[key];
    if (value === "" || value === undefined || value === null) {
      delete payload[key];
      return;
    }
    if (Array.isArray(value) && value.length === 0) {
      delete payload[key];
    }
  });
  return payload;
}

async function fetchJson(url, options) {
  const response = await fetch(url, options || { method: "GET" });
  const payload = await response.json();
  if (!response.ok || payload.ok === false) {
    throw new Error(payload.message || payload.error || "Request failed.");
  }
  return payload;
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

function queueEntries(queueStatusCounts) {
  return countLines("status", queueStatusCounts);
}

function statusBadgeText(readiness) {
  const status = String((readiness || {}).overall_status || "needs_attention");
  return status;
}

function workflowLine(workflow) {
  return `${workflow.workflow_id} | ${workflow.title} | section=${workflow.related_hub_section} | status=${workflow.execution_status}`;
}

function renderWorkflowCards(containerId, emptyId, workflows) {
  const container = byId(containerId);
  const empty = byId(emptyId);
  if (!container || !empty) {
    return;
  }
  container.innerHTML = "";
  if (!workflows || workflows.length === 0) {
    empty.style.display = "block";
    return;
  }
  empty.style.display = "none";
  workflows.forEach((workflow) => {
    const card = document.createElement("article");
    card.className = "workflow-card";
    const required = (workflow.required_inputs || []).join(", ") || "none";
    card.innerHTML = `
      <h4>${workflow.title || workflow.workflow_id || "workflow"}</h4>
      <p>${workflow.description || ""}</p>
      <p><strong>Hub:</strong> ${workflow.related_hub_section || "-"}</p>
      <p><strong>Inputs:</strong> ${required}</p>
      <p><strong>Status:</strong> ${workflow.execution_status || "report_only"}</p>
      <p><strong>Notes:</strong> ${workflow.notes || ""}</p>
    `;
    container.appendChild(card);
  });
}

const state = {
  projects: [],
  selectedProjectId: "",
  activeProject: null,
  bootstrapStatus: null,
  bootstrapPlan: null,
  queueFilters: {
    project_id: "",
    repo_id: "",
    status: "",
    type: "",
    assigned_agent: "",
  },
  report: null,
  exportText: "",
  projectFactoryDossier: null,
  scopePackage: null,
  architectureContract: null,
  milestoneIssuePlan: null,
  githubApplyPlan: null,
  agentDispatchPlan: null,
  validationExecutionPlan: null,
  documentationCloseoutPlan: null,
  executionPhaseApproval: null,
  executionReadiness: null,
};

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
  state.activeProject = payload || null;
  const selected = Boolean(payload && payload.active_project_selected);
  const project = (payload && payload.active_project) || {};
  const repo = (payload && payload.active_repo) || {};
  const projectId = String((payload && payload.active_project_id) || "").trim();
  const repoId = String((payload && payload.active_repo_id) || "").trim();
  const projectName = project.name || projectId || "None selected";

  const homeName = byId("home-active-project-name");
  if (homeName) {
    homeName.textContent = selected ? projectName : "None selected";
  }
  const badge = byId("home-active-project-badge");
  if (badge) {
    badge.textContent = selected ? "active" : "not selected";
    badge.className = selected ? "status-pill status-pill-ready" : "status-pill status-pill-needs_attention";
  }
  const detail = byId("home-active-project-detail");
  if (detail) {
    detail.textContent = selected
      ? `${projectId} | status=${project.status || "-"} | github=${project.github_connection_status || "unlinked"}`
      : "Select an active project from Projects.";
  }
  const repoIdElement = byId("home-active-repo-id");
  if (repoIdElement) {
    repoIdElement.textContent = repoId || "-";
  }
  const repoDetail = byId("home-active-repo-detail");
  if (repoDetail) {
    repoDetail.textContent = repoId
      ? `${repo.name || repoId} | role=${repo.role || "-"} | status=${repo.status || "-"}`
      : "Used as the Queue default when available.";
  }

  const projectSummary = byId("projects-active-project-summary");
  if (projectSummary) {
    projectSummary.textContent = selected
      ? `Active project: ${projectId} (${project.name || projectId}) | default repo: ${repoId || "-"}`
      : "No active project selected.";
  }
  const queueSummary = byId("queue-active-project-summary");
  if (queueSummary) {
    queueSummary.textContent = selected
      ? `Queue defaults will use project=${projectId} and repo=${repoId || "(manual repo required)"}.`
      : "No active project selected. Queue filters and new items remain manual.";
  }
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

  byId("home-workbench-project").textContent = selected
    ? `${activeProjectIdValue} | ${(project.name || activeProjectIdValue || "-")}`
    : "No active project selected";
  byId("home-workbench-project-detail").textContent = selected
    ? `status=${project.status || "-"}`
    : "Select an active project from Projects.";
  byId("home-workbench-repo").textContent = activeRepoIdValue
    ? `${activeRepoIdValue} | ${(repo.name || activeRepoIdValue)}`
    : "-";
  byId("home-workbench-repo-detail").textContent = activeRepoIdValue
    ? `status=${repo.status || "-"}`
    : "No active repo selected.";
  byId("home-workbench-current-work").textContent = `queue=${queueTotal} | ready=${readyCount} | blocked=${blockedCount}`;
  byId("home-workbench-current-work-detail").textContent = `in_progress=${inProgressCount} | high/urgent=${highUrgentCount} | unassigned=${unassignedCount}`;
  byId("home-workbench-attention").textContent = `blocked=${blockedCount} | high/urgent=${highUrgentCount}`;
  byId("home-workbench-attention-detail").textContent = `GitHub sync status: ${githubSyncStatus}`;

  const currentWorkItems = (report.active_project_current_items || []).map((item) => {
    const title = item.title || "(no title)";
    return `${item.item_id || "-"} | ${title} | status=${item.status || "-"} | priority=${item.priority || "-"} | agent=${item.assigned_agent || "-"}`;
  });
  if (!selected) {
    setList("home-current-active-work", "home-current-active-work-empty", ["No active project selected"]);
  } else {
    setList("home-current-active-work", "home-current-active-work-empty", currentWorkItems);
  }

  const workbenchActions = [];
  (report.recommended_next_actions || []).forEach((action) => workbenchActions.push(String(action)));
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
  activateSection("queue");
  const intakeTitle = byId("intake-title");
  if (intakeTitle) {
    intakeTitle.focus();
  }
}

function renderProjects(projects) {
  const lines = (projects || []).map((project) => {
    const tags = (project.tags || []).join(", ") || "-";
    const githubState = project.github_connection_status || "unlinked";
    const activeMarker = project.is_active_project ? "ACTIVE | " : "";
    return `${activeMarker}${project.project_id} | ${project.name} | status=${project.status || "-"} | github=${githubState} | owner=${project.github_owner || "-"} | repo=${project.github_repo || "-"} | primary=${project.primary_repo_id || "-"} | root=${project.root_path || "-"} | repos=${project.repo_count || 0} | tags=${tags}`;
  });
  setList("projects-list", "projects-empty-state", lines);
}

function renderProjectsReadOnly(payload) {
  const projects = (payload && payload.projects) || [];
  const lines = projects.map((project) => {
    const activeMarker = project.is_active ? "ACTIVE" : "INACTIVE";
    const pathValue = project.local_path || project.repo_path || "-";
    return `${activeMarker} | ${project.project_id} | ${project.project_name || "-"} | readiness=${project.readiness_status || "-"} | path=${pathValue} | primary_repo=${project.repo_path || "-"} | warnings=${(payload.warnings || []).length}`;
  });
  setList("projects-readonly-list", "projects-readonly-empty-state", lines);
}

function refreshProjectSelectors(projects) {
  const selectors = [byId("repo-project-select"), byId("active-project-select")].filter(Boolean);
  const previousRepoProject = byId("repo-project-select") ? byId("repo-project-select").value : "";
  const currentActive = activeProjectId();

  selectors.forEach((selector) => {
    const previous = selector.id === "active-project-select" ? currentActive : previousRepoProject;
    selector.innerHTML = "";
    const initialOption = document.createElement("option");
    initialOption.value = "";
    initialOption.textContent = selector.id === "active-project-select" ? "Select active project" : "Select project";
    selector.appendChild(initialOption);
    (projects || []).forEach((project) => {
      const option = document.createElement("option");
      option.value = project.project_id;
      option.textContent = `${project.is_active_project ? "ACTIVE - " : ""}${project.project_id} (${project.name})`;
      selector.appendChild(option);
    });
    if ((projects || []).some((project) => project.project_id === previous)) {
      selector.value = previous;
    } else {
      selector.value = "";
    }
  });

  const repoSelector = byId("repo-project-select");
  if (repoSelector) {
    if ((projects || []).some((project) => project.project_id === previousRepoProject)) {
      state.selectedProjectId = previousRepoProject;
    } else if (currentActive && (projects || []).some((project) => project.project_id === currentActive)) {
      repoSelector.value = currentActive;
      state.selectedProjectId = currentActive;
    } else {
      state.selectedProjectId = "";
    }
  }
}

function renderRepos(repos, showNoProject) {
  const noProject = byId("repos-no-project-state");
  const list = byId("repos-list");
  const empty = byId("repos-empty-state");
  if (noProject) {
    noProject.style.display = showNoProject ? "block" : "none";
  }
  if (!list || !empty) {
    return;
  }
  list.innerHTML = "";
  if (!repos || repos.length === 0) {
    empty.style.display = "block";
    return;
  }
  empty.style.display = "none";
  repos.forEach((repo) => {
    const item = document.createElement("li");
    const tags = (repo.tags || []).join(", ") || "-";
    const githubState = repo.github_connection_status || "unlinked";
    const localGit = repo.local_git_status_summary || "-";
    item.textContent = `${repo.repo_id} | ${repo.name} | role=${repo.role || "-"} | status=${repo.status || "-"} | github=${githubState} | owner=${repo.github_owner || "-"} | repo=${repo.github_repo || "-"} | branch=${repo.local_git_branch || "-"} | head=${repo.local_git_head || "-"} | local_status=${localGit} | path=${repo.path || "-"} | tags=${tags}`;

    const button = document.createElement("button");
    button.type = "button";
    button.textContent = "Inspect local git link";
    button.className = "repo-link-action";
    button.addEventListener("click", async () => {
      await inspectRepoGitHubLink(repo.repo_id, true);
    });
    item.appendChild(document.createTextNode(" "));
    item.appendChild(button);
    list.appendChild(item);
  });
}

async function inspectRepoGitHubLink(repoId, inspectLocalGit) {
  if (!state.selectedProjectId) {
    setMessage("repos-message", "Select a project before inspecting a repo link.", "warn");
    return;
  }
  if (!repoId || !String(repoId).trim()) {
    setMessage("repos-message", "Enter or choose a repo id before inspecting link state.", "warn");
    return;
  }

  try {
    setMessage("repos-message", "Inspecting local git link metadata...", "loading");
    const query = toQuery({ inspect_local_git: inspectLocalGit ? "true" : "false" });
    const payload = await fetchJson(
      `/api/projects/${encodeURIComponent(state.selectedProjectId)}/repos/${encodeURIComponent(String(repoId).trim())}/github-link${query}`
    );
    const warningText = (payload.warnings || []).join(" | ");
    const message = `Repo ${payload.repo_id}: github=${payload.github_connection_status} owner=${payload.github_owner || "-"} repo=${payload.github_repo || "-"} local_branch=${payload.local_git_branch || "-"} local_head=${payload.local_git_head || "-"} local_status=${payload.local_git_status_summary || "-"}`;
    setMessage("repos-message", warningText ? `${message} | warnings: ${warningText}` : message, warningText ? "warn" : "success");
    await loadReposForSelectedProject();
    await loadProjects();
    await refreshSummaryAndReport();
  } catch (error) {
    setMessage("repos-message", String(error.message || error), "error");
  }
}

function renderQueueItems(items) {
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
          await loadQueue();
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

function assignmentLines(assignments) {
  return (assignments || []).map((assignment) => {
    return `${assignment.item_id} -> ${assignment.recommended_agent_id || "unassigned"} (${assignment.recommended_agent_role || "unknown"})`;
  });
}

function blockedLines(items) {
  return (items || []).map((item) => `${item.item_id} | ${item.reason || item.status || "blocked"}`);
}

function promptLines(prompts) {
  return (prompts || []).map((prompt) => {
    const text = String(prompt.prompt || "").replace(/\s+/g, " ").trim();
    const shortText = text.length > 180 ? `${text.slice(0, 180)}...` : text;
    return `${prompt.item_id || "item"}: ${shortText}`;
  });
}

function renderOrchestrationPlan(plan) {
  setList("orchestration-assignments", "orchestration-assignments-empty", assignmentLines(plan.recommended_assignments));
  setList("orchestration-dependency-order", "orchestration-dependency-empty", plan.dependency_order || []);
  setList("orchestration-blocked", "orchestration-blocked-empty", blockedLines(plan.blocked_items));
  setList("orchestration-unassigned", "orchestration-unassigned-empty", blockedLines(plan.unassigned_items));
  setList("orchestration-prompts", "orchestration-prompts-empty", promptLines(plan.handoff_prompts));
  setList("orchestration-risks", "orchestration-risks-empty", plan.risk_warnings || []);
  setList("orchestration-actions", "orchestration-actions-empty", plan.next_actions || []);
}

function classificationLines(label, items) {
  return (items || []).map((item) => `${label}: ${item.item_id} (${item.project_id || "-"}/${item.repo_id || "-"})`);
}

function reasonLines(reasonsByItem) {
  if (!reasonsByItem || typeof reasonsByItem !== "object") {
    return [];
  }
  return Object.keys(reasonsByItem).map((itemId) => `${itemId}: ${(reasonsByItem[itemId] || []).join("; ")}`);
}

function targetLines(targets) {
  return (targets || []).map((target) => `${target.item_id || "item"}: agent=${target.recommended_agent_id || "-"} target=${target.recommended_target_id || "-"} type=${target.recommended_target_type || "-"}`);
}

function guidanceLines(guidance) {
  return (guidance || []).map((item) => {
    const text = String(item.prompt || "").replace(/\s+/g, " ").trim();
    const shortText = text.length > 170 ? `${text.slice(0, 170)}...` : text;
    return `${item.item_id || "item"} (${item.classification || "-"}): ${shortText}`;
  });
}

function renderEscalationPlan(plan) {
  setList("escalation-local-llm", "escalation-local-llm-empty", classificationLines("local_llm_suitable", plan.local_llm_suitable));
  setList("escalation-codex", "escalation-codex-empty", classificationLines("codex_suitable", plan.codex_suitable));
  setList("escalation-cloud", "escalation-cloud-empty", classificationLines("cloud_llm_recommended", plan.cloud_llm_recommended));
  setList("escalation-human", "escalation-human-empty", classificationLines("human_required", plan.human_required));
  setList("escalation-blocked", "escalation-blocked-empty", classificationLines("blocked_or_needs_clarification", plan.blocked_or_needs_clarification));
  setList("escalation-reasons", "escalation-reasons-empty", reasonLines(plan.escalation_reasons));
  setList("escalation-targets", "escalation-targets-empty", targetLines(plan.recommended_handoff_targets));
  setList("escalation-guidance", "escalation-guidance-empty", guidanceLines(plan.prompt_guidance));
  setList("escalation-risks", "escalation-risks-empty", plan.risk_warnings || []);
  setList("escalation-actions", "escalation-actions-empty", plan.next_actions || []);
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
  const payload = await fetchJson("/api/projects/active", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: projectId }),
  });
  renderActiveProjectSummary(payload);
  return payload;
}

async function loadProjects() {
  setMessage("projects-message", "Loading projects...", "loading");
  await loadActiveProject();
  try {
    const localProjectsPayload = await fetchJson("/api/local-projects");
    renderProjectsReadOnly(localProjectsPayload);
  } catch (_error) {
    setList("projects-readonly-list", "projects-readonly-empty-state", []);
  }
  const payload = await fetchJson("/api/projects");
  state.projects = payload.projects || [];
  if (payload.active_project_id) {
    renderActiveProjectSummary(payload);
  }
  renderProjects(state.projects);
  refreshProjectSelectors(state.projects);
  await loadProjectFactoryDossier(activeProjectId());
  await loadScopePackage(activeProjectId());
  await loadArchitectureContract(activeProjectId());
  await loadMilestoneIssuePlan(activeProjectId());
  await loadGithubApplyPlan(activeProjectId());
  await loadAgentDispatchPlan(activeProjectId());
  await loadValidationExecutionPlan(activeProjectId());
  await loadDocumentationCloseoutPlan(activeProjectId());
  await loadExecutionPhaseApproval(activeProjectId());
  setMessage("projects-message", payload.warnings && payload.warnings.length ? payload.warnings.join(" | ") : "Projects loaded.", payload.warnings && payload.warnings.length ? "warn" : "success");
}

async function loadReposForSelectedProject() {
  const projectId = state.selectedProjectId;
  if (!projectId) {
    renderRepos([], true);
    return;
  }
  setMessage("repos-message", "Loading repos...", "loading");
  const payload = await fetchJson(`/api/projects/${encodeURIComponent(projectId)}/repos`);
  renderRepos(payload.repos || [], false);
  setMessage("repos-message", payload.warnings && payload.warnings.length ? payload.warnings.join(" | ") : "Repos loaded.", payload.warnings && payload.warnings.length ? "warn" : "success");
}

function renderQueueReadOnlySummary(payload) {
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
    Object.keys(statusCounts).sort().map((status) => `${status}: ${statusCounts[status]}`),
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

async function loadQueueReadOnlySummary() {
  const payload = await fetchJson("/api/local-queue-agent-summary");
  renderQueueReadOnlySummary(payload);
}

async function loadQueue() {
  setMessage("queue-message", "Loading queue...", "loading");
  try {
    await loadQueueReadOnlySummary();
  } catch (_error) {
    setText("queue-readonly-total-count", "0");
    setText("queue-readonly-active-project", "Unavailable");
    setText("queue-readonly-next-safe-action", "Queue summary endpoint unavailable.");
    setList("queue-readonly-status-counts", "queue-readonly-status-counts-empty", []);
    setList("queue-readonly-grouped-items", "queue-readonly-grouped-items-empty", []);
    setList("queue-readonly-blocked-items", "queue-readonly-blocked-items-empty", []);
    setList("queue-readonly-ready-items", "queue-readonly-ready-items-empty", []);
  }
  const payload = await fetchJson(`/api/queue${toQuery(state.queueFilters)}`);
  renderQueueItems(payload.items || []);
  setList("queue-counts", "queue-counts-empty-state", [].concat(countLines("status", payload.counts_by_status), countLines("type", payload.counts_by_type), countLines("priority", payload.counts_by_priority)));
  setMessage("queue-message", payload.warnings && payload.warnings.length ? payload.warnings.join(" | ") : "Queue loaded.", payload.warnings && payload.warnings.length ? "warn" : "success");
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

async function loadOrchestrationPlan(filters, usePost) {
  setMessage("orchestration-message", "Generating plan-only orchestration output...", "loading");
  let payload;
  if (usePost) {
    payload = await fetchJson("/api/orchestration/plan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(prunePayload(filters || {})),
    });
  } else {
    payload = await fetchJson("/api/orchestration/plan");
  }
  renderOrchestrationPlan(payload);
  setMessage("orchestration-message", "Plan generated. This is plan-only and does not execute agents.", "success");
}

async function loadEscalationPlan(filters, usePost) {
  setMessage("escalation-message", "Generating plan-only escalation output...", "loading");
  let payload;
  if (usePost) {
    payload = await fetchJson("/api/escalation/plan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(prunePayload(filters || {})),
    });
  } else {
    payload = await fetchJson("/api/escalation/plan");
  }
  renderEscalationPlan(payload);
  setMessage("escalation-message", "Plan generated. No local/cloud/Codex/ChatGPT/Ollama model invocation occurred.", "success");
}

function renderReportSummary(report) {
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
  setList("readiness-list", "readiness-empty-state", (report.project_management_readiness || []).concat((report.plan_only_boundary_hints || []).map((hint) => `Boundary: ${hint}`)));
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

async function loadDashboardReport() {
  setMessage("reports-message", "Loading dashboard report...", "loading");
  const payload = await fetchJson("/api/reports/dashboard", { method: "GET" });
  state.report = payload;
  renderReportSummary(payload);
  setMessage("reports-message", "Report loaded.", "success");
}

function renderLocalProjectReportFoundation(report) {
  const activeProject = (report && report.active_project) || {};
  const projectHealth = (report && report.project_health) || {};
  const roadmapSummary = (report && report.roadmap_summary) || {};
  const queueSummary = (report && report.queue_summary) || {};
  const validationSummary = (report && report.validation_summary) || {};
  const documentationSummary = (report && report.documentation_summary) || {};
  const blockers = Array.isArray(report && report.blockers) ? report.blockers : [];
  const warnings = Array.isArray(report && report.warnings) ? report.warnings : [];

  setText(
    "reports-local-active-project",
    activeProject.active_project_name || activeProject.active_project_id || "None selected",
  );
  setText("reports-local-project-health", projectHealth.overall_status || "needs_attention");
  setText(
    "reports-local-recommended-next-action",
    (report && report.recommended_next_action) || "No recommendation available.",
  );
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
    Object.keys(validationSummary).sort().map((key) => `${key}: ${validationSummary[key]}`),
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

async function loadLocalProjectReportFoundation() {
  const payload = await fetchJson("/api/local-project-report", { method: "GET" });
  renderLocalProjectReportFoundation(payload);
}

function renderLocalHomeDashboard(dashboard, report) {
  const projectSummary = (dashboard && dashboard.project_summary) || {};
  const queueSummary = (dashboard && dashboard.queue_summary) || {};
  const docsSummary = (dashboard && dashboard.docs_summary) || {};
  const activeProject = (dashboard && dashboard.active_project) || {};
  const readinessSummary = (report && report.project_health) || {};
  const warnings = Array.isArray((dashboard && dashboard.warnings)) ? dashboard.warnings : [];
  const blockers = Array.isArray((report && report.blockers)) ? report.blockers : [];
  const recommended = (report && report.recommended_next_action) || (dashboard && dashboard.recommended_next_action) || "No recommendation available yet.";
  const overallStatus = readinessSummary.overall_status || ((dashboard && dashboard.validation_summary) || {}).overall_status || "needs_attention";
  const queueStatuses = queueSummary.counts_by_status || {};
  const queueLines = Object.keys(queueStatuses).sort().map((key) => `${key}: ${queueStatuses[key]}`);

  setText("home-local-total-projects", String(projectSummary.project_count || dashboard.total_projects || 0));
  setText("home-local-active-project", activeProject.name || "None selected");
  setText("home-local-active-project-id", `project_id: ${dashboard.active_project_id || "-"}`);
  setText("home-local-active-repo", dashboard.active_repo_id || "-");
  setText("home-local-overall-readiness", overallStatus);
  setText("home-local-queue-count", String(queueSummary.item_count || 0));
  setText("home-local-docs-readiness", docsSummary.docs_ready ? "ready" : "needs docs");
  setList("home-local-queue-status-summary", "home-local-queue-status-summary-empty", queueLines);
  setText("home-local-recommended-next-action", recommended);
  setList("home-local-warnings-blockers", "home-local-warnings-blockers-empty", blockers.concat(warnings).slice(0, 12));
  setText("home-local-dashboard-message", "Read-only local dashboard/report snapshot loaded.");
}

async function loadLocalHomeDashboard() {
  const dashboard = await fetchJson("/api/local-project-dashboard", { method: "GET" });
  const report = await fetchJson("/api/local-project-report", { method: "GET" });
  renderLocalHomeDashboard(dashboard, report);
}

async function loadReportSlices() {
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

async function loadExportPreview(formatName) {
  const payload = await fetchJson(`/api/reports/export${toQuery({ format: formatName || "json" })}`, { method: "GET" });
  state.exportText = String(payload.content || "");
  setCodeBlock("reports-export-content", "reports-export-content-empty", state.exportText);
  return payload;
}

async function copyExportText() {
  if (!state.exportText) {
    await loadExportPreview("json");
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

async function refreshSummaryAndReport() {
  try {
    await loadLocalHomeDashboard();
  } catch (_error) {
    setText("home-local-dashboard-message", "Local home dashboard data is unavailable.");
    setText("home-local-recommended-next-action", "Refresh Summary to retry local dashboard loading.");
    setList("home-local-queue-status-summary", "home-local-queue-status-summary-empty", []);
    setList("home-local-warnings-blockers", "home-local-warnings-blockers-empty", ["Local dashboard/report endpoint unavailable."]);
  }
  try {
    await loadLocalProjectReportFoundation();
  } catch (_error) {
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

function buildProjectPayload() {
  return prunePayload({
    project_id: byId("project-project-id").value.trim(),
    name: byId("project-name").value.trim(),
    root_path: byId("project-root-path").value.trim(),
    description: byId("project-description").value.trim(),
    status: byId("project-status").value.trim(),
    default_branch: byId("project-default-branch").value.trim(),
    primary_repo_id: byId("project-primary-repo-id").value.trim(),
    github_url: byId("project-github-url").value.trim(),
    github_owner: byId("project-github-owner").value.trim(),
    github_repo: byId("project-github-repo").value.trim(),
    github_default_branch: byId("project-github-default-branch").value.trim(),
    tags: parseCommaList(byId("project-tags").value),
    notes: byId("project-notes").value.trim(),
  });
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
  activateSection("projects");
  const firstField = byId("wizard-project-name");
  if (firstField) {
    firstField.focus();
  }
}

function buildRepoPayload() {
  return prunePayload({
    repo_id: byId("repo-repo-id").value.trim(),
    name: byId("repo-name").value.trim(),
    path: byId("repo-path").value.trim(),
    remote_url: byId("repo-remote-url").value.trim(),
    default_branch: byId("repo-default-branch").value.trim(),
    github_url: byId("repo-github-url").value.trim(),
    github_owner: byId("repo-github-owner").value.trim(),
    github_repo: byId("repo-github-repo").value.trim(),
    github_default_branch: byId("repo-github-default-branch").value.trim(),
    inspect_local_git: byId("repo-inspect-local-git").checked,
    role: byId("repo-role").value.trim(),
    status: byId("repo-status").value.trim(),
    tags: parseCommaList(byId("repo-tags").value),
    notes: byId("repo-notes").value.trim(),
  });
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

function buildIntakePayload() {
  const title = byId("intake-title").value.trim();
  const intakeType = byId("intake-type").value.trim() || "task";
  const itemType = intakeType === "direction" ? "task" : intakeType;
  const tags = parseCommaList(byId("intake-tags").value);
  if (intakeType === "direction" && tags.indexOf("direction") === -1) {
    tags.push("direction");
  }
  if (tags.indexOf("active-project-intake") === -1) {
    tags.push("active-project-intake");
  }

  return prunePayload({
    item_id: byId("intake-item-id").value.trim() || generatedQueueItemId(title),
    project_id: activeProjectId(),
    repo_id: activeRepoId(),
    title,
    description: byId("intake-description").value.trim(),
    status: byId("intake-status").value.trim() || "proposed",
    priority: byId("intake-priority").value.trim() || "normal",
    item_type: itemType,
    tags,
    assigned_agent: byId("intake-assigned-agent").value.trim(),
    source: `hub-active-project-intake:${intakeType}`,
    notes: byId("intake-notes").value.trim(),
  });
}

function clearIntakeForm() {
  ["intake-item-id", "intake-title", "intake-assigned-agent", "intake-tags", "intake-description", "intake-notes"].forEach((id) => {
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
  if (byId("intake-status")) {
    byId("intake-status").value = "proposed";
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

  on("project-form", "submit", async (event) => {
    event.preventDefault();
    try {
      setMessage("projects-message", "Saving project...", "loading");
      await fetchJson("/api/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildProjectPayload()),
      });
      await loadProjects();
      await refreshSummaryAndReport();
      await loadReposForSelectedProject();
      setMessage("projects-message", "Project saved.", "success");
    } catch (error) {
      setMessage("projects-message", String(error.message || error), "error");
    }
  });

  on("active-project-set", "click", async () => {
    const projectId = byId("active-project-select").value.trim();
    if (!projectId) {
      setMessage("projects-message", "Choose a project to set active.", "warn");
      return;
    }
    try {
      setMessage("projects-message", "Setting active project...", "loading");
      await setActiveProject(projectId);
      await loadProjects();
      await refreshSummaryAndReport();
      await loadProjectFactoryDossier(activeProjectId());
      await loadScopePackage(activeProjectId());
      await loadArchitectureContract(activeProjectId());
      applyActiveProjectDefaultsToQueueForm();
      setMessage("projects-message", `Active project set to ${projectId}.`, "success");
    } catch (error) {
      setMessage("projects-message", String(error.message || error), "error");
    }
  });

  on("repo-project-select", "change", async () => {
    state.selectedProjectId = byId("repo-project-select").value;
    try {
      await loadReposForSelectedProject();
    } catch (error) {
      setMessage("repos-message", String(error.message || error), "error");
    }
  });

  on("repo-form", "submit", async (event) => {
    event.preventDefault();
    if (!state.selectedProjectId) {
      setMessage("repos-message", "Select a project before saving a repo.", "warn");
      return;
    }
    try {
      setMessage("repos-message", "Saving repo...", "loading");
      await fetchJson(`/api/projects/${encodeURIComponent(state.selectedProjectId)}/repos`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildRepoPayload()),
      });
      await loadReposForSelectedProject();
      await loadProjects();
      await refreshSummaryAndReport();
      setMessage("repos-message", "Repo saved.", "success");
    } catch (error) {
      setMessage("repos-message", String(error.message || error), "error");
    }
  });

  on("repo-check-github-link", "click", async () => {
    try {
      await inspectRepoGitHubLink(byId("repo-repo-id").value.trim(), true);
    } catch (error) {
      setMessage("repos-message", String(error.message || error), "error");
    }
  });

  on("queue-use-active-project", "click", () => {
    applyActiveProjectDefaultsToQueueForm();
    setMessage("queue-message", activeProjectId() ? "Active project defaults applied to queue form." : "No active project selected.", activeProjectId() ? "success" : "warn");
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
      await loadQueue();
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
      await loadQueue();
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
      await loadQueue();
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
      await loadQueue();
      await refreshSummaryAndReport();
      setMessage("queue-message", "Queue item saved.", "success");
    } catch (error) {
      setMessage("queue-message", String(error.message || error), "error");
    }
  });

  on("intake-form", "submit", async (event) => {
    event.preventDefault();
    const intakeSubmit = byId("intake-submit");
    const originalIntakeSubmitLabel = intakeSubmit ? intakeSubmit.textContent : "";
    if (!activeProjectId()) {
      setMessage("intake-message", "Select an active project before adding intake work.", "warn");
      return;
    }
    if (!activeRepoId()) {
      setMessage("intake-message", "The active project has no default repo. Add or select a primary repo first.", "warn");
      return;
    }
    try {
      if (intakeSubmit) {
        intakeSubmit.disabled = true;
        intakeSubmit.textContent = "Adding...";
      }
      setMessage("intake-message", "Adding intake item to active project queue...", "loading");
      const payload = await fetchJson("/api/queue", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildIntakePayload()),
      });
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
      setMessage("intake-message", `Added ${payload.item.item_id} to active project queue.`, "success");
    } catch (error) {
      setMessage("intake-message", String(error.message || error), "error");
    } finally {
      if (intakeSubmit) {
        intakeSubmit.disabled = false;
        intakeSubmit.textContent = originalIntakeSubmitLabel || "Add To Active Project Queue";
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

  on("orchestration-form", "submit", async (event) => {
    event.preventDefault();
    try {
      await loadOrchestrationPlan(
        {
          project_id: byId("orchestration-project-id").value.trim(),
          repo_id: byId("orchestration-repo-id").value.trim(),
          status: byId("orchestration-status").value.trim(),
          format: "json",
        },
        true
      );
      await refreshSummaryAndReport();
    } catch (error) {
      setMessage("orchestration-message", String(error.message || error), "error");
    }
  });

  on("orchestration-reset", "click", async () => {
    byId("orchestration-project-id").value = "";
    byId("orchestration-repo-id").value = "";
    byId("orchestration-status").value = "";
    try {
      await loadOrchestrationPlan({}, false);
      await refreshSummaryAndReport();
    } catch (error) {
      setMessage("orchestration-message", String(error.message || error), "error");
    }
  });

  on("escalation-form", "submit", async (event) => {
    event.preventDefault();
    try {
      await loadEscalationPlan(
        {
          item_id: byId("escalation-item-id").value.trim(),
          project_id: byId("escalation-project-id").value.trim(),
          repo_id: byId("escalation-repo-id").value.trim(),
          status: byId("escalation-status").value.trim(),
          format: "json",
        },
        true
      );
      await refreshSummaryAndReport();
    } catch (error) {
      setMessage("escalation-message", String(error.message || error), "error");
    }
  });

  on("escalation-reset", "click", async () => {
    byId("escalation-item-id").value = "";
    byId("escalation-project-id").value = "";
    byId("escalation-repo-id").value = "";
    byId("escalation-status").value = "";
    try {
      await loadEscalationPlan({}, false);
      await refreshSummaryAndReport();
    } catch (error) {
      setMessage("escalation-message", String(error.message || error), "error");
    }
  });

  on("reports-refresh", "click", async () => {
    try {
      await refreshSummaryAndReport();
      setMessage("reports-message", "Report refreshed.", "success");
    } catch (error) {
      setMessage("reports-message", String(error.message || error), "error");
    }
  });

  on("home-refresh-summary", "click", async () => {
    try {
      await refreshSummaryAndReport();
      await loadExecutionReadiness(activeProjectId());
      setMessage("reports-message", "Summary refreshed.", "success");
    } catch (error) {
      setMessage("reports-message", String(error.message || error), "error");
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

  on("home-open-bootstrap", "click", () => {
    activateSection("bootstrap");
  });

  on("home-quick-intake", "click", () => {
    activateQueueIntakeFocus();
  });

  on("home-start-new-project", "click", () => {
    focusNewProjectWizard();
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

  on("reports-copy-json", "click", async () => {
    try {
      const copied = await copyExportText();
      setMessage("reports-message", copied ? "Report JSON copied." : "Nothing to copy.", copied ? "success" : "warn");
    } catch (error) {
      setMessage("reports-message", String(error.message || error), "error");
    }
  });

  on("reports-export-json", "click", async () => {
    try {
      await loadExportPreview("json");
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
  bindForms();
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
    await loadOrchestrationPlan({}, false);
  } catch (error) {
    setMessage("orchestration-message", String(error.message || error), "error");
  }

  try {
    await loadEscalationPlan({}, false);
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
