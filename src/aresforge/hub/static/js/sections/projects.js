import { byId, on, setList, setMessage, setText } from "/js/core/dom.js";
import { fetchJson, prunePayload } from "/js/core/http.js";

const PROJECT_AI_ENGINES = ["local_reasoning_llm", "local_coding_llm", "codex_cli"];

export function buildProjectPayload(parseCommaList) {
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

function checkedValues(selector) {
  return Array.from(document.querySelectorAll(selector))
    .filter((input) => input.checked)
    .map((input) => input.value);
}

function setCheckedValues(selector, values) {
  const selected = new Set(values || []);
  document.querySelectorAll(selector).forEach((input) => {
    input.checked = selected.has(input.value);
  });
}

function buildProjectAiSettingsPayload() {
  return {
    project_ai_mode: byId("project-ai-mode").value.trim(),
    available_engines: checkedValues(".project-ai-available-engine"),
    disabled_engines: checkedValues(".project-ai-disabled-engine"),
    default_engine: byId("project-ai-default-engine").value.trim(),
    default_model: byId("project-ai-default-model").value.trim(),
    operator_override_allowed: Boolean(byId("project-ai-operator-override-allowed").checked),
    notes: byId("project-ai-notes").value.trim(),
  };
}

export function renderProjectAiSettings(payload) {
  const details = (payload && payload.details) || {};
  const settings = (payload && payload.project_ai_settings) || details.project_ai_settings || {};
  if (byId("project-ai-mode")) {
    byId("project-ai-mode").value = settings.project_ai_mode || "balanced";
  }
  setCheckedValues(".project-ai-available-engine", settings.available_engines || PROJECT_AI_ENGINES);
  setCheckedValues(".project-ai-disabled-engine", settings.disabled_engines || []);
  if (byId("project-ai-default-engine")) {
    byId("project-ai-default-engine").value = settings.default_engine || "";
  }
  if (byId("project-ai-default-model")) {
    byId("project-ai-default-model").value = settings.default_model || "";
  }
  if (byId("project-ai-operator-override-allowed")) {
    byId("project-ai-operator-override-allowed").checked = Boolean(settings.operator_override_allowed);
  }
  if (byId("project-ai-notes")) {
    byId("project-ai-notes").value = settings.notes || "";
  }

  const validation = (payload && payload.validation) || details.validation || {};
  setList("project-ai-settings-summary", "project-ai-settings-summary-empty", [
    `project_id: ${payload && payload.project_id ? payload.project_id : "-"}`,
    `project_ai_mode: ${settings.project_ai_mode || "-"}`,
    `available_engines: ${(settings.available_engines || []).join(", ") || "none"}`,
    `disabled_engines: ${(settings.disabled_engines || []).join(", ") || "none"}`,
    `default_engine: ${settings.default_engine || "blank/manual"}`,
    `default_model: ${settings.default_model || "-"}`,
    `operator_override_allowed: ${Boolean(settings.operator_override_allowed)}`,
    `next_safe_action: ${payload && payload.next_safe_action ? payload.next_safe_action : "-"}`,
  ]);
  setList("project-ai-settings-validation", "project-ai-settings-validation-empty", [
    `valid: ${Boolean(validation.valid)}`,
    `routing_execution_status: ${validation.routing_execution_status || "not_implemented"}`,
  ]);
  setList("project-ai-settings-warnings", "project-ai-settings-warnings-empty", (payload && payload.warnings) || validation.warnings || []);
  setList("project-ai-settings-blockers", "project-ai-settings-blockers-empty", (payload && payload.blockers) || validation.blockers || (payload && payload.message ? [payload.message] : []));
}

export function renderProjectAiSettingsUnavailable(messageText) {
  setList("project-ai-settings-summary", "project-ai-settings-summary-empty", messageText ? [messageText] : []);
  setList("project-ai-settings-validation", "project-ai-settings-validation-empty", []);
  setList("project-ai-settings-warnings", "project-ai-settings-warnings-empty", []);
  setList("project-ai-settings-blockers", "project-ai-settings-blockers-empty", []);
}

export function renderProjects(projects) {
  const lines = (projects || []).map((project) => {
    const tags = (project.tags || []).join(", ") || "-";
    const githubState = project.github_connection_status || "unlinked";
    const activeMarker = project.is_active_project ? "ACTIVE | " : "";
    return `${activeMarker}${project.project_id} | ${project.name} | status=${project.status || "-"} | github=${githubState} | owner=${project.github_owner || "-"} | repo=${project.github_repo || "-"} | primary=${project.primary_repo_id || "-"} | root=${project.root_path || "-"} | repos=${project.repo_count || 0} | tags=${tags}`;
  });
  setList("projects-list", "projects-empty-state", lines);
}

export function renderProjectsReadOnly(payload) {
  const projects = (payload && payload.projects) || [];
  const lines = projects.map((project) => {
    const activeMarker = project.is_active ? "ACTIVE" : "INACTIVE";
    const pathValue = project.local_path || project.repo_path || "-";
    return `${activeMarker} | ${project.project_id} | ${project.project_name || "-"} | readiness=${project.readiness_status || "-"} | path=${pathValue} | primary_repo=${project.repo_path || "-"} | warnings=${(payload.warnings || []).length}`;
  });
  setList("projects-readonly-list", "projects-readonly-empty-state", lines);
}

export function renderProjectsReadOnlyUnavailable() {
  setList("projects-readonly-list", "projects-readonly-empty-state", []);
}

export function renderProjectProgressRollup(payload) {
  setText("projects-progress-rollup-total", payload.total_queue_items || 0);
  setText("projects-progress-rollup-ready", payload.ready_item_count || 0);
  setText("projects-progress-rollup-evidence", payload.items_with_evidence_captured_count || 0);
  setText("projects-progress-rollup-closeout", payload.items_eligible_for_closeout_count || 0);
  setText("projects-progress-rollup-closed", payload.closed_completed_item_count || 0);
  setText("projects-progress-rollup-next-safe-action", payload.next_safe_action || "Inspect local project progress.");
  const statusLines = Object.entries(payload.items_by_status || {}).map(([status, count]) => `${status}: ${count}`);
  const typeLines = Object.entries(payload.items_by_type || {}).map(([type, count]) => `type:${type}: ${count}`);
  const laneLines = Object.entries(payload.items_by_lane || {}).map(([lane, count]) => `lane:${lane}: ${count}`);
  setList("projects-progress-rollup-summary", "projects-progress-rollup-summary-empty", [
    `project: ${payload.project_id || "-"} | active=${payload.active_project ? "true" : "false"} | latest=${payload.latest_activity_timestamp || "-"}`,
    ...statusLines,
    ...typeLines,
    ...laneLines,
  ]);
  setList("projects-progress-rollup-blockers", "projects-progress-rollup-blockers-empty", payload.blockers || []);
  setList("projects-progress-rollup-warnings", "projects-progress-rollup-warnings-empty", payload.warnings || []);
}

export function renderProjectProgressRollupUnavailable(messageText) {
  setText("projects-progress-rollup-total", "0");
  setText("projects-progress-rollup-ready", "0");
  setText("projects-progress-rollup-evidence", "0");
  setText("projects-progress-rollup-closeout", "0");
  setText("projects-progress-rollup-closed", "0");
  setText("projects-progress-rollup-next-safe-action", messageText || "Select an active project to inspect progress.");
  setList("projects-progress-rollup-summary", "projects-progress-rollup-summary-empty", []);
  setList("projects-progress-rollup-blockers", "projects-progress-rollup-blockers-empty", []);
  setList("projects-progress-rollup-warnings", "projects-progress-rollup-warnings-empty", []);
}

export async function loadProjectProgressRollup(projectId) {
  const normalizedProjectId = String(projectId || "").trim();
  if (!normalizedProjectId) {
    renderProjectProgressRollupUnavailable("Select an active project to inspect progress.");
    return null;
  }
  try {
    const payload = await fetchJson(`/api/projects/${encodeURIComponent(normalizedProjectId)}/progress-rollup`);
    renderProjectProgressRollup(payload);
    return payload;
  } catch (error) {
    renderProjectProgressRollupUnavailable(String(error.message || error));
    return null;
  }
}

export async function loadProjectAiSettings(projectId) {
  const normalizedProjectId = String(projectId || "").trim();
  if (!normalizedProjectId) {
    renderProjectAiSettingsUnavailable("Select an active project to load Project AI Settings.");
    return null;
  }
  try {
    const payload = await fetchJson(`/api/projects/${encodeURIComponent(normalizedProjectId)}/ai-settings`);
    renderProjectAiSettings(payload);
    return payload;
  } catch (error) {
    renderProjectAiSettings((error && error.payload) || {});
    return null;
  }
}

export function refreshProjectSelectors(state, projects, { activeProjectId }) {
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

export async function loadProjectsData(state, { loadActiveProject, renderActiveProjectSummary, activeProjectId }) {
  setMessage("projects-message", "Loading projects...", "loading");
  await loadActiveProject();
  try {
    const localProjectsPayload = await fetchJson("/api/local-projects");
    renderProjectsReadOnly(localProjectsPayload);
  } catch (_error) {
    renderProjectsReadOnlyUnavailable();
  }
  const payload = await fetchJson("/api/projects");
  state.projects = payload.projects || [];
  if (payload.active_project_id) {
    renderActiveProjectSummary(payload);
  }
  renderProjects(state.projects);
  refreshProjectSelectors(state, state.projects, { activeProjectId });
  await loadProjectProgressRollup(activeProjectId());
  await loadProjectAiSettings(activeProjectId());
  setMessage(
    "projects-message",
    payload.warnings && payload.warnings.length ? payload.warnings.join(" | ") : "Projects loaded.",
    payload.warnings && payload.warnings.length ? "warn" : "success",
  );
  return payload;
}

export async function setActiveProject(projectId, { renderActiveProjectSummary }) {
  const payload = await fetchJson("/api/projects/active", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: projectId }),
  });
  renderActiveProjectSummary(payload);
  return payload;
}

