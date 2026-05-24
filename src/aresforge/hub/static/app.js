function byId(id) {
  return document.getElementById(id);
}

function setList(listId, emptyId, values) {
  const list = byId(listId);
  const empty = byId(emptyId);
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

async function loadSummary() {
  const response = await fetch("/api/summary", { method: "GET" });
  const payload = await response.json();

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
  setList("boundary-list", "boundary-empty-state", payload.boundary_confirmations || []);
}

async function init() {
  bindNavigation();
  try {
    await loadSummary();
  } catch (_error) {
    setList("warnings-list", "warnings-empty-state", ["Hub summary API is unavailable."]);
    setList("actions-list", "actions-empty-state", ["Start the local hub server via python -m aresforge serve-hub."]);
  }
}

init();
