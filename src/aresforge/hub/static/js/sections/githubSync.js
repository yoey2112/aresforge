import { byId, on, setList, setMessage, setText } from "/js/core/dom.js";
import { fetchJson, toQuery } from "/js/core/http.js";

function sourceLine(source) {
  if (!source) return "unknown";
  const status = source.sync_status || source.status || "unknown";
  return `${source.source_id || source.record_type || "source"} | ${status} | mutation=${Boolean(source.mutation_performed)}`;
}

function registryLines(records) {
  return (records || []).map((record) => {
    const issue = record.issue_number ? `issue #${record.issue_number}` : "issue none";
    const pr = record.pr_number ? `PR #${record.pr_number}` : "PR none";
    return `${record.queue_item_id || record.item_id || "item"} | ${issue} | ${pr} | ${record.sync_status || "unknown"}`;
  });
}

function issuePlanLines(items) {
  return (items || []).map((item) => {
    return `${item.item_id || "item"} | ${item.sync_status || "planned"} | issue=${item.issue_number || "none"}`;
  });
}

function recoveryLines(plans) {
  return (plans || []).map((plan) => {
    return `${plan.operation_type || "operation"} | ${plan.item_id || "item"} | ${plan.sync_status || "review"}`;
  });
}

function actionLines(actions) {
  return (actions || []).map((action) => {
    return `${action.label || action.action_id || "review"} | ${action.sync_status || "dry_run"} | github=${Boolean(action.github_enabled)}`;
  });
}

function boundaryLines(boundary) {
  const blocked = boundary && Array.isArray(boundary.blocked_operations) ? boundary.blocked_operations : [];
  return [
    `dry_run_default=${Boolean(boundary && boundary.dry_run_default)}`,
    `unsafe_default_execute_buttons=${Boolean(boundary && boundary.unsafe_default_execute_buttons)}`,
    `blocked_operations=${blocked.join(", ")}`,
  ];
}

export function renderGitHubSyncControlPanel(payload) {
  const registry = payload && payload.link_registry ? payload.link_registry : {};
  const issueSync = payload && payload.issue_sync_plans ? payload.issue_sync_plans : {};
  const reconciliation = payload && payload.reconciliation ? payload.reconciliation : {};
  const recovery = payload && payload.recovery_actions ? payload.recovery_actions : {};

  setText("github-sync-status", (payload && payload.sync_status) || (payload && payload.status) || "unknown");
  setText("github-sync-repository", (payload && payload.repository) || "unknown");
  setText("github-sync-issue", payload && payload.issue_number ? `#${payload.issue_number}` : "none");
  setText("github-sync-pr", payload && payload.pr_number ? `#${payload.pr_number}` : "none");
  setText("github-sync-next-safe-action", (payload && payload.next_safe_action) || "Review dry-run sync evidence.");

  setList("github-sync-sources", "github-sync-sources-empty", [
    sourceLine(registry),
    sourceLine(issueSync),
    sourceLine(payload && payload.status_comments),
    sourceLine(reconciliation),
    sourceLine(payload && payload.closure_gates),
    sourceLine(payload && payload.pr_draft_plans),
    sourceLine(payload && payload.pr_evidence_comments),
    sourceLine(recovery),
  ]);
  setList("github-sync-registry", "github-sync-registry-empty", registryLines(registry.records || []));
  setList("github-sync-issue-plans", "github-sync-issue-plans-empty", issuePlanLines(issueSync.items || []));
  setList("github-sync-reconciliation", "github-sync-reconciliation-empty", issuePlanLines(reconciliation.items || []));
  setList("github-sync-recovery", "github-sync-recovery-empty", [
    ...recoveryLines(recovery.resume_plan || []),
    ...recoveryLines(recovery.repair_plan || []),
  ]);
  setList("github-sync-safe-actions", "github-sync-safe-actions-empty", actionLines((payload && payload.next_safe_actions) || []));
  setList("github-sync-boundaries", "github-sync-boundaries-empty", boundaryLines(payload && payload.safety_boundaries));
  setList("github-sync-warnings", "github-sync-warnings-empty", (payload && payload.warnings) || []);
  setList("github-sync-blockers", "github-sync-blockers-empty", (payload && payload.blocked_reasons) || []);
}

export async function loadGitHubSyncControlPanel(filters) {
  setMessage("github-sync-message", "Loading GitHub sync control panel...", "loading");
  const payload = await fetchJson(`/api/github-sync/control-panel${toQuery(filters || {})}`, { method: "GET" });
  renderGitHubSyncControlPanel(payload);
  setMessage("github-sync-message", "GitHub sync control panel loaded. Live mutations remain separate and gated.", "success");
  return payload;
}

export function bindGitHubSyncActions({ loadGitHubSyncControlPanelForState }) {
  on("github-sync-form", "submit", async (event) => {
    event.preventDefault();
    try {
      await loadGitHubSyncControlPanelForState({
        project_id: byId("github-sync-project-id").value.trim(),
        item_id: byId("github-sync-item-id").value.trim(),
        repo: byId("github-sync-repo").value.trim(),
        autonomy_profile: byId("github-sync-autonomy-profile").value.trim(),
      });
    } catch (error) {
      setMessage("github-sync-message", String(error.message || error), "error");
    }
  });

  on("github-sync-reset", "click", async () => {
    byId("github-sync-project-id").value = "aresforge";
    byId("github-sync-item-id").value = "m180-hub-github-sync-control-panel";
    byId("github-sync-repo").value = "";
    byId("github-sync-autonomy-profile").value = "github_sync_dry_run";
    try {
      await loadGitHubSyncControlPanelForState({
        project_id: "aresforge",
        item_id: "m180-hub-github-sync-control-panel",
        autonomy_profile: "github_sync_dry_run",
      });
    } catch (error) {
      setMessage("github-sync-message", String(error.message || error), "error");
    }
  });
}
