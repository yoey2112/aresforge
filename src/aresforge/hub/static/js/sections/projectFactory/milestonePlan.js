import { byId, on, setList, setMessage } from "/js/core/dom.js";
import { fetchJson, prunePayload, toQuery } from "/js/core/http.js";

function parseJsonArray(text, fieldName) {
  const raw = String(text || "").trim();
  if (!raw) {
    return [];
  }
  let decoded;
  try {
    decoded = JSON.parse(raw);
  } catch (_error) {
    throw new Error(`${fieldName} must be valid JSON array.`);
  }
  if (!Array.isArray(decoded)) {
    throw new Error(`${fieldName} must be a JSON array.`);
  }
  return decoded;
}

export function buildMilestoneIssuePlanPayload({ activeProjectId, parseLineList }) {
  return prunePayload({
    project_id: activeProjectId(),
    planning_summary: byId("milestone-plan-summary").value.trim(),
    milestones: parseJsonArray(byId("milestone-plan-milestones").value, "milestones"),
    issues: parseJsonArray(byId("milestone-plan-issues").value, "issues"),
    cross_cutting_tasks: parseLineList(byId("milestone-plan-cross-cutting-tasks").value),
    validation_plan: parseLineList(byId("milestone-plan-validation-plan").value),
    documentation_plan: parseLineList(byId("milestone-plan-documentation-plan").value),
    release_notes: parseLineList(byId("milestone-plan-release-notes").value),
    open_questions: parseLineList(byId("milestone-plan-open-questions").value),
    github_apply_notes: byId("milestone-plan-github-apply-notes").value.trim(),
  });
}

export function renderMilestoneIssuePlan(state, payload, { toTextareaList }) {
  state.milestoneIssuePlan = payload || null;
  const message = byId("home-milestone-plan-message");
  const stateLine = byId("home-milestone-plan-state");
  const exists = Boolean(payload && payload.milestone_issue_plan_exists);
  const plan = (payload && payload.milestone_issue_plan) || {};
  if (!exists) {
    byId("milestone-plan-summary").value = "";
    byId("milestone-plan-milestones").value = "";
    byId("milestone-plan-issues").value = "";
    byId("milestone-plan-cross-cutting-tasks").value = "";
    byId("milestone-plan-validation-plan").value = "";
    byId("milestone-plan-documentation-plan").value = "";
    byId("milestone-plan-release-notes").value = "";
    byId("milestone-plan-open-questions").value = "";
    byId("milestone-plan-github-apply-notes").value = "";
    setList("home-milestone-plan-audit-trail", "home-milestone-plan-audit-trail-empty", []);
    if (message) {
      message.textContent = "No milestone/issue plan found. Approve architecture first, then prepare milestone/issue plan.";
    }
    if (stateLine) {
      stateLine.textContent = "Milestone/Issue Plan lifecycle state: not_started";
    }
    return;
  }
  byId("milestone-plan-summary").value = String(plan.planning_summary || "");
  byId("milestone-plan-milestones").value = JSON.stringify(Array.isArray(plan.milestones) ? plan.milestones : [], null, 2);
  byId("milestone-plan-issues").value = JSON.stringify(Array.isArray(plan.issues) ? plan.issues : [], null, 2);
  byId("milestone-plan-cross-cutting-tasks").value = toTextareaList(plan.cross_cutting_tasks);
  byId("milestone-plan-validation-plan").value = toTextareaList(plan.validation_plan);
  byId("milestone-plan-documentation-plan").value = toTextareaList(plan.documentation_plan);
  byId("milestone-plan-release-notes").value = toTextareaList(plan.release_notes);
  byId("milestone-plan-open-questions").value = toTextareaList(plan.open_questions);
  byId("milestone-plan-github-apply-notes").value = String(plan.github_apply_notes || "");
  setList(
    "home-milestone-plan-audit-trail",
    "home-milestone-plan-audit-trail-empty",
    (plan.audit_trail || []).map((entry) => `${entry.timestamp || "-"} | ${entry.event_type || "-"} | state=${entry.lifecycle_state || "-"} | actor=${entry.actor || "-"}`),
  );
  if (message) {
    message.textContent = "Milestone/issue planning is local-only. No GitHub or model execution is triggered.";
  }
  if (stateLine) {
    stateLine.textContent = `Milestone/Issue Plan lifecycle state: ${plan.lifecycle_state || "not_started"}`;
  }
}

export async function loadMilestoneIssuePlan(projectId, { renderMilestoneIssuePlanForState }) {
  const query = toQuery({ project_id: projectId || "" });
  const payload = await fetchJson(`/api/project-factory/milestone-issue-plan${query}`, { method: "GET" });
  renderMilestoneIssuePlanForState(payload);
  return payload;
}

export async function prepareMilestoneIssuePlan(activeProjectId) {
  const payload = await fetchJson("/api/project-factory/milestone-issue-plan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(prunePayload({ project_id: activeProjectId() })),
  });
  return payload;
}

export async function saveMilestoneIssuePlanDraft(buildMilestoneIssuePlanPayloadForState) {
  const payload = await fetchJson("/api/project-factory/milestone-issue-plan", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(buildMilestoneIssuePlanPayloadForState()),
  });
  return payload;
}

export async function approveMilestoneIssuePlan(activeProjectId) {
  const payload = await fetchJson("/api/project-factory/milestone-issue-plan/approve", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(prunePayload({ project_id: activeProjectId() })),
  });
  return payload;
}

export function bindProjectFactoryMilestonePlanActions({
  activeProjectId,
  prepareMilestoneIssuePlanForState,
  saveMilestoneIssuePlanDraftForState,
  approveMilestoneIssuePlanForState,
  loadMilestoneIssuePlanForState,
  loadGithubApplyPlan,
  loadProjectFactoryDossier,
  refreshSummaryAndReport,
}) {
  on("home-prepare-milestone-issue-plan", "click", async () => {
    try {
      setMessage("projects-message", "Preparing local milestone/issue plan placeholder...", "loading");
      await prepareMilestoneIssuePlanForState();
      await loadMilestoneIssuePlanForState(activeProjectId());
      await loadGithubApplyPlan(activeProjectId());
      await loadProjectFactoryDossier(activeProjectId());
      await refreshSummaryAndReport();
      setMessage("projects-message", "Milestone/issue plan prepared locally.", "success");
    } catch (error) {
      setMessage("projects-message", String(error.message || error), "error");
    }
  });

  on("milestone-plan-save-draft", "click", async () => {
    try {
      setMessage("projects-message", "Saving local milestone/issue plan draft...", "loading");
      await saveMilestoneIssuePlanDraftForState();
      await loadMilestoneIssuePlanForState(activeProjectId());
      await loadGithubApplyPlan(activeProjectId());
      await loadProjectFactoryDossier(activeProjectId());
      await refreshSummaryAndReport();
      setMessage("projects-message", "Milestone/issue plan draft saved.", "success");
    } catch (error) {
      setMessage("projects-message", String(error.message || error), "error");
    }
  });

  on("milestone-plan-approve", "click", async () => {
    try {
      setMessage("projects-message", "Approving local milestone/issue plan...", "loading");
      await approveMilestoneIssuePlanForState();
      await loadMilestoneIssuePlanForState(activeProjectId());
      await loadGithubApplyPlan(activeProjectId());
      await loadProjectFactoryDossier(activeProjectId());
      await refreshSummaryAndReport();
      setMessage("projects-message", "Milestone/issue plan approved.", "success");
    } catch (error) {
      setMessage("projects-message", String(error.message || error), "error");
    }
  });
}
