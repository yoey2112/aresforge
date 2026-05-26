import { byId, on, setList, setMessage } from "/js/core/dom.js";
import { fetchJson, prunePayload } from "/js/core/http.js";

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

export function renderEscalationPlan(plan) {
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

export async function loadEscalationPlan(filters, usePost) {
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

export function bindEscalationActions({ loadEscalationPlanForState, refreshSummaryAndReport }) {
  on("escalation-form", "submit", async (event) => {
    event.preventDefault();
    try {
      await loadEscalationPlanForState(
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
      await loadEscalationPlanForState({}, false);
      await refreshSummaryAndReport();
    } catch (error) {
      setMessage("escalation-message", String(error.message || error), "error");
    }
  });
}
