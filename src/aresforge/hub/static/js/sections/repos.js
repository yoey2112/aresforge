import { byId, on, setMessage } from "/js/core/dom.js";
import { fetchJson, prunePayload, toQuery } from "/js/core/http.js";

export function buildRepoPayload(parseCommaList) {
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

export function renderRepos(repos, showNoProject, { inspectRepoGitHubLink }) {
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

export async function inspectRepoGitHubLink(state, repoId, inspectLocalGit, { loadReposForSelectedProject, loadProjects, refreshSummaryAndReport }) {
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
      `/api/projects/${encodeURIComponent(state.selectedProjectId)}/repos/${encodeURIComponent(String(repoId).trim())}/github-link${query}`,
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

export async function loadReposForSelectedProject(state, { inspectRepoGitHubLink, loadProjects, refreshSummaryAndReport }) {
  const projectId = state.selectedProjectId;
  if (!projectId) {
    renderRepos([], true, {
      inspectRepoGitHubLink: (repoId, inspectLocalGit) => inspectRepoGitHubLink(repoId, inspectLocalGit),
    });
    return;
  }
  setMessage("repos-message", "Loading repos...", "loading");
  const payload = await fetchJson(`/api/projects/${encodeURIComponent(projectId)}/repos`);
  renderRepos(payload.repos || [], false, {
    inspectRepoGitHubLink: (repoId, inspectLocalGit) =>
      inspectRepoGitHubLink(repoId, inspectLocalGit, { loadProjects, refreshSummaryAndReport }),
  });
  setMessage(
    "repos-message",
    payload.warnings && payload.warnings.length ? payload.warnings.join(" | ") : "Repos loaded.",
    payload.warnings && payload.warnings.length ? "warn" : "success",
  );
}

export async function loadReposSection(state, deps) {
  return loadReposForSelectedProject(state, {
    inspectRepoGitHubLink: (repoId, inspectLocalGit) =>
      inspectRepoGitHubLink(state, repoId, inspectLocalGit, deps),
    loadProjects: deps.loadProjects,
    refreshSummaryAndReport: deps.refreshSummaryAndReport,
  });
}

export async function inspectRepoGitHubLinkSection(state, repoId, inspectLocalGit, deps) {
  return inspectRepoGitHubLink(state, repoId, inspectLocalGit, {
    loadReposForSelectedProject: () => loadReposSection(state, deps),
    loadProjects: deps.loadProjects,
    refreshSummaryAndReport: deps.refreshSummaryAndReport,
  });
}

export function bindReposActions({
  state,
  parseCommaList,
  reloadReposForSelectedProject,
  reloadProjects,
  refreshSummaryAndReport,
  inspectRepoGitHubLink,
}) {
  on("repo-project-select", "change", async () => {
    state.selectedProjectId = byId("repo-project-select").value;
    try {
      await reloadReposForSelectedProject();
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
        body: JSON.stringify(buildRepoPayload(parseCommaList)),
      });
      await reloadReposForSelectedProject();
      await reloadProjects();
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
}
