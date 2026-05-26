import { byId, on, setList, setMessage } from "/js/core/dom.js";
import { fetchJson, prunePayload } from "/js/core/http.js";

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

export function renderOrchestrationPlan(plan) {
  setList("orchestration-assignments", "orchestration-assignments-empty", assignmentLines(plan.recommended_assignments));
  setList("orchestration-dependency-order", "orchestration-dependency-empty", plan.dependency_order || []);
  setList("orchestration-blocked", "orchestration-blocked-empty", blockedLines(plan.blocked_items));
  setList("orchestration-unassigned", "orchestration-unassigned-empty", blockedLines(plan.unassigned_items));
  setList("orchestration-prompts", "orchestration-prompts-empty", promptLines(plan.handoff_prompts));
  setList("orchestration-risks", "orchestration-risks-empty", plan.risk_warnings || []);
  setList("orchestration-actions", "orchestration-actions-empty", plan.next_actions || []);
}

export async function loadOrchestrationPlan(filters, usePost) {
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

export function bindOrchestrationActions({ loadOrchestrationPlanForState, refreshSummaryAndReport }) {
  on("orchestration-form", "submit", async (event) => {
    event.preventDefault();
    try {
      await loadOrchestrationPlanForState(
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
      await loadOrchestrationPlanForState({}, false);
      await refreshSummaryAndReport();
    } catch (error) {
      setMessage("orchestration-message", String(error.message || error), "error");
    }
  });
}