export async function loadProjectsSection(state, deps) {
  await loadProjectsData(state, deps);
  await deps.loadProjectFactoryDossier(deps.activeProjectId());
  await deps.loadScopePackage(deps.activeProjectId());
  await deps.loadArchitectureContract(deps.activeProjectId());
  await deps.loadMilestoneIssuePlan(deps.activeProjectId());
  await deps.loadGithubApplyPlan(deps.activeProjectId());
  await deps.loadAgentDispatchPlan(deps.activeProjectId());
  await deps.loadValidationExecutionPlan(deps.activeProjectId());
  await deps.loadDocumentationCloseoutPlan(deps.activeProjectId());
  await deps.loadExecutionPhaseApproval(deps.activeProjectId());
}

export function bindProjectsActions({
  parseCommaList,
  reloadProjects,
  refreshSummaryAndReport,
  loadReposForSelectedProject,
  setActiveProject,
  activeProjectId,
  loadProjectFactoryDossier,
  loadScopePackage,
  loadArchitectureContract,
  applyActiveProjectDefaultsToQueueForm,
}) {
  on("project-form", "submit", async (event) => {
    event.preventDefault();
    try {
      setMessage("projects-message", "Saving project...", "loading");
      await fetchJson("/api/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildProjectPayload(parseCommaList)),
      });
      await reloadProjects();
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
      await reloadProjects();
      await refreshSummaryAndReport();
      await loadProjectFactoryDossier(activeProjectId());
      await loadScopePackage(activeProjectId());
      await loadArchitectureContract(activeProjectId());
      await loadProjectAiSettings(activeProjectId());
      applyActiveProjectDefaultsToQueueForm();
      setMessage("projects-message", `Active project set to ${projectId}.`, "success");
    } catch (error) {
      setMessage("projects-message", String(error.message || error), "error");
    }
  });

  on("project-ai-settings-load", "click", async () => {
    const projectId = activeProjectId();
    if (!projectId) {
      setMessage("projects-message", "Select an active project before loading AI settings.", "warn");
      return;
    }
    try {
      setMessage("projects-message", "Loading Project AI Settings...", "loading");
      await loadProjectAiSettings(projectId);
      setMessage("projects-message", "Project AI Settings loaded.", "success");
    } catch (error) {
      renderProjectAiSettings((error && error.payload) || {});
      setMessage("projects-message", String(error.message || error), "error");
    }
  });

  on("project-ai-settings-form", "submit", async (event) => {
    event.preventDefault();
    const projectId = activeProjectId();
    if (!projectId) {
      setMessage("projects-message", "Select an active project before saving AI settings.", "warn");
      return;
    }
    try {
      setMessage("projects-message", "Saving Project AI Settings...", "loading");
      const payload = await fetchJson(`/api/projects/${encodeURIComponent(projectId)}/ai-settings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildProjectAiSettingsPayload()),
      });
      renderProjectAiSettings(payload);
      setMessage("projects-message", "Project AI Settings saved. No execution performed.", "success");
    } catch (error) {
      renderProjectAiSettings((error && error.payload) || {});
      setMessage("projects-message", String(error.message || error), "error");
    }
  });
}
