import { byId, on, setCodeBlock, setList, setMessage } from "/js/core/dom.js";
import { fetchJson, prunePayload, toQuery } from "/js/core/http.js";

export function buildExecutionPhaseApprovalPayload({ activeProjectId }) {
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

export function renderExecutionPhaseApproval(state, payload) {
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
    (plan.audit_trail || []).map((entry) => `${entry.timestamp || "-"} | ${entry.event_type || "-"} | state=${entry.lifecycle_state || "-"} | actor=${entry.actor || "-"}`),
  );
  if (message) {
    message.textContent = "This is a local execution approval gate only. It does not execute GitHub mutations, validation commands, documentation updates, agents/models, or closeout.";
  }
  if (stateLine) {
    stateLine.textContent = `Execution Phase Approval lifecycle state: ${plan.lifecycle_state || "not_started"}`;
  }
}

export function renderExecutionReadiness(state, payload) {
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

export async function loadExecutionPhaseApproval(projectId, { renderExecutionPhaseApprovalForState }) {
  const query = toQuery({ project_id: projectId || "" });
  const payload = await fetchJson(`/api/project-factory/execution-phase-approval${query}`, { method: "GET" });
  renderExecutionPhaseApprovalForState(payload);
  return payload;
}

export async function loadExecutionReadiness(projectId, { renderExecutionReadinessForState }) {
  const query = toQuery({ project_id: projectId || "" });
  const payload = await fetchJson(`/api/project-factory/execution-readiness${query}`, { method: "GET" });
  renderExecutionReadinessForState(payload);
  return payload;
}

export async function prepareExecutionPhaseApproval(activeProjectId) {
  const payload = await fetchJson("/api/project-factory/execution-phase-approval", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(prunePayload({ project_id: activeProjectId() })),
  });
  return payload;
}

export async function saveExecutionPhaseApprovalDraft(buildExecutionPhaseApprovalPayloadForState) {
  const payload = await fetchJson("/api/project-factory/execution-phase-approval", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(buildExecutionPhaseApprovalPayloadForState()),
  });
  return payload;
}

export async function approveExecutionPhaseApproval(activeProjectId) {
  const payload = await fetchJson("/api/project-factory/execution-phase-approval/approve", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(prunePayload({ project_id: activeProjectId() })),
  });
  return payload;
}

export function bindProjectFactoryExecutionApprovalActions({
  activeProjectId,
  prepareExecutionPhaseApprovalForState,
  saveExecutionPhaseApprovalDraftForState,
  approveExecutionPhaseApprovalForState,
  loadExecutionPhaseApprovalForState,
  loadExecutionReadinessForState,
  loadProjectFactoryDossier,
  refreshSummaryAndReport,
}) {
  on("home-prepare-execution-phase-approval", "click", async () => {
    try {
      setMessage("projects-message", "Preparing local Execution Phase Approval...", "loading");
      await prepareExecutionPhaseApprovalForState();
      await loadExecutionPhaseApprovalForState(activeProjectId());
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
      await saveExecutionPhaseApprovalDraftForState();
      await loadExecutionPhaseApprovalForState(activeProjectId());
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
      await approveExecutionPhaseApprovalForState();
      await loadExecutionPhaseApprovalForState(activeProjectId());
      await loadExecutionReadinessForState(activeProjectId());
      await loadProjectFactoryDossier(activeProjectId());
      await refreshSummaryAndReport();
      setMessage("projects-message", "Execution phase approval approved.", "success");
    } catch (error) {
      setMessage("projects-message", String(error.message || error), "error");
    }
  });
}
