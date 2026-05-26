import { byId, on, setList, setMessage } from "/js/core/dom.js";
import { fetchJson, prunePayload, toQuery } from "/js/core/http.js";

export async function prepareScopePackage(activeProjectId) {
  const payload = await fetchJson("/api/project-factory/scope-package", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(prunePayload({ project_id: activeProjectId() })),
  });
  return payload;
}

export function buildScopeAuthoringPayload({ activeProjectId, parseLineList }) {
  return prunePayload({
    project_id: activeProjectId(),
    requirements: parseLineList(byId("scope-requirements").value),
    constraints: parseLineList(byId("scope-constraints").value),
    assumptions: parseLineList(byId("scope-assumptions").value),
    acceptance_criteria: parseLineList(byId("scope-acceptance-criteria").value),
    risks: parseLineList(byId("scope-risks").value),
    out_of_scope: parseLineList(byId("scope-out-of-scope").value),
    stakeholders: parseLineList(byId("scope-stakeholders").value),
    notes: byId("scope-notes").value.trim(),
  });
}

export function renderScopeAuthoring(state, payload, { toTextareaList }) {
  state.scopePackage = payload || null;
  const message = byId("home-scope-authoring-message");
  const stateLine = byId("home-scope-authoring-state");
  const scopeExists = Boolean(payload && payload.scope_package_exists);
  const scopePackage = (payload && payload.scope_package) || {};
  if (!scopeExists) {
    byId("scope-requirements").value = "";
    byId("scope-constraints").value = "";
    byId("scope-assumptions").value = "";
    byId("scope-acceptance-criteria").value = "";
    byId("scope-risks").value = "";
    byId("scope-out-of-scope").value = "";
    byId("scope-stakeholders").value = "";
    byId("scope-notes").value = "";
    setList("home-scope-audit-trail", "home-scope-audit-trail-empty", []);
    if (message) {
      message.textContent = "No scope package found. Use Prepare Scope Package first for the active project.";
    }
    if (stateLine) {
      stateLine.textContent = "Scope lifecycle state: not_started";
    }
    return;
  }

  byId("scope-requirements").value = toTextareaList(scopePackage.requirements);
  byId("scope-constraints").value = toTextareaList(scopePackage.constraints);
  byId("scope-assumptions").value = toTextareaList(scopePackage.assumptions);
  byId("scope-acceptance-criteria").value = toTextareaList(scopePackage.acceptance_criteria);
  byId("scope-risks").value = toTextareaList(scopePackage.risks);
  byId("scope-out-of-scope").value = toTextareaList(scopePackage.out_of_scope);
  byId("scope-stakeholders").value = toTextareaList(scopePackage.stakeholders);
  byId("scope-notes").value = String(scopePackage.notes || "");
  setList(
    "home-scope-audit-trail",
    "home-scope-audit-trail-empty",
    (scopePackage.audit_trail || []).map((entry) => `${entry.timestamp || "-"} | ${entry.event_type || "-"} | state=${entry.lifecycle_state || "-"} | actor=${entry.actor || "-"}`),
  );
  if (message) {
    message.textContent = "Scope authoring is local-only. No GitHub or model execution is triggered.";
  }
  if (stateLine) {
    stateLine.textContent = `Scope lifecycle state: ${scopePackage.lifecycle_state || "not_started"}`;
  }
}

export async function loadScopePackage(projectId, { renderScopeAuthoringForState }) {
  const query = toQuery({ project_id: projectId || "" });
  const payload = await fetchJson(`/api/project-factory/scope-package${query}`, { method: "GET" });
  renderScopeAuthoringForState(payload);
  return payload;
}

export async function saveScopeDraft(buildScopeAuthoringPayloadForState) {
  const payload = await fetchJson("/api/project-factory/scope-package", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(buildScopeAuthoringPayloadForState()),
  });
  return payload;
}

export async function approveScope(activeProjectId) {
  const payload = await fetchJson("/api/project-factory/scope-package/approve", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(prunePayload({ project_id: activeProjectId() })),
  });
  return payload;
}

export function bindProjectFactoryScopeActions({
  activeProjectId,
  prepareScopePackageForState,
  saveScopeDraftForState,
  approveScopeForState,
  loadProjectFactoryDossier,
  loadScopePackageForState,
  loadArchitectureContractForState,
  refreshSummaryAndReport,
}) {
  on("home-prepare-scope-package", "click", async () => {
    try {
      setMessage("projects-message", "Preparing local scope package placeholder...", "loading");
      await prepareScopePackageForState();
      await loadProjectFactoryDossier(activeProjectId());
      await loadScopePackageForState(activeProjectId());
      await refreshSummaryAndReport();
      setMessage("projects-message", "Scope package prepared locally.", "success");
    } catch (error) {
      setMessage("projects-message", String(error.message || error), "error");
    }
  });

  on("scope-save-draft", "click", async () => {
    try {
      setMessage("projects-message", "Saving local scope draft...", "loading");
      await saveScopeDraftForState();
      await loadScopePackageForState(activeProjectId());
      await loadProjectFactoryDossier(activeProjectId());
      await refreshSummaryAndReport();
      setMessage("projects-message", "Scope draft saved.", "success");
    } catch (error) {
      setMessage("projects-message", String(error.message || error), "error");
    }
  });

  on("scope-approve", "click", async () => {
    try {
      setMessage("projects-message", "Approving local scope package...", "loading");
      await approveScopeForState();
      await loadScopePackageForState(activeProjectId());
      await loadProjectFactoryDossier(activeProjectId());
      await loadArchitectureContractForState(activeProjectId());
      await refreshSummaryAndReport();
      setMessage("projects-message", "Scope approved.", "success");
    } catch (error) {
      setMessage("projects-message", String(error.message || error), "error");
    }
  });
}
