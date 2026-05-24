function byId(id) {
  return document.getElementById(id);
}

function setMessage(id, text, tone) {
  const element = byId(id);
  if (!element) {
    return;
  }
  element.className = "message";
  if (!text) {
    element.textContent = "";
    return;
  }
  element.textContent = text;
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

function parseCommaList(value) {
  if (!value || typeof value !== "string") {
    return [];
  }
  return value
    .split(",")
    .map((item) => item.trim())
    .filter((item, index, all) => item && all.indexOf(item) === index);
}

function toQuery(params) {
  const query = new URLSearchParams();
  Object.keys(params).forEach((key) => {
    const value = params[key];
    if (value !== undefined && value !== null && String(value).trim()) {
      query.set(key, String(value).trim());
    }
  });
  const rendered = query.toString();
  return rendered ? `?${rendered}` : "";
}

async function fetchJson(url, options) {
  const response = await fetch(url, options || { method: "GET" });
  const payload = await response.json();
  if (!response.ok || payload.ok === false) {
    const message = payload.message || payload.error || "Request failed.";
    throw new Error(message);
  }
  return payload;
}

function activateSection(sectionName) {
  document.querySelectorAll(".nav-item").forEach((button) => {
    const active = button.dataset.section === sectionName;
    button.classList.toggle("active", active);
  });

  document.querySelectorAll(".panel").forEach((panel) => {
    const active = panel.dataset.panel === sectionName;
    panel.classList.toggle("active", active);
  });
}

function bindNavigation() {
  document.querySelectorAll(".nav-item").forEach((button) => {
    button.addEventListener("click", () => activateSection(button.dataset.section));
  });
}

function queueEntries(queueStatusCounts) {
  if (!queueStatusCounts || typeof queueStatusCounts !== "object") {
    return [];
  }
  return Object.keys(queueStatusCounts)
    .sort()
    .map((status) => `${status}: ${queueStatusCounts[status]}`);
}

const state = {
  projects: [],
  selectedProjectId: "",
  queueFilters: {
    project_id: "",
    repo_id: "",
    status: "",
    type: "",
    assigned_agent: "",
  },
};

function renderProjects(projects) {
  const lines = (projects || []).map((project) => {
    const tags = (project.tags || []).join(", ") || "-";
    return `${project.project_id} | ${project.name} | status=${project.status || "-"} | root=${project.root_path || "-"} | branch=${project.default_branch || "-"} | tags=${tags} | repos=${project.repo_count || 0}`;
  });
  setList("projects-list", "projects-empty-state", lines);
}

function refreshProjectSelectors(projects) {
  const selector = byId("repo-project-select");
  if (!selector) {
    return;
  }
  const previous = selector.value;
  selector.innerHTML = "";

  const initialOption = document.createElement("option");
  initialOption.value = "";
  initialOption.textContent = "Select project";
  selector.appendChild(initialOption);

  (projects || []).forEach((project) => {
    const option = document.createElement("option");
    option.value = project.project_id;
    option.textContent = `${project.project_id} (${project.name})`;
    selector.appendChild(option);
  });

  if ((projects || []).some((project) => project.project_id === previous)) {
    selector.value = previous;
    state.selectedProjectId = previous;
  } else {
    selector.value = "";
    state.selectedProjectId = "";
  }
}

async function loadProjects() {
  setMessage("projects-message", "Loading projects...", "loading");
  const payload = await fetchJson("/api/projects");
  state.projects = payload.projects || [];
  renderProjects(state.projects);
  refreshProjectSelectors(state.projects);
  setMessage("projects-message", "Projects loaded.", "success");
  if (payload.warnings && payload.warnings.length > 0) {
    setMessage("projects-message", payload.warnings.join(" | "), "warn");
  }
}

async function loadProjectDetail(projectId) {
  const payload = await fetchJson(`/api/projects/${encodeURIComponent(projectId)}`);
  return payload;
}

function renderRepos(repos, showNoProject) {
  const noProject = byId("repos-no-project-state");
  if (noProject) {
    noProject.style.display = showNoProject ? "block" : "none";
  }

  const lines = (repos || []).map((repo) => {
    const tags = (repo.tags || []).join(", ") || "-";
    return `${repo.repo_id} | ${repo.name} | role=${repo.role || "-"} | status=${repo.status || "-"} | path=${repo.path || "-"} | branch=${repo.default_branch || "-"} | remote=${repo.remote_url || "-"} | tags=${tags}`;
  });
  setList("repos-list", "repos-empty-state", lines);
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
  setMessage("repos-message", "Repos loaded.", "success");
  if (payload.warnings && payload.warnings.length > 0) {
    setMessage("repos-message", payload.warnings.join(" | "), "warn");
  }
}

function queueCountLines(payload) {
  const lines = [];
  const byStatus = payload.counts_by_status || {};
  const byType = payload.counts_by_type || {};
  const byPriority = payload.counts_by_priority || {};

  Object.keys(byStatus).forEach((key) => lines.push(`status ${key}: ${byStatus[key]}`));
  Object.keys(byType).forEach((key) => lines.push(`type ${key}: ${byType[key]}`));
  Object.keys(byPriority).forEach((key) => lines.push(`priority ${key}: ${byPriority[key]}`));
  return lines;
}

async function quickUpdateQueueStatus(itemId, newStatus) {
  try {
    setMessage("queue-message", `Updating ${itemId} -> ${newStatus}...`, "loading");
    await fetchJson(`/api/queue/${encodeURIComponent(itemId)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: newStatus }),
    });
    await loadQueue();
    setMessage("queue-message", `Updated ${itemId} to ${newStatus}.`, "success");
  } catch (error) {
    setMessage("queue-message", String(error.message || error), "error");
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

    const tags = (item.tags || []).join(", ") || "-";
    const deps = (item.dependencies || []).join(", ") || "-";
    const blocked = (item.blocked_by || []).join(", ") || "-";

    card.innerHTML = `
      <h3>${item.item_id}</h3>
      <p>${item.title || "(no title)"}</p>
      <p><strong>Project:</strong> ${item.project_id || "-"} | <strong>Repo:</strong> ${item.repo_id || "-"}</p>
      <p><strong>Status:</strong> ${item.status || "-"} | <strong>Priority:</strong> ${item.priority || "-"} | <strong>Type:</strong> ${item.item_type || "-"}</p>
      <p><strong>Assigned:</strong> ${item.assigned_agent || "-"}</p>
      <p><strong>Dependencies:</strong> ${deps}</p>
      <p><strong>Blocked By:</strong> ${blocked}</p>
      <p><strong>Tags:</strong> ${tags}</p>
    `;

    const controls = document.createElement("div");
    controls.className = "quick-actions";
    ["ready", "in_progress", "blocked", "done"].forEach((status) => {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = `Set ${status}`;
      button.addEventListener("click", () => quickUpdateQueueStatus(item.item_id, status));
      controls.appendChild(button);
    });

    card.appendChild(controls);
    container.appendChild(card);
  });
}

async function loadQueue() {
  setMessage("queue-message", "Loading queue...", "loading");
  const query = toQuery(state.queueFilters);
  const payload = await fetchJson(`/api/queue${query}`);

  renderQueueItems(payload.items || []);
  setList("queue-counts", "queue-counts-empty-state", queueCountLines(payload));
  setMessage("queue-message", "Queue loaded.", "success");

  if (payload.warnings && payload.warnings.length > 0) {
    setMessage("queue-message", payload.warnings.join(" | "), "warn");
  }
}

async function loadSettings() {
  try {
    const payload = await fetchJson("/api/settings");
    byId("settings-registry-path").textContent = payload.registry_path || "(unavailable)";
    byId("settings-queue-path").textContent = payload.queue_path || "(unavailable)";
  } catch (_error) {
    byId("settings-registry-path").textContent = "(unavailable)";
    byId("settings-queue-path").textContent = "(unavailable)";
  }
}

async function loadSummary() {
  const payload = await fetchJson("/api/summary", { method: "GET" });

  byId("project-count").textContent = String(payload.project_count || 0);
  byId("repo-count").textContent = String(payload.repo_count || 0);
  byId("agent-count").textContent = String(payload.agent_count || 0);

  const queueValues = queueEntries(payload.queue_status_counts);
  const queueTotal = queueValues.reduce((sum, line) => {
    const value = Number(line.split(": ")[1] || 0);
    return sum + value;
  }, 0);
  byId("queue-total").textContent = String(queueTotal);

  setList("queue-status-list", "queue-empty-state", queueValues);
  setList("warnings-list", "warnings-empty-state", payload.warnings || []);
  setList("actions-list", "actions-empty-state", payload.next_recommended_actions || []);
  setList("readiness-list", "readiness-empty-state", payload.project_management_readiness || []);
  setList("boundary-list", "boundary-empty-state", payload.boundary_confirmations || []);
}

function buildProjectPayload() {
  const payload = {
    project_id: byId("project-project-id").value.trim(),
    name: byId("project-name").value.trim(),
    root_path: byId("project-root-path").value.trim(),
    description: byId("project-description").value.trim(),
    status: byId("project-status").value.trim(),
    default_branch: byId("project-default-branch").value.trim(),
    tags: parseCommaList(byId("project-tags").value),
    notes: byId("project-notes").value.trim(),
  };

  Object.keys(payload).forEach((key) => {
    const value = payload[key];
    if (value === "" || (Array.isArray(value) && value.length === 0)) {
      delete payload[key];
    }
  });
  return payload;
}

function buildRepoPayload() {
  const payload = {
    repo_id: byId("repo-repo-id").value.trim(),
    name: byId("repo-name").value.trim(),
    path: byId("repo-path").value.trim(),
    remote_url: byId("repo-remote-url").value.trim(),
    default_branch: byId("repo-default-branch").value.trim(),
    role: byId("repo-role").value.trim(),
    status: byId("repo-status").value.trim(),
    tags: parseCommaList(byId("repo-tags").value),
    notes: byId("repo-notes").value.trim(),
  };

  Object.keys(payload).forEach((key) => {
    const value = payload[key];
    if (value === "" || (Array.isArray(value) && value.length === 0)) {
      delete payload[key];
    }
  });
  return payload;
}

function buildQueuePayload() {
  const payload = {
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
  };

  Object.keys(payload).forEach((key) => {
    const value = payload[key];
    if (value === "" || (Array.isArray(value) && value.length === 0)) {
      delete payload[key];
    }
  });
  return payload;
}

function bindForms() {
  const projectForm = byId("project-form");
  projectForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      setMessage("projects-message", "Saving project...", "loading");
      const payload = buildProjectPayload();
      await fetchJson("/api/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      await loadProjects();
      await loadSummary();
      await loadReposForSelectedProject();
      setMessage("projects-message", "Project saved.", "success");
    } catch (error) {
      setMessage("projects-message", String(error.message || error), "error");
    }
  });

  const repoSelector = byId("repo-project-select");
  repoSelector.addEventListener("change", async () => {
    state.selectedProjectId = repoSelector.value;
    await loadReposForSelectedProject();
  });

  const repoForm = byId("repo-form");
  repoForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!state.selectedProjectId) {
      setMessage("repos-message", "Select a project before saving a repo.", "warn");
      return;
    }

    try {
      setMessage("repos-message", "Saving repo...", "loading");
      const payload = buildRepoPayload();
      await fetchJson(`/api/projects/${encodeURIComponent(state.selectedProjectId)}/repos`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      await loadReposForSelectedProject();
      await loadProjects();
      await loadSummary();
      setMessage("repos-message", "Repo saved.", "success");
    } catch (error) {
      setMessage("repos-message", String(error.message || error), "error");
    }
  });

  const queueFilterForm = byId("queue-filter-form");
  queueFilterForm.addEventListener("submit", async (event) => {
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

  byId("queue-filter-reset").addEventListener("click", async () => {
    byId("filter-project-id").value = "";
    byId("filter-repo-id").value = "";
    byId("filter-status").value = "";
    byId("filter-type").value = "";
    byId("filter-assigned-agent").value = "";
    state.queueFilters = {
      project_id: "",
      repo_id: "",
      status: "",
      type: "",
      assigned_agent: "",
    };
    try {
      await loadQueue();
      setMessage("queue-message", "Filters reset.", "success");
    } catch (error) {
      setMessage("queue-message", String(error.message || error), "error");
    }
  });

  const queueForm = byId("queue-form");
  queueForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      setMessage("queue-message", "Saving queue item...", "loading");
      const payload = buildQueuePayload();
      await fetchJson("/api/queue", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      await loadQueue();
      await loadSummary();
      setMessage("queue-message", "Queue item saved.", "success");
    } catch (error) {
      setMessage("queue-message", String(error.message || error), "error");
    }
  });
}

async function init() {
  bindNavigation();
  bindForms();
  renderRepos([], true);

  try {
    await loadSummary();
  } catch (_error) {
    setList("warnings-list", "warnings-empty-state", ["Hub summary API is unavailable."]);
    setList("actions-list", "actions-empty-state", ["Start the local hub server via python -m aresforge serve-hub."]);
  }

  try {
    await loadProjects();
  } catch (error) {
    setMessage("projects-message", String(error.message || error), "error");
  }

  try {
    await loadQueue();
  } catch (error) {
    setMessage("queue-message", String(error.message || error), "error");
  }

  await loadSettings();

  const selector = byId("repo-project-select");
  if (selector && selector.value) {
    state.selectedProjectId = selector.value;
    try {
      await loadProjectDetail(selector.value);
      await loadReposForSelectedProject();
    } catch (error) {
      setMessage("repos-message", String(error.message || error), "error");
    }
  }
}

init();
