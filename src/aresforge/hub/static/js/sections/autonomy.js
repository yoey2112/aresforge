import { byId, on, setList, setMessage, setText } from "/js/core/dom.js";
import { fetchJson, toQuery } from "/js/core/http.js";

function gateLines(gates) {
  return (gates || []).map((gate) => {
    const status = gate.passed ? "passed" : "blocked";
    return `${gate.gate_profile || "gate"}: ${status}`;
  });
}

function runLines(runs) {
  return (runs || []).map((run) => `${run.run_id || "run"} | ${run.item_id || "item"} | ${run.status || "unknown"}`);
}

function evidenceLines(entries) {
  return (entries || []).map((entry) => `${entry.record_type || entry.artifact_type || "artifact"} | ${entry.status || "unknown"} | ${entry.path || ""}`);
}

function recommendationLines(entries) {
  return (entries || []).map((entry) => {
    return `${entry.recommended_action || "review"} | ${entry.item_id || "item"} | ${entry.reason || "dry-run only"}`;
  });
}

function actionLines(actions) {
  return (actions || []).map((action) => `${action.label || action.action_id || "review"} | dry_run=${Boolean(action.dry_run)}`);
}

export function renderAutonomyControlCenter(payload) {
  const profile = payload && payload.autonomy_profile_summary ? payload.autonomy_profile_summary : {};
  const runStore = payload && payload.run_store_status ? payload.run_store_status : {};
  const github = payload && payload.github_sync_status ? payload.github_sync_status : {};
  const closure = payload && payload.issue_closure_recommendations ? payload.issue_closure_recommendations : {};

  setText("autonomy-status", (payload && payload.status) || "unknown");
  setText("autonomy-profile", profile.autonomy_profile || (payload && payload.autonomy_profile) || "unknown");
  setText("autonomy-run-store", `${runStore.status || "unknown"} | runs=${runStore.project_run_count || 0}`);
  setText("autonomy-github-sync", `${github.status || "unknown"} | mutation_allowed=false`);
  setText("autonomy-closure", `${closure.status || "unknown"} | closure_allowed=false`);
  setText("autonomy-next-safe-action", (payload && payload.next_safe_action) || "Review local autonomy status.");

  setList("autonomy-gates", "autonomy-gates-empty", gateLines((payload && payload.machine_gates_checked) || []));
  setList("autonomy-runs", "autonomy-runs-empty", runLines((payload && payload.orchestration_runs) || []));
  setList("autonomy-evidence", "autonomy-evidence-empty", evidenceLines((payload && payload.evidence_bundles) || []));
  setList("autonomy-pr-drafts", "autonomy-pr-drafts-empty", evidenceLines((payload && payload.pr_draft_summaries) || []));
  setList("autonomy-github-recommendations", "autonomy-github-recommendations-empty", recommendationLines((github && github.operation_recommendations) || []));
  setList("autonomy-safe-actions", "autonomy-safe-actions-empty", actionLines((payload && payload.next_safe_actions) || []));
  setList("autonomy-warnings", "autonomy-warnings-empty", (payload && payload.warnings) || []);
  setList("autonomy-blockers", "autonomy-blockers-empty", (payload && payload.blocked_reasons) || []);
}

export async function loadAutonomyControlCenter(filters) {
  setMessage("autonomy-message", "Loading autonomy control center data...", "loading");
  const payload = await fetchJson(`/api/autonomy/control-center${toQuery(filters || {})}`, { method: "GET" });
  renderAutonomyControlCenter(payload);
  setMessage("autonomy-message", "Autonomy control center loaded. All high-risk actions remain dry-run or blocked.", "success");
  return payload;
}

export function bindAutonomyActions({ loadAutonomyControlCenterForState }) {
  on("autonomy-form", "submit", async (event) => {
    event.preventDefault();
    try {
      await loadAutonomyControlCenterForState({
        project_id: byId("autonomy-project-id").value.trim(),
        item_id: byId("autonomy-item-id").value.trim(),
        run_id: byId("autonomy-run-id").value.trim(),
        autonomy_profile: byId("autonomy-profile-input").value.trim(),
      });
    } catch (error) {
      setMessage("autonomy-message", String(error.message || error), "error");
    }
  });

  on("autonomy-reset", "click", async () => {
    byId("autonomy-project-id").value = "aresforge";
    byId("autonomy-item-id").value = "m167-hub-autonomy-control-center-v1";
    byId("autonomy-run-id").value = "";
    byId("autonomy-profile-input").value = "github_sync_dry_run";
    try {
      await loadAutonomyControlCenterForState({
        project_id: "aresforge",
        item_id: "m167-hub-autonomy-control-center-v1",
        autonomy_profile: "github_sync_dry_run",
      });
    } catch (error) {
      setMessage("autonomy-message", String(error.message || error), "error");
    }
  });
}
