import { byId, on, setCodeBlock, setList, setMessage } from "/js/core/dom.js";
import { fetchJson, prunePayload, toQuery } from "/js/core/http.js";

export function buildDocumentationCloseoutPlanPayload({ activeProjectId, parseLineList }) {
  return prunePayload({
    project_id: activeProjectId(),
    closeout_summary: byId("documentation-closeout-summary").value.trim(),
    operator_notes: byId("documentation-closeout-operator-notes").value.trim(),
    sequencing_notes: parseLineList(byId("documentation-closeout-sequencing-notes").value),
    dependency_notes: parseLineList(byId("documentation-closeout-dependency-notes").value),
    approval_conditions: parseLineList(byId("documentation-closeout-approval-conditions").value),
    known_risks: parseLineList(byId("documentation-closeout-known-risks").value),
    documentation_update_notes: parseLineList(byId("documentation-closeout-update-notes").value),
    evidence_collection_notes: parseLineList(byId("documentation-closeout-evidence-notes").value),
  });
}

export function renderDocumentationCloseoutPlan(state, payload, { toTextareaList }) {
  state.documentationCloseoutPlan = payload || null;
  const message = byId("home-documentation-closeout-plan-message");
  const stateLine = byId("home-documentation-closeout-plan-state");
  const statusLine = byId("home-documentation-closeout-plan-status");
  const exists = Boolean(payload && payload.documentation_closeout_plan_exists);
  const plan = (payload && payload.documentation_closeout_plan) || {};
  if (!exists) {
    byId("documentation-closeout-summary").value = "";
    byId("documentation-closeout-operator-notes").value = "";
    byId("documentation-closeout-sequencing-notes").value = "";
    byId("documentation-closeout-dependency-notes").value = "";
    byId("documentation-closeout-approval-conditions").value = "";
    byId("documentation-closeout-known-risks").value = "";
    byId("documentation-closeout-update-notes").value = "";
    byId("documentation-closeout-evidence-notes").value = "";
    setCodeBlock("home-documentation-closeout-items", "home-documentation-closeout-items-empty", "");
    setCodeBlock("home-documentation-closeout-evidence-packages", "home-documentation-closeout-evidence-packages-empty", "");
    setCodeBlock("home-documentation-closeout-checks", "home-documentation-closeout-checks-empty", "");
    setList("home-documentation-closeout-audit-trail", "home-documentation-closeout-audit-trail-empty", []);
    if (message) {
      message.textContent = "No Documentation Closeout Plan found. Approve the local Validation Execution Plan first.";
    }
    if (stateLine) {
      stateLine.textContent = "Documentation Closeout Plan lifecycle state: not_started";
    }
    if (statusLine) {
      statusLine.textContent = "documentation_execution=not_requested | validation_execution=not_requested | agent_execution=not_requested | model_execution=not_requested";
    }
    return;
  }
  byId("documentation-closeout-summary").value = String(plan.closeout_summary || "");
  byId("documentation-closeout-operator-notes").value = String(plan.operator_notes || "");
  byId("documentation-closeout-sequencing-notes").value = toTextareaList(plan.sequencing_notes);
  byId("documentation-closeout-dependency-notes").value = toTextareaList(plan.dependency_notes);
  byId("documentation-closeout-approval-conditions").value = toTextareaList(plan.approval_conditions);
  byId("documentation-closeout-known-risks").value = toTextareaList(plan.known_risks);
  byId("documentation-closeout-update-notes").value = toTextareaList(plan.documentation_update_notes);
  byId("documentation-closeout-evidence-notes").value = toTextareaList(plan.evidence_collection_notes);
  const closeoutPlan = plan.documentation_plan || {};
  setCodeBlock("home-documentation-closeout-items", "home-documentation-closeout-items-empty", JSON.stringify(closeoutPlan.documentation_items || [], null, 2));
  setCodeBlock("home-documentation-closeout-evidence-packages", "home-documentation-closeout-evidence-packages-empty", JSON.stringify(closeoutPlan.evidence_packages || [], null, 2));
  setCodeBlock("home-documentation-closeout-checks", "home-documentation-closeout-checks-empty", JSON.stringify(closeoutPlan.closeout_checks || [], null, 2));
  setList(
    "home-documentation-closeout-audit-trail",
    "home-documentation-closeout-audit-trail-empty",
    (plan.audit_trail || []).map((entry) => `${entry.timestamp || "-"} | ${entry.event_type || "-"} | state=${entry.lifecycle_state || "-"} | actor=${entry.actor || "-"}`),
  );
  if (message) {
    message.textContent = "This is a local documentation closeout plan only. It does not update docs, execute validation, run agents/models, or perform GitHub actions.";
  }
  if (stateLine) {
    stateLine.textContent = `Documentation Closeout Plan lifecycle state: ${plan.lifecycle_state || "not_started"}`;
  }
  if (statusLine) {
    statusLine.textContent = `documentation_execution=${plan.documentation_execution_status || "not_requested"} | validation_execution=${plan.validation_execution_status || "not_requested"} | agent_execution=${plan.agent_execution_status || "not_requested"} | model_execution=${plan.model_execution_status || "not_requested"}`;
  }
}

