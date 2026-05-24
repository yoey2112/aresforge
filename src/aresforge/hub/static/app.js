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
  queueFilters: {
    project_id: "",
    repo_id: "",
    status: "",
    type: "",
    assigned_agent: "",
  },
  report: null,
  exportText: "",
};

function renderProjects(projects) {
  const lines = (projects || []).map((project) => {
    const tags = (project.tags || []).join(", ") || "-";
    const githubState = project.github_connection_status || "unlinked";
    return `${project.project_id} | ${project.name} | status=${project.status || "-"} | github=${githubState} | owner=${project.github_owner || "-"} | repo=${project.github_repo || "-"} | primary=${project.primary_repo_id || "-"} | root=${project.root_path || "-"} | repos=${project.repo_count || 0} | tags=${tags}`;
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

async function loadProjects() {
  setMessage("projects-message", "Loading projects...", "loading");
  const payload = await fetchJson("/api/projects");
  state.projects = payload.projects || [];
  renderProjects(state.projects);
  refreshProjectSelectors(state.projects);
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

async function loadQueue() {
  setMessage("queue-message", "Loading queue...", "loading");
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
  await loadDashboardReport();
  await loadReportSlices();
}

async function loadSettings() {
  try {
    const payload = await fetchJson("/api/settings");
    byId("settings-registry-path").textContent = payload.registry_path || "(unavailable)";
    byId("settings-queue-path").textContent = payload.queue_path || "(unavailable)";
    byId("settings-agents-path").textContent = payload.agents_path || "(unavailable)";
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
      setMessage("reports-message", "Summary refreshed.", "success");
    } catch (error) {
      setMessage("reports-message", String(error.message || error), "error");
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
}

async function init() {
  bindNavigation();
  bindForms();
  renderRepos([], true);

  try {
    await refreshSummaryAndReport();
  } catch (error) {
    setMessage("reports-message", String(error.message || error), "error");
    setList("warnings-list", "warnings-empty-state", ["Hub report API is unavailable."]);
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

  try {
    await loadExportPreview("json");
  } catch (_error) {
    setCodeBlock("reports-export-content", "reports-export-content-empty", "");
  }

  await loadSettings();
}

init();
