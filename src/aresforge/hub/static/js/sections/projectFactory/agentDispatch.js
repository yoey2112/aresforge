import { byId, on, setCodeBlock, setList, setMessage } from "/js/core/dom.js";
import { fetchJson, prunePayload, toQuery } from "/js/core/http.js";

export function buildAgentDispatchPlanPayload({ activeProjectId, parseLineList }) {
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

export function renderAgentDispatchPlan(state, payload, { toTextareaList }) {
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
    (plan.audit_trail || []).map((entry) => `${entry.timestamp || "-"} | ${entry.event_type || "-"} | state=${entry.lifecycle_state || "-"} | actor=${entry.actor || "-"}`),
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

export async function loadAgentDispatchPlan(projectId, { renderAgentDispatchPlanForState }) {
  const query = toQuery({ project_id: projectId || "" });
  const payload = await fetchJson(`/api/project-factory/agent-dispatch-plan${query}`, { method: "GET" });
  renderAgentDispatchPlanForState(payload);
  return payload;
}

export async function prepareAgentDispatchPlan(activeProjectId) {
  const payload = await fetchJson("/api/project-factory/agent-dispatch-plan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(prunePayload({ project_id: activeProjectId() })),
  });
  return payload;
}

export async function saveAgentDispatchPlanDraft(buildAgentDispatchPlanPayloadForState) {
  const payload = await fetchJson("/api/project-factory/agent-dispatch-plan", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(buildAgentDispatchPlanPayloadForState()),
  });
  return payload;
}

export async function approveAgentDispatchPlan(activeProjectId) {
  const payload = await fetchJson("/api/project-factory/agent-dispatch-plan/approve", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(prunePayload({ project_id: activeProjectId() })),
  });
  return payload;
}

export function bindProjectFactoryAgentDispatchActions({
  activeProjectId,
  prepareAgentDispatchPlanForState,
  saveAgentDispatchPlanDraftForState,
  approveAgentDispatchPlanForState,
  loadAgentDispatchPlanForState,
  loadValidationExecutionPlan,
  loadDocumentationCloseoutPlan,
  loadProjectFactoryDossier,
  refreshSummaryAndReport,
}) {
  on("home-prepare-agent-dispatch-plan", "click", async () => {
    try {
      setMessage("projects-message", "Preparing local Agent Dispatch Plan...", "loading");
      await prepareAgentDispatchPlanForState();
      await loadAgentDispatchPlanForState(activeProjectId());
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
      await saveAgentDispatchPlanDraftForState();
      await loadAgentDispatchPlanForState(activeProjectId());
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
      await approveAgentDispatchPlanForState();
      await loadAgentDispatchPlanForState(activeProjectId());
      await loadValidationExecutionPlan(activeProjectId());
      await loadDocumentationCloseoutPlan(activeProjectId());
      await loadProjectFactoryDossier(activeProjectId());
      await refreshSummaryAndReport();
      setMessage("projects-message", "Agent dispatch plan approved.", "success");
    } catch (error) {
      setMessage("projects-message", String(error.message || error), "error");
    }
  });
}
