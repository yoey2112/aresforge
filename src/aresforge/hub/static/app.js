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
  const payload = await fetchJson(`/api/queue${toQuery(state.queueFilters)}`);
  renderQueueItems(payload.items || []);
  setList("queue-counts", "queue-counts-empty-state", queueCountLines(payload));
  setMessage("queue-message", "Queue loaded.", "success");
  if (payload.warnings && payload.warnings.length > 0) {
    setMessage("queue-message", payload.warnings.join(" | "), "warn");
  }
}

function renderAgents(agents) {
  const lines = (agents || []).map((agent) => {
    const types = (agent.allowed_item_types || []).join(", ") || "-";
    const tags = (agent.tags || []).join(", ") || "-";
    return `${agent.agent_id} | ${agent.name} | role=${agent.role || "-"} | mode=${agent.execution_mode || "-"} | status=${agent.status || "-"} | model=${agent.model_preference || "-"} | escalation_allowed=${agent.escalation_allowed} | allowed_types=${types} | tags=${tags}`;
  });
  setList("agents-list", "agents-empty-state", lines);
}

function renderHandoffTargets(targets) {
  const lines = (targets || []).map((target) => {
    const tags = (target.tags || []).join(", ") || "-";
    return `${target.target_id} | ${target.name} | type=${target.target_type || "-"} | in=${target.input_format || "-"} | out=${target.output_format || "-"} | status=${target.status || "-"} | tags=${tags}`;
  });
  setList("handoff-targets-list", "handoff-targets-empty-state", lines);
}

async function loadAgents() {
  setMessage("agents-message", "Loading agents...", "loading");
  const payload = await fetchJson("/api/agents");
  renderAgents(payload.agents || []);
  setMessage("agents-message", "Agents loaded.", "success");
  if (payload.warnings && payload.warnings.length > 0) {
    setMessage("agents-message", payload.warnings.join(" | "), "warn");
  }
}

async function loadHandoffTargets() {
  const payload = await fetchJson("/api/handoff-targets");
  renderHandoffTargets(payload.handoff_targets || []);
  if (payload.warnings && payload.warnings.length > 0) {
    setMessage("agents-message", payload.warnings.join(" | "), "warn");
  }
}

async function loadHandoffPreview() {
  setMessage("handoff-message", "Generating local handoff preview...", "loading");
  const payload = await fetchJson("/api/handoff/preview");
  setCodeBlock("handoff-preview", "handoff-preview-empty", payload.preview || "");
  setMessage("handoff-message", "Handoff preview loaded. Local-only and not posted anywhere.", "success");
  if (payload.warnings && payload.warnings.length > 0) {
    setMessage("handoff-message", payload.warnings.join(" | "), "warn");
  }
}

