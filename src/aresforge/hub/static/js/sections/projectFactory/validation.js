import { byId, on, setCodeBlock, setList, setMessage } from "/js/core/dom.js";
import { fetchJson, prunePayload, toQuery } from "/js/core/http.js";

export function buildValidationExecutionPlanPayload({ activeProjectId, parseLineList }) {
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

export function renderValidationExecutionPlan(state, payload, { toTextareaList }) {
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
    (plan.audit_trail || []).map((entry) => `${entry.timestamp || "-"} | ${entry.event_type || "-"} | state=${entry.lifecycle_state || "-"} | actor=${entry.actor || "-"}`),
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

export async function loadValidationExecutionPlan(projectId, { renderValidationExecutionPlanForState }) {
  const query = toQuery({ project_id: projectId || "" });
  const payload = await fetchJson(`/api/project-factory/validation-execution-plan${query}`, { method: "GET" });
  renderValidationExecutionPlanForState(payload);
  return payload;
}

export async function prepareValidationExecutionPlan(activeProjectId) {
  const payload = await fetchJson("/api/project-factory/validation-execution-plan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(prunePayload({ project_id: activeProjectId() })),
  });
  return payload;
}

export async function saveValidationExecutionPlanDraft(buildValidationExecutionPlanPayloadForState) {
  const payload = await fetchJson("/api/project-factory/validation-execution-plan", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(buildValidationExecutionPlanPayloadForState()),
  });
  return payload;
}

export async function approveValidationExecutionPlan(activeProjectId) {
  const payload = await fetchJson("/api/project-factory/validation-execution-plan/approve", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(prunePayload({ project_id: activeProjectId() })),
  });
  return payload;
}

export function bindProjectFactoryValidationActions({
  activeProjectId,
  prepareValidationExecutionPlanForState,
  saveValidationExecutionPlanDraftForState,
  approveValidationExecutionPlanForState,
  loadValidationExecutionPlanForState,
  loadDocumentationCloseoutPlan,
  loadProjectFactoryDossier,
  refreshSummaryAndReport,
}) {
  on("home-prepare-validation-execution-plan", "click", async () => {
    try {
      setMessage("projects-message", "Preparing local Validation Execution Plan...", "loading");
      await prepareValidationExecutionPlanForState();
      await loadValidationExecutionPlanForState(activeProjectId());
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
      await saveValidationExecutionPlanDraftForState();
      await loadValidationExecutionPlanForState(activeProjectId());
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
      await approveValidationExecutionPlanForState();
      await loadValidationExecutionPlanForState(activeProjectId());
      await loadDocumentationCloseoutPlan(activeProjectId());
      await loadProjectFactoryDossier(activeProjectId());
      await refreshSummaryAndReport();
      setMessage("projects-message", "Validation execution plan approved.", "success");
    } catch (error) {
      setMessage("projects-message", String(error.message || error), "error");
    }
  });
}
