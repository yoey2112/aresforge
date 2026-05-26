import { byId, on, setList, setMessage } from "/js/core/dom.js";
import { fetchJson, prunePayload, toQuery } from "/js/core/http.js";

export function buildArchitectureAuthoringPayload({ activeProjectId, parseLineList }) {
  return prunePayload({
    project_id: activeProjectId(),
    architecture_summary: byId("architecture-summary").value.trim(),
    system_components: parseLineList(byId("architecture-system-components").value),
    data_model_notes: parseLineList(byId("architecture-data-model-notes").value),
    integration_points: parseLineList(byId("architecture-integration-points").value),
    security_considerations: parseLineList(byId("architecture-security-considerations").value),
    deployment_notes: parseLineList(byId("architecture-deployment-notes").value),
    testing_strategy: parseLineList(byId("architecture-testing-strategy").value),
    documentation_plan: parseLineList(byId("architecture-documentation-plan").value),
    open_questions: parseLineList(byId("architecture-open-questions").value),
    milestone_planning_notes: byId("architecture-milestone-planning-notes").value.trim(),
  });
}

export function renderArchitectureAuthoring(state, payload, { toTextareaList }) {
  state.architectureContract = payload || null;
  const message = byId("home-architecture-authoring-message");
  const stateLine = byId("home-architecture-authoring-state");
  const exists = Boolean(payload && payload.architecture_contract_exists);
  const contract = (payload && payload.architecture_contract) || {};
  if (!exists) {
    byId("architecture-summary").value = "";
    byId("architecture-system-components").value = "";
    byId("architecture-data-model-notes").value = "";
    byId("architecture-integration-points").value = "";
    byId("architecture-security-considerations").value = "";
    byId("architecture-deployment-notes").value = "";
    byId("architecture-testing-strategy").value = "";
    byId("architecture-documentation-plan").value = "";
    byId("architecture-open-questions").value = "";
    byId("architecture-milestone-planning-notes").value = "";
    setList("home-architecture-audit-trail", "home-architecture-audit-trail-empty", []);
    if (message) {
      message.textContent = "No architecture contract found. Approve scope first, then prepare architecture contract.";
    }
    if (stateLine) {
      stateLine.textContent = "Architecture lifecycle state: not_started";
    }
    return;
  }

  byId("architecture-summary").value = String(contract.architecture_summary || "");
  byId("architecture-system-components").value = toTextareaList(contract.system_components);
  byId("architecture-data-model-notes").value = toTextareaList(contract.data_model_notes);
  byId("architecture-integration-points").value = toTextareaList(contract.integration_points);
  byId("architecture-security-considerations").value = toTextareaList(contract.security_considerations);
  byId("architecture-deployment-notes").value = toTextareaList(contract.deployment_notes);
  byId("architecture-testing-strategy").value = toTextareaList(contract.testing_strategy);
  byId("architecture-documentation-plan").value = toTextareaList(contract.documentation_plan);
  byId("architecture-open-questions").value = toTextareaList(contract.open_questions);
  byId("architecture-milestone-planning-notes").value = String(contract.milestone_planning_notes || "");
  setList(
    "home-architecture-audit-trail",
    "home-architecture-audit-trail-empty",
    (contract.audit_trail || []).map((entry) => `${entry.timestamp || "-"} | ${entry.event_type || "-"} | state=${entry.lifecycle_state || "-"} | actor=${entry.actor || "-"}`),
  );
  if (message) {
    message.textContent = "Architecture authoring is local-only. No GitHub or model execution is triggered.";
  }
  if (stateLine) {
    stateLine.textContent = `Architecture lifecycle state: ${contract.lifecycle_state || "not_started"}`;
  }
}

export async function loadArchitectureContract(projectId, { renderArchitectureAuthoringForState }) {
  const query = toQuery({ project_id: projectId || "" });
  const payload = await fetchJson(`/api/project-factory/architecture-contract${query}`, { method: "GET" });
  renderArchitectureAuthoringForState(payload);
  return payload;
}

export async function prepareArchitectureContract(activeProjectId) {
  const payload = await fetchJson("/api/project-factory/architecture-contract", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(prunePayload({ project_id: activeProjectId() })),
  });
  return payload;
}

export async function saveArchitectureDraft(buildArchitectureAuthoringPayloadForState) {
  const payload = await fetchJson("/api/project-factory/architecture-contract", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(buildArchitectureAuthoringPayloadForState()),
  });
  return payload;
}

export async function approveArchitecture(activeProjectId) {
  const payload = await fetchJson("/api/project-factory/architecture-contract/approve", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(prunePayload({ project_id: activeProjectId() })),
  });
  return payload;
}

export function bindProjectFactoryArchitectureActions({
  activeProjectId,
  prepareArchitectureContractForState,
  saveArchitectureDraftForState,
  approveArchitectureForState,
  loadArchitectureContractForState,
  loadProjectFactoryDossier,
  loadMilestoneIssuePlan,
  loadGithubApplyPlan,
  refreshSummaryAndReport,
}) {
  on("home-prepare-architecture-contract", "click", async () => {
    try {
      setMessage("projects-message", "Preparing local architecture contract placeholder...", "loading");
      await prepareArchitectureContractForState();
      await loadArchitectureContractForState(activeProjectId());
      await loadProjectFactoryDossier(activeProjectId());
      await refreshSummaryAndReport();
      setMessage("projects-message", "Architecture contract prepared locally.", "success");
    } catch (error) {
      setMessage("projects-message", String(error.message || error), "error");
    }
  });

  on("architecture-save-draft", "click", async () => {
    try {
      setMessage("projects-message", "Saving local architecture draft...", "loading");
      await saveArchitectureDraftForState();
      await loadArchitectureContractForState(activeProjectId());
      await loadProjectFactoryDossier(activeProjectId());
      await refreshSummaryAndReport();
      setMessage("projects-message", "Architecture draft saved.", "success");
    } catch (error) {
      setMessage("projects-message", String(error.message || error), "error");
    }
  });

  on("architecture-approve", "click", async () => {
    try {
      setMessage("projects-message", "Approving local architecture contract...", "loading");
      await approveArchitectureForState();
      await loadArchitectureContractForState(activeProjectId());
      await loadProjectFactoryDossier(activeProjectId());
      await loadMilestoneIssuePlan(activeProjectId());
      await loadGithubApplyPlan(activeProjectId());
      await refreshSummaryAndReport();
      setMessage("projects-message", "Architecture approved.", "success");
    } catch (error) {
      setMessage("projects-message", String(error.message || error), "error");
    }
  });
}