export async function loadDocumentationCloseoutPlan(projectId, { renderDocumentationCloseoutPlanForState }) {
  const query = toQuery({ project_id: projectId || "" });
  const payload = await fetchJson(`/api/project-factory/documentation-closeout-plan${query}`, { method: "GET" });
  renderDocumentationCloseoutPlanForState(payload);
  return payload;
}

export async function prepareDocumentationCloseoutPlan(activeProjectId) {
  const payload = await fetchJson("/api/project-factory/documentation-closeout-plan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(prunePayload({ project_id: activeProjectId() })),
  });
  return payload;
}

export async function saveDocumentationCloseoutPlanDraft(buildDocumentationCloseoutPlanPayloadForState) {
  const payload = await fetchJson("/api/project-factory/documentation-closeout-plan", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(buildDocumentationCloseoutPlanPayloadForState()),
  });
  return payload;
}

export async function approveDocumentationCloseoutPlan(activeProjectId) {
  const payload = await fetchJson("/api/project-factory/documentation-closeout-plan/approve", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(prunePayload({ project_id: activeProjectId() })),
  });
  return payload;
}

export function bindProjectFactoryCloseoutActions({
  activeProjectId,
  prepareDocumentationCloseoutPlanForState,
  saveDocumentationCloseoutPlanDraftForState,
  approveDocumentationCloseoutPlanForState,
  loadDocumentationCloseoutPlanForState,
  loadProjectFactoryDossier,
  refreshSummaryAndReport,
}) {
  on("home-prepare-documentation-closeout-plan", "click", async () => {
    try {
      setMessage("projects-message", "Preparing local Documentation Closeout Plan...", "loading");
      await prepareDocumentationCloseoutPlanForState();
      await loadDocumentationCloseoutPlanForState(activeProjectId());
      await loadProjectFactoryDossier(activeProjectId());
      await refreshSummaryAndReport();
      setMessage("projects-message", "Documentation closeout plan prepared locally.", "success");
    } catch (error) {
      setMessage("projects-message", String(error.message || error), "error");
    }
  });

  on("documentation-closeout-plan-save-draft", "click", async () => {
    try {
      setMessage("projects-message", "Saving local Documentation Closeout Plan draft...", "loading");
      await saveDocumentationCloseoutPlanDraftForState();
      await loadDocumentationCloseoutPlanForState(activeProjectId());
      await loadProjectFactoryDossier(activeProjectId());
      await refreshSummaryAndReport();
      setMessage("projects-message", "Documentation closeout plan draft saved.", "success");
    } catch (error) {
      setMessage("projects-message", String(error.message || error), "error");
    }
  });

  on("documentation-closeout-plan-approve", "click", async () => {
    try {
      setMessage("projects-message", "Approving local Documentation Closeout Plan...", "loading");
      await approveDocumentationCloseoutPlanForState();
      await loadDocumentationCloseoutPlanForState(activeProjectId());
      await loadProjectFactoryDossier(activeProjectId());
      await refreshSummaryAndReport();
      setMessage("projects-message", "Documentation closeout plan approved.", "success");
    } catch (error) {
      setMessage("projects-message", String(error.message || error), "error");
    }
  });
}