function assignmentLines(assignments) {
  return (assignments || []).map((assignment) => {
    return `${assignment.item_id} -> ${assignment.recommended_agent_id || "unassigned"} (${assignment.recommended_agent_role || "unknown"}, confidence=${assignment.confidence || "-"})`;
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
  return (targets || []).map((target) => {
    return `${target.item_id || "item"}: agent=${target.recommended_agent_id || "-"} target=${target.recommended_target_id || "-"} type=${target.recommended_target_type || "-"}`;
  });
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

async function loadSettings() {
  try {
    const payload = await fetchJson("/api/settings");
    byId("settings-registry-path").textContent = payload.registry_path || "(unavailable)";
    byId("settings-queue-path").textContent = payload.queue_path || "(unavailable)";
    byId("settings-agents-path").textContent = payload.agents_path || "(unavailable)";
    setList("settings-m39-boundaries", "settings-m39-boundaries-empty", payload.m39_boundary_confirmations || []);
  } catch (_error) {
    byId("settings-registry-path").textContent = "(unavailable)";
    byId("settings-queue-path").textContent = "(unavailable)";
    byId("settings-agents-path").textContent = "(unavailable)";
  }
}

async function loadSummary() {
  const payload = await fetchJson("/api/summary", { method: "GET" });
  byId("project-count").textContent = String(payload.project_count || 0);
  byId("repo-count").textContent = String(payload.repo_count || 0);
  byId("agent-count").textContent = String(payload.agent_count || 0);

  const queueValues = queueEntries(payload.queue_status_counts);
  const queueTotal = queueValues.reduce((sum, line) => sum + Number(line.split(": ")[1] || 0), 0);
  byId("queue-total").textContent = String(queueTotal);

  const readiness = (payload.project_management_readiness || []).slice();
  if (payload.orchestration_readiness_hint) {
    readiness.push(`Orchestration: ${payload.orchestration_readiness_hint}`);
  }
  if (payload.escalation_readiness_hint) {
    readiness.push(`Escalation: ${payload.escalation_readiness_hint}`);
  }
  if (payload.plan_only_boundary_hints && Array.isArray(payload.plan_only_boundary_hints)) {
    payload.plan_only_boundary_hints.forEach((hint) => readiness.push(`Boundary: ${hint}`));
  }

  setList("queue-status-list", "queue-empty-state", queueValues);
  setList("warnings-list", "warnings-empty-state", payload.warnings || []);
  setList("actions-list", "actions-empty-state", payload.next_recommended_actions || []);
  setList("readiness-list", "readiness-empty-state", readiness);
  setList("boundary-list", "boundary-empty-state", payload.boundary_confirmations || []);
}

function buildProjectPayload() {
  return prunePayload({
    project_id: byId("project-project-id").value.trim(),
    name: byId("project-name").value.trim(),
    root_path: byId("project-root-path").value.trim(),
    description: byId("project-description").value.trim(),
    status: byId("project-status").value.trim(),
    default_branch: byId("project-default-branch").value.trim(),
    tags: parseCommaList(byId("project-tags").value),
    notes: byId("project-notes").value.trim(),
  });
}

function buildRepoPayload() {
  return prunePayload({
    repo_id: byId("repo-repo-id").value.trim(),
    name: byId("repo-name").value.trim(),
    path: byId("repo-path").value.trim(),
    remote_url: byId("repo-remote-url").value.trim(),
    default_branch: byId("repo-default-branch").value.trim(),
    role: byId("repo-role").value.trim(),
    status: byId("repo-status").value.trim(),
    tags: parseCommaList(byId("repo-tags").value),
    notes: byId("repo-notes").value.trim(),
  });
}

function buildQueuePayload() {
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
  byId("project-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      setMessage("projects-message", "Saving project...", "loading");
      await fetchJson("/api/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildProjectPayload()),
      });
      await loadProjects();
      await loadSummary();
      await loadReposForSelectedProject();
      setMessage("projects-message", "Project saved.", "success");
    } catch (error) {
      setMessage("projects-message", String(error.message || error), "error");
    }
  });

  byId("repo-project-select").addEventListener("change", async () => {
    state.selectedProjectId = byId("repo-project-select").value;
    await loadReposForSelectedProject();
  });

  byId("repo-form").addEventListener("submit", async (event) => {
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
      await loadSummary();
      setMessage("repos-message", "Repo saved.", "success");
    } catch (error) {
      setMessage("repos-message", String(error.message || error), "error");
    }
  });

  byId("queue-filter-form").addEventListener("submit", async (event) => {
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
    state.queueFilters = { project_id: "", repo_id: "", status: "", type: "", assigned_agent: "" };
    try {
      await loadQueue();
      setMessage("queue-message", "Filters reset.", "success");
    } catch (error) {
      setMessage("queue-message", String(error.message || error), "error");
    }
  });

  byId("queue-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      setMessage("queue-message", "Saving queue item...", "loading");
      await fetchJson("/api/queue", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildQueuePayload()),
      });
      await loadQueue();
      await loadSummary();
      setMessage("queue-message", "Queue item saved.", "success");
    } catch (error) {
      setMessage("queue-message", String(error.message || error), "error");
    }
  });

  byId("agent-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      setMessage("agents-message", "Saving agent...", "loading");
      await fetchJson("/api/agents", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildAgentPayload()),
      });
      await loadAgents();
      await loadSummary();
      setMessage("agents-message", "Agent saved.", "success");
    } catch (error) {
      setMessage("agents-message", String(error.message || error), "error");
    }
  });

  byId("handoff-target-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      setMessage("agents-message", "Saving handoff target...", "loading");
      await fetchJson("/api/handoff-targets", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildHandoffTargetPayload()),
      });
      await loadHandoffTargets();
      await loadSummary();
      setMessage("agents-message", "Handoff target saved.", "success");
    } catch (error) {
      setMessage("agents-message", String(error.message || error), "error");
    }
  });

  byId("handoff-refresh").addEventListener("click", async () => {
    try {
      await loadHandoffPreview();
    } catch (error) {
      setMessage("handoff-message", String(error.message || error), "error");
    }
  });

  byId("orchestration-form").addEventListener("submit", async (event) => {
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
    } catch (error) {
      setMessage("orchestration-message", String(error.message || error), "error");
    }
  });

  byId("orchestration-reset").addEventListener("click", async () => {
    byId("orchestration-project-id").value = "";
    byId("orchestration-repo-id").value = "";
    byId("orchestration-status").value = "";
    try {
      await loadOrchestrationPlan({}, false);
    } catch (error) {
      setMessage("orchestration-message", String(error.message || error), "error");
    }
  });

  byId("escalation-form").addEventListener("submit", async (event) => {
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
    } catch (error) {
      setMessage("escalation-message", String(error.message || error), "error");
    }
  });

  byId("escalation-reset").addEventListener("click", async () => {
    byId("escalation-item-id").value = "";
    byId("escalation-project-id").value = "";
    byId("escalation-repo-id").value = "";
    byId("escalation-status").value = "";
    try {
      await loadEscalationPlan({}, false);
    } catch (error) {
      setMessage("escalation-message", String(error.message || error), "error");
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

  await loadSettings();
}

init();
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
