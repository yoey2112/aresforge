import { byId, on, setList, setMessage } from "/js/core/dom.js";
import { fetchJson, prunePayload } from "/js/core/http.js";

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
      applyActiveProjectDefaultsToQueueForm();
      setMessage("projects-message", `Active project set to ${projectId}.`, "success");
    } catch (error) {
      setMessage("projects-message", String(error.message || error), "error");
    }
  });
}
