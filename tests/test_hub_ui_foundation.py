import re
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.hub.api import (
    get_active_project_workspace,
    get_bootstrap_plan,
    get_bootstrap_status,
    get_agent,
    get_agents,
    get_docs_status,
    get_escalation_plan,
    get_health,
    get_handoff_preview,
    get_handoff_target,
    get_handoff_targets,
    get_local_queue_agent_summary,
    get_orchestration_plan,
    get_project,
    get_project_repo_github_link,
    get_project_repos,
    get_reports_action_center,
    get_reports_dashboard,
    get_reports_export,
    get_reports_operator_workflows,
    get_reports_readiness,
    get_projects,
    get_queue,
    get_queue_item,
    get_settings,
    get_summary,
    patch_queue_item,
    post_active_project,
    post_agent,
    post_bootstrap_apply,
    post_escalation_plan,
    post_handoff_target,
    post_orchestration_plan,
    post_project,
    post_project_repo,
    post_queue_item,
)


NAV_LABELS = [
    "Home",
    "Bootstrap",
    "Workspace",
    "Projects",
    "Repos",
    "Queue",
    "Agents",
    "Handoff",
    "Orchestration",
    "Escalation",
    "Reports",
    "Settings",
]


def _config(tmp_path: Path) -> AppConfig:
    artifact_root = tmp_path / "artifacts"
    return AppConfig(
        repo_root=tmp_path,
        db_host="127.0.0.1",
        db_port=5433,
        db_name="aresforge",
        db_user="aresforge",
        db_password="aresforge",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="qwen2.5:32b",
        artifact_root=artifact_root,
        prompts_dir=artifact_root / "prompts" / "generated",
        evidence_dir=artifact_root / "evidence" / "generated",
        codex_handoffs_dir=artifact_root / "codex_handoffs" / "generated",
        github_owner="local",
        github_repo="aresforge",
    )


def _static_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "src" / "aresforge" / "hub" / "static"


def _frontend_script_texts() -> dict[str, str]:
    static_dir = _static_dir()
    return {
        str(path.relative_to(static_dir)).replace("\\", "/"): path.read_text(encoding="utf-8")
        for path in sorted(static_dir.rglob("*.js"))
    }


def _combined_frontend_script_text() -> str:
    return "\n".join(_frontend_script_texts().values())


def _seed_project(config: AppConfig, project_id: str = "p1") -> None:
    payload = post_project(
        config,
        {
            "project_id": project_id,
            "name": "Project One",
            "root_path": str(config.repo_root),
            "status": "active",
            "default_branch": "main",
            "github_owner": "example-org",
            "github_repo": "sample-repo",
            "github_default_branch": "main",
            "tags": ["local"],
            "notes": "seed",
        },
    )
    assert payload["ok"] is True


def _seed_repo(config: AppConfig, project_id: str = "p1", repo_id: str = "r1") -> None:
    payload = post_project_repo(
        config,
        project_id,
        {
            "repo_id": repo_id,
            "name": "Repo One",
            "path": str(config.repo_root),
            "role": "primary",
            "status": "active",
            "github_owner": "example-org",
            "github_repo": "sample-repo",
            "github_default_branch": "main",
        },
    )
    assert payload["ok"] is True


def _seed_queue_item(config: AppConfig, item_id: str = "q1") -> None:
    _seed_project(config, "p1")
    _seed_repo(config, "p1", "r1")
    payload = post_queue_item(
        config,
        {
            "item_id": item_id,
            "project_id": "p1",
            "repo_id": "r1",
            "title": "Queue Item",
            "status": "ready",
            "priority": "high",
            "item_type": "task",
            "assigned_agent": "agent-a",
        },
    )
    assert payload["ok"] is True


def _seed_agent(config: AppConfig, agent_id: str = "agent-a") -> None:
    payload = post_agent(
        config,
        {
            "agent_id": agent_id,
            "name": "Agent A",
            "role": "implementer",
            "execution_mode": "codex",
            "status": "active",
            "escalation_allowed": True,
            "allowed_item_types": ["task", "feature"],
            "tags": ["m39"],
        },
    )
    assert payload["ok"] is True


def _seed_handoff_target(config: AppConfig, target_id: str = "target-a") -> None:
    payload = post_handoff_target(
        config,
        {
            "target_id": target_id,
            "name": "Target A",
            "target_type": "codex_prompt",
            "status": "active",
            "input_format": "markdown",
            "output_format": "patch",
            "tags": ["m39"],
        },
    )
    assert payload["ok"] is True


def test_hub_static_files_exist() -> None:
    static_dir = _static_dir()
    assert (static_dir / "index.html").exists()
    assert (static_dir / "app.js").exists()
    assert (static_dir / "js" / "core" / "dom.js").exists()
    assert (static_dir / "js" / "core" / "http.js").exists()
    assert (static_dir / "js" / "core" / "state.js").exists()
    assert (static_dir / "js" / "sections" / "home.js").exists()
    assert (static_dir / "js" / "sections" / "projects.js").exists()
    assert (static_dir / "js" / "sections" / "queue.js").exists()
    assert (static_dir / "js" / "sections" / "reports.js").exists()
    assert (static_dir / "js" / "sections" / "repos.js").exists()
    assert (static_dir / "js" / "sections" / "workspace.js").exists()
    assert (static_dir / "js" / "sections" / "orchestration.js").exists()
    assert (static_dir / "js" / "sections" / "escalation.js").exists()
    assert (static_dir / "js" / "sections" / "projectFactory" / "index.js").exists()
    assert (static_dir / "js" / "sections" / "projectFactory" / "scope.js").exists()
    assert (static_dir / "js" / "sections" / "projectFactory" / "architecture.js").exists()
    assert (static_dir / "js" / "sections" / "projectFactory" / "milestonePlan.js").exists()
    assert (static_dir / "js" / "sections" / "projectFactory" / "validation.js").exists()
    assert (static_dir / "js" / "sections" / "projectFactory" / "agentDispatch.js").exists()
    assert (static_dir / "js" / "sections" / "projectFactory" / "executionApproval.js").exists()
    assert (static_dir / "js" / "sections" / "projectFactory" / "closeout.js").exists()
    assert (static_dir / "styles.css").exists()


def test_index_loads_app_js_as_module_entrypoint() -> None:
    index_text = (_static_dir() / "index.html").read_text(encoding="utf-8")
    assert '<script type="module" src="/app.js"></script>' in index_text


def test_index_html_has_no_external_script_or_stylesheet_urls() -> None:
    index_text = (_static_dir() / "index.html").read_text(encoding="utf-8")
    assert "http://" not in index_text.lower()
    assert "https://" not in index_text.lower()
    assert "src=\"//" not in index_text.lower()
    assert "href=\"//" not in index_text.lower()


def test_app_js_imports_core_modules() -> None:
    app_text = (_static_dir() / "app.js").read_text(encoding="utf-8")
    assert 'from "/js/core/dom.js"' in app_text
    assert 'from "/js/core/http.js"' in app_text
    assert 'from "/js/core/state.js"' in app_text


def test_app_js_imports_section_modules() -> None:
    app_text = (_static_dir() / "app.js").read_text(encoding="utf-8")
    assert 'from "/js/sections/home.js"' in app_text
    assert 'from "/js/sections/projects.js"' in app_text
    assert 'from "/js/sections/queue.js"' in app_text
    assert 'from "/js/sections/reports.js"' in app_text
    assert 'from "/js/sections/repos.js"' in app_text
    assert 'from "/js/sections/workspace.js"' in app_text
    assert 'from "/js/sections/orchestration.js"' in app_text
    assert 'from "/js/sections/escalation.js"' in app_text
    assert 'from "/js/sections/projectFactory/index.js"' in app_text


def test_project_factory_index_exports_remaining_project_factory_modules() -> None:
    index_text = (_static_dir() / "js" / "sections" / "projectFactory" / "index.js").read_text(encoding="utf-8")
    assert 'from "/js/sections/projectFactory/milestonePlan.js"' in index_text
    assert 'from "/js/sections/projectFactory/validation.js"' in index_text
    assert 'from "/js/sections/projectFactory/agentDispatch.js"' in index_text
    assert 'from "/js/sections/projectFactory/executionApproval.js"' in index_text
    assert 'from "/js/sections/projectFactory/closeout.js"' in index_text


def test_index_contains_required_navigation_labels_and_m39_sections() -> None:
    index_text = (_static_dir() / "index.html").read_text(encoding="utf-8")
    for label in NAV_LABELS:
        assert label in index_text
    assert "Add Or Update Project" in index_text
    assert "Add Or Update Repo" in index_text
    assert "Add Or Update Queue Item" in index_text
    assert "Add Or Update Agent" in index_text
    assert "Add Or Update Handoff Target" in index_text
    assert "Refresh Handoff Preview" in index_text
    assert "Generate/view plan-only orchestration guidance" in index_text
    assert "Generate/view plan-only escalation classification" in index_text
    assert "Action Center Preview" in index_text
    assert "Quick Workflow Cards" in index_text
    assert "Refresh Summary" in index_text
    assert "Refresh Report" in index_text
    assert "Copy Report JSON" in index_text
    assert "Export JSON Text" in index_text
    assert "GitHub URL" in index_text
    assert "GitHub Owner" in index_text
    assert "GitHub Repo" in index_text
    assert "Inspect local git during save" in index_text
    assert "Inspect Local Git Link For Repo ID" in index_text
    assert "Bootstrap Setup" in index_text
    assert "Apply Bootstrap" in index_text
    assert "Seed sample work queue" in index_text
    assert "Force overwrite where safe" in index_text
    assert "Active Project Selector" in index_text
    assert "Active Project Workspace for local-only control-plane visibility and safe next actions." in index_text
    assert "Refresh Workspace" in index_text
    assert "Continue Task Intake" in index_text
    assert "Open Queue Lifecycle" in index_text
    assert "Select Active Project" in index_text
    assert "Workspace Summary" in index_text
    assert "Active Project Summary" in index_text
    assert "Current Queue Items" in index_text
    assert "Recent Completed Queue Items" in index_text
    assert "Workspace Warnings" in index_text
    assert "Set Active Project" in index_text
    assert "New Project Wizard" in index_text
    assert "Start New Project" in index_text
    assert "Create Local Project Factory Start" in index_text
    assert "Project Factory Dossier" in index_text
    assert "Scope Project Kickoff" in index_text
    assert "Prepare Scope Package" in index_text
    assert "Scope Authoring" in index_text
    assert "Save Scope Draft" in index_text
    assert "Approve Scope" in index_text
    assert "Architecture Contract" in index_text
    assert "Prepare Architecture Contract" in index_text
    assert "Save Architecture Draft" in index_text
    assert "Approve Architecture" in index_text
    assert "Milestone/Issue Plan" in index_text
    assert "Prepare Milestone/Issue Plan" in index_text
    assert "Save Plan Draft" in index_text
    assert "Approve Plan" in index_text
    assert "GitHub Apply Plan" in index_text
    assert "Prepare GitHub Apply Plan" in index_text
    assert "Save Apply Plan Draft" in index_text
    assert "Approve Apply Plan" in index_text
    assert "This is a local apply plan only. It does not create GitHub milestones or issues." in index_text
    assert "Agent Dispatch Plan" in index_text
    assert "Prepare Agent Dispatch Plan" in index_text
    assert "Save Dispatch Draft" in index_text
    assert "Approve Dispatch Plan" in index_text
    assert "This is a local dispatch plan only. It does not execute agents or models." in index_text
    assert "Validation Execution Plan" in index_text
    assert "Prepare Validation Execution Plan" in index_text
    assert "Save Validation Draft" in index_text
    assert "Approve Validation Plan" in index_text
    assert "This is a local validation plan only. It does not execute validation commands, agents, models, or GitHub actions." in index_text
    assert "Documentation Closeout Plan" in index_text
    assert "Prepare Documentation Closeout Plan" in index_text
    assert "Save Closeout Draft" in index_text
    assert "Approve Closeout Plan" in index_text
    assert "This is a local documentation closeout plan only. It does not update docs, execute validation, run agents/models, or perform GitHub actions." in index_text
    assert "Execution Phase Approval" in index_text
    assert "Prepare Execution Phase Approval" in index_text
    assert "Save Execution Approval Draft" in index_text
    assert "Approve Execution Phase Gate" in index_text
    assert "This is a local execution approval gate only. It does not execute GitHub mutations, validation commands, documentation updates, agents/models, or closeout." in index_text
    assert "Execution Readiness Control Center" in index_text
    assert "Refresh Execution Readiness" in index_text
    assert "Artifact Checklist" in index_text
    assert "Execution Lane Statuses" in index_text
    assert "wizard-project-name" in index_text
    assert "wizard-project-id" in index_text
    assert "wizard-project-type" in index_text
    assert "wizard-preferred-stack" in index_text
    assert "wizard-root-path" in index_text
    assert "wizard-github-owner" in index_text
    assert "wizard-github-repo" in index_text
    assert "wizard-github-mode" in index_text
    assert "wizard-default-branch" in index_text
    assert "wizard-description" in index_text
    assert "wizard-initial-requirements" in index_text
    assert "wizard-tags" in index_text
    assert "Active Project Queue Focus" in index_text
    assert "Use Active Project Defaults" in index_text
    assert "Filter To Active Project" in index_text
    assert "Local Queue Lifecycle" in index_text
    assert "Local-only and manual queue lifecycle controls: no automatic Codex execution, no agent execution, no GitHub sync/mutation." in index_text
    assert "Add Task" in index_text
    assert "Item ID is generated automatically from the title and active project context exposed by the local queue lifecycle API." in index_text
    assert "Task Lifecycle Controls" in index_text
    assert "Inspect Readiness" in index_text
    assert "Start Task" in index_text
    assert "Generate Codex Prompt" in index_text
    assert "Capture Completion Evidence" in index_text
    assert "Records local evidence on the queue item only. Does not complete or close out the item." in index_text
    assert "queue-lifecycle-evidence-form" in index_text
    assert "queue-lifecycle-evidence-summary" in index_text
    assert "queue-lifecycle-evidence-validation-commands" in index_text
    assert "queue-lifecycle-evidence-validation-results" in index_text
    assert "queue-lifecycle-evidence-smoke-checks" in index_text
    assert "queue-lifecycle-evidence-diff-check-result" in index_text
    assert "queue-lifecycle-evidence-files-changed" in index_text
    assert "queue-lifecycle-evidence-commit-hash" in index_text
    assert "queue-lifecycle-evidence-push-result" in index_text
    assert "queue-lifecycle-evidence-operator-notes" in index_text
    assert "queue-lifecycle-evidence-summary-list" in index_text
    assert "Complete With Evidence" in index_text
    assert "Implementation Commit" in index_text
    assert "Validation Summary" in index_text
    assert "Completion Notes" in index_text
    assert "queue-lifecycle-message" in index_text
    assert "queue-lifecycle-add-form" in index_text
    assert "queue-lifecycle-item-id" in index_text
    assert "queue-lifecycle-codex-form" in index_text
    assert "queue-lifecycle-complete-form" in index_text
    assert "queue-lifecycle-codex-prompt" in index_text
    assert "Active Project Report Focus" in index_text
    assert "settings-active-project-path" in index_text
    assert "Active Project Task Intake" in index_text
    assert "Create Local Queue Item" in index_text
    assert "Task Summary / Details" in index_text
    assert "intake-active-project-summary" in index_text
    assert "intake-result" in index_text
    assert "Projects Read-Only Overview" in index_text
    assert "projects-readonly-list" in index_text
    assert "Local-only and read-only project view: no project mutations, no GitHub sync/mutation, no agent/model execution." in index_text
    assert "Local Home Dashboard" in index_text
    assert "home-local-dashboard-last-loaded" in index_text
    assert "home-local-dashboard-error" in index_text
    assert "Total Projects" in index_text
    assert "Active Project" in index_text
    assert "Active Project Status" in index_text
    assert "Queue Item Count" in index_text
    assert "Total Advisory Agent Lanes" in index_text
    assert "Repo Availability" in index_text
    assert "Queue Status Summary" in index_text
    assert "Queue Status Drilldown (Advisory)" in index_text
    assert "Agent Lane Details" in index_text
    assert "Agent Lane Drilldown (Advisory)" in index_text
    assert "Repo Warnings" in index_text
    assert "Local Queue Read-Only Summary" in index_text
    assert "Total Queue Item Count" in index_text
    assert "Active Project Context" in index_text
    assert "Next Safe Action" in index_text
    assert "Counts By Status" in index_text
    assert "Grouped Queue Items" in index_text
    assert "Blocked Items" in index_text
    assert "Ready Items" in index_text
    assert "Queue Item Detail Panel" in index_text
    assert "Read-only/advisory detail panel. Inspect local queue item context before taking any lifecycle action." in index_text
    assert "queue-detail-item-id" in index_text
    assert "queue-detail-summary" in index_text
    assert "queue-detail-description" in index_text
    assert "queue-detail-requested-outcome" in index_text
    assert "queue-detail-readiness-summary" in index_text
    assert "No queue item selected. Select a queue item to inspect details." in index_text
    assert "Local-only and read-only queue view: no queue mutation, no agent execution, no GitHub sync/mutation." in index_text
    assert "Recommended Next Action" in index_text
    assert "Blockers" in index_text
    assert "Warnings" in index_text
    assert "Read-only local-only dashboard: no GitHub calls, no agent execution, no model routing." in index_text
    assert "View projects" in index_text
    assert "Open queue" in index_text
    assert "View repo status" in index_text
    assert "Open advisory lanes" in index_text
    assert "Open reports" in index_text
    assert "home-local-queue-status-drilldown" in index_text
    assert "home-local-agent-lane-drilldown" in index_text
    assert "Local Project Report Foundation" in index_text
    assert "Project Health" in index_text
    assert "Roadmap Summary" in index_text
    assert "Validation Summary" in index_text
    assert "Documentation Summary" in index_text
    assert "Blockers" in index_text
    assert "Local-only and read-only reports view: no report mutations, no GitHub sync/mutation, no agent/model execution." in index_text
    assert "active-project-intake" not in index_text


def test_frontend_scripts_reference_m39_api_endpoints_and_forms() -> None:
    combined_text = _combined_frontend_script_text()
    for endpoint in (
        "/api/projects",
        "/api/projects/active",
        "/api/project-factory/new-project",
        "/api/project-factory/dossier",
        "/api/project-factory/scope-package",
        "/api/project-factory/scope-package/approve",
        "/api/project-factory/architecture-contract",
        "/api/project-factory/architecture-contract/approve",
        "/api/project-factory/milestone-issue-plan",
        "/api/project-factory/milestone-issue-plan/approve",
        "/api/project-factory/github-apply-plan",
        "/api/project-factory/github-apply-plan/approve",
        "/api/project-factory/agent-dispatch-plan",
        "/api/project-factory/agent-dispatch-plan/approve",
        "/api/project-factory/validation-execution-plan",
        "/api/project-factory/validation-execution-plan/approve",
        "/api/project-factory/documentation-closeout-plan",
        "/api/project-factory/documentation-closeout-plan/approve",
        "/api/project-factory/execution-phase-approval",
        "/api/project-factory/execution-phase-approval/approve",
        "/api/project-factory/execution-readiness",
        "/api/projects/",
        "/github-link",
        "/api/bootstrap/status",
        "/api/bootstrap/plan",
        "/api/bootstrap/apply",
        "/api/queue",
        "/api/local-queue/items",
        "/api/local-queue/prompt-pack",
        "/evidence",
        "/readiness",
        "/start",
        "/codex-prompt",
        "/complete",
        "/api/settings",
        "/api/agents",
        "/api/handoff-targets",
        "/api/handoff/preview",
        "/api/orchestration/plan",
        "/api/escalation/plan",
        "/api/reports/dashboard",
        "/api/reports/action-center",
        "/api/reports/readiness",
        "/api/reports/operator-workflows",
        "/api/reports/export",
        "/api/dashboard/summary",
        "/api/local-project-report",
        "/api/active-project/workspace",
        "/api/local-projects",
        "/api/local-queue-agent-summary",
    ):
        assert endpoint in combined_text
    assert "ACTIVE" in combined_text
    for form_id in (
        "project-form",
        "new-project-wizard-form",
        "scope-authoring-form",
        "architecture-authoring-form",
        "repo-form",
        "queue-form",
        "queue-filter-form",
        "queue-lifecycle-add-form",
        "queue-lifecycle-codex-form",
        "queue-prompt-pack-form",
        "queue-lifecycle-evidence-form",
        "queue-lifecycle-complete-form",
        "intake-form",
        "agent-form",
        "handoff-target-form",
        "orchestration-form",
        "escalation-form",
    ):
        assert form_id in combined_text
    for action_id in (
        "bootstrap-refresh-status",
        "bootstrap-refresh-plan",
        "bootstrap-apply",
        "reports-refresh",
        "reports-copy-json",
        "reports-export-json",
        "reports-generate-handoff",
        "reports-generate-orchestration",
        "reports-generate-escalation",
        "home-refresh-summary",
        "home-local-open-project-context",
        "home-local-open-queue",
        "home-local-open-repos",
        "home-local-open-lanes",
        "home-local-open-reports",
        "workspace-refresh",
        "workspace-continue-intake",
        "workspace-open-queue",
        "workspace-select-project",
        "home-start-new-project",
        "projects-focus-new-project-wizard",
        "active-project-set",
        "queue-use-active-project",
        "queue-filter-active-project",
        "queue-lifecycle-add-submit",
        "queue-lifecycle-readiness",
        "queue-lifecycle-start",
        "queue-lifecycle-codex-submit",
        "queue-prompt-pack-submit",
        "queue-lifecycle-evidence-submit",
        "queue-lifecycle-complete-submit",
        "intake-submit",
        "scope-save-draft",
        "scope-approve",
        "home-prepare-architecture-contract",
        "architecture-save-draft",
        "architecture-approve",
        "home-prepare-milestone-issue-plan",
        "milestone-plan-save-draft",
        "milestone-plan-approve",
        "home-prepare-github-apply-plan",
        "github-apply-plan-save-draft",
        "github-apply-plan-approve",
        "home-prepare-agent-dispatch-plan",
        "agent-dispatch-plan-save-draft",
        "agent-dispatch-plan-approve",
        "home-prepare-validation-execution-plan",
        "validation-execution-plan-save-draft",
        "validation-execution-plan-approve",
        "home-prepare-documentation-closeout-plan",
        "documentation-closeout-plan-save-draft",
        "documentation-closeout-plan-approve",
        "home-prepare-execution-phase-approval",
        "execution-phase-approval-save-draft",
        "execution-phase-approval-approve",
        "home-refresh-execution-readiness",
    ):
        assert action_id in combined_text
    assert "parseLineList" in combined_text
    assert "toTextareaList" in combined_text
    assert "renderScopeAuthoring" in combined_text
    assert "buildScopeAuthoringPayload" in combined_text
    assert "renderArchitectureAuthoring" in combined_text
    assert "buildArchitectureAuthoringPayload" in combined_text
    assert "renderMilestoneIssuePlan" in combined_text
    assert "buildMilestoneIssuePlanPayload" in combined_text
    assert "renderGithubApplyPlan" in combined_text
    assert "buildGithubApplyPlanPayload" in combined_text
    assert "renderAgentDispatchPlan" in combined_text
    assert "buildAgentDispatchPlanPayload" in combined_text
    assert "renderValidationExecutionPlan" in combined_text
    assert "buildValidationExecutionPlanPayload" in combined_text
    assert "renderDocumentationCloseoutPlan" in combined_text
    assert "buildDocumentationCloseoutPlanPayload" in combined_text
    assert "renderExecutionReadiness" in combined_text
    assert "loadExecutionReadiness" in combined_text
    assert "setLocalQueueLifecycleItemId" in combined_text
    assert "buildLocalQueueAddPayload" in combined_text
    assert "buildLocalQueueCodexPromptPayload" in combined_text
    assert "buildLocalQueuePromptPackPayload" in combined_text
    assert "buildLocalQueueEvidencePayload" in combined_text
    assert "buildLocalQueueCompletePayload" in combined_text
    assert "renderLocalQueueReadinessResult" in combined_text
    assert "renderLocalQueueCodexPromptResult" in combined_text
    assert "renderLocalQueuePromptPackResult" in combined_text
    assert "renderLocalQueueEvidenceResult" in combined_text
    assert "renderLocalQueueCompleteResult" in combined_text
    assert "home-github-apply-plan-milestones" in combined_text
    assert "home-github-apply-plan-issues" in combined_text
    assert "home-agent-dispatch-items" in combined_text
    assert "home-agent-dispatch-queues" in combined_text
    assert "home-validation-execution-items" in combined_text
    assert "home-validation-execution-groups" in combined_text
    assert "home-validation-execution-evidence" in combined_text
    assert "home-documentation-closeout-items" in combined_text
    assert "home-documentation-closeout-evidence-packages" in combined_text
    assert "home-documentation-closeout-checks" in combined_text
    home_text = _frontend_script_texts()["js/sections/home.js"]
    assert "setInterval(" not in home_text
    assert "setTimeout(" not in home_text
    assert "/api/dashboard/summary" in home_text


def test_active_project_workspace_api_reuses_local_only_dashboard_and_report_data(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project(config, "p1")
    _seed_repo(config, "p1", "r1")
    payload = post_active_project(config, {"project_id": "p1"})
    assert payload["ok"] is True

    payload = post_queue_item(
        config,
        {
            "item_id": "ready-1",
            "project_id": "p1",
            "repo_id": "r1",
            "title": "Ready item",
            "status": "ready",
            "priority": "high",
            "item_type": "task",
        },
    )
    assert payload["ok"] is True
    payload = post_queue_item(
        config,
        {
            "item_id": "done-1",
            "project_id": "p1",
            "repo_id": "r1",
            "title": "Done item",
            "status": "done",
            "priority": "high",
            "item_type": "task",
        },
    )
    assert payload["ok"] is True

    workspace = get_active_project_workspace(config)

    assert workspace["ok"] is True
    assert workspace["local_only"] is True
    assert workspace["report_only"] is True
    assert workspace["active_project_selected"] is True
    assert workspace["active_project_id"] == "p1"
    assert workspace["active_repo_id"] == "r1"
    assert workspace["active_project_summary"]["active_project"]["name"] == "Project One"
    assert workspace["current_queue_items"][0]["item_id"] == "ready-1"
    assert workspace["recent_completed_queue_items"][0]["item_id"] == "done-1"
    assert "overall_status" in workspace["report_status"]
    assert "message" in workspace["repo_status"]
    assert workspace["continue_actions"]["task_intake_section"] == "queue"


def test_bootstrap_api_status_plan_apply(tmp_path: Path) -> None:
    config = _config(tmp_path)

    status = get_bootstrap_status(config)
    assert status["ok"] is True
    assert status["local_only"] is True
    assert "boundary_confirmations" in status

    plan = get_bootstrap_plan(config, {"seed_sample_work": "true"})
    assert plan["ok"] is True
    assert plan["plan_only"] is True
    assert "actions" in plan
    assert "boundary_confirmations" in plan

    applied = post_bootstrap_apply(config, {"force": False, "seed_sample_work": True})
    assert applied["ok"] is True
    assert applied["local_only"] is True
    assert "warnings" in applied
    assert "boundary_confirmations" in applied
    assert "m43-hub-stabilization" in applied["seeded_queue_items"]


def test_reports_and_settings_sections_contain_m40_concepts() -> None:
    index_text = (_static_dir() / "index.html").read_text(encoding="utf-8")
    assert "Project/Repo Summary" in index_text
    assert "Queue Summary" in index_text
    assert "Agent Summary" in index_text
    assert "Orchestration Summary" in index_text
    assert "Escalation Summary" in index_text
    assert "Docs Summary" in index_text
    assert "Readiness Indicators" in index_text
    assert "Action Center" in index_text
    assert "Operator Workflows" in index_text
    assert "GitHub Linkage" in index_text
    assert "Known limitations" in index_text
    assert "Next milestone scope" in index_text


def test_static_assets_do_not_reference_external_resources() -> None:
    external_patterns = [
        r"https?://",
        r"cdn",
        r"fonts\.googleapis",
        r"fonts\.gstatic",
        r"unpkg",
        r"jsdelivr",
    ]
    pattern = re.compile("|".join(external_patterns), re.IGNORECASE)

    static_dir = _static_dir()
    for path in (
        static_dir / "index.html",
        static_dir / "app.js",
        static_dir / "styles.css",
        static_dir / "js" / "core" / "dom.js",
        static_dir / "js" / "core" / "http.js",
        static_dir / "js" / "core" / "state.js",
        static_dir / "js" / "sections" / "home.js",
        static_dir / "js" / "sections" / "projects.js",
        static_dir / "js" / "sections" / "queue.js",
        static_dir / "js" / "sections" / "reports.js",
        static_dir / "js" / "sections" / "repos.js",
        static_dir / "js" / "sections" / "workspace.js",
        static_dir / "js" / "sections" / "projectFactory" / "index.js",
        static_dir / "js" / "sections" / "projectFactory" / "scope.js",
        static_dir / "js" / "sections" / "projectFactory" / "architecture.js",
        static_dir / "js" / "sections" / "projectFactory" / "milestonePlan.js",
        static_dir / "js" / "sections" / "projectFactory" / "validation.js",
        static_dir / "js" / "sections" / "projectFactory" / "agentDispatch.js",
        static_dir / "js" / "sections" / "projectFactory" / "executionApproval.js",
        static_dir / "js" / "sections" / "projectFactory" / "closeout.js",
    ):
        content = path.read_text(encoding="utf-8")
        assert not pattern.search(content)


def test_reports_bindings_live_in_reports_module_only() -> None:
    static_dir = _static_dir()
    app_text = (static_dir / "app.js").read_text(encoding="utf-8")
    reports_text = (static_dir / "js" / "sections" / "reports.js").read_text(encoding="utf-8")

    assert "bindReportsActions" in reports_text
    assert "bindReportsActions" in app_text
    for action_id in (
        "reports-refresh",
        "reports-copy-json",
        "reports-export-json",
        "reports-generate-handoff",
        "reports-generate-orchestration",
        "reports-generate-escalation",
    ):
        assert action_id not in app_text
        assert action_id in reports_text


def test_projects_bindings_live_in_projects_module_only() -> None:
    static_dir = _static_dir()
    app_text = (static_dir / "app.js").read_text(encoding="utf-8")
    projects_text = (static_dir / "js" / "sections" / "projects.js").read_text(encoding="utf-8")

    assert "bindProjectsActions" in projects_text
    assert "bindProjectsActions" in app_text
    for action_id in (
        "project-form",
        "active-project-set",
    ):
        assert action_id not in app_text
        assert action_id in projects_text


def test_repos_bindings_live_in_repos_module_only() -> None:
    static_dir = _static_dir()
    app_text = (static_dir / "app.js").read_text(encoding="utf-8")
    repos_text = (static_dir / "js" / "sections" / "repos.js").read_text(encoding="utf-8")

    assert "bindReposActions" in repos_text
    assert "bindReposActions" in app_text
    for action_id in (
        "repo-project-select",
        "repo-form",
        "repo-check-github-link",
    ):
        assert action_id not in app_text
        assert action_id in repos_text


def test_queue_bindings_live_in_queue_module_only() -> None:
    static_dir = _static_dir()
    app_text = (static_dir / "app.js").read_text(encoding="utf-8")
    queue_text = (static_dir / "js" / "sections" / "queue.js").read_text(encoding="utf-8")

    assert "bindQueueActions" in queue_text
    assert "bindQueueActions" in app_text
    for action_id in (
        "queue-use-active-project",
        "queue-filter-active-project",
        "queue-filter-form",
        "queue-filter-reset",
        "queue-form",
    ):
        assert action_id not in app_text
        assert action_id in queue_text


def test_workspace_bindings_live_in_workspace_module_only() -> None:
    static_dir = _static_dir()
    app_text = (static_dir / "app.js").read_text(encoding="utf-8")
    workspace_text = (static_dir / "js" / "sections" / "workspace.js").read_text(encoding="utf-8")

    assert "bindWorkspaceActions" in workspace_text
    assert "bindWorkspaceActions" in app_text
    for action_id in (
        "workspace-refresh",
        "workspace-continue-intake",
        "workspace-open-queue",
        "workspace-select-project",
    ):
        assert action_id not in app_text
        assert action_id in workspace_text


def test_settings_and_boundary_notice_present_in_static_markup() -> None:
    index_text = (_static_dir() / "index.html").read_text(encoding="utf-8")
    assert "Local-only boundary" in index_text
    assert "settings-registry-path" in index_text
    assert "settings-queue-path" in index_text
    assert "settings-agents-path" in index_text
    assert "settings-handoff-artifacts-path" in index_text
    assert "settings-orchestration-artifacts-path" in index_text
    assert "settings-escalation-artifacts-path" in index_text
    assert "settings-dashboard-artifacts-path" in index_text
    assert "settings-m41-boundaries" in index_text
    assert "GitHub link boundary note" in index_text
    assert "plan-only" in index_text


def test_api_health_response_contains_boundaries() -> None:
    payload = get_health()

    assert payload["ok"] is True
    assert payload["local_only"] is True
    assert payload["service"] == "aresforge-hub"
    assert any("No GitHub calls" in item for item in payload["boundary_confirmations"])


def test_api_summary_with_missing_files_returns_empty_state(tmp_path: Path) -> None:
    payload = get_summary(_config(tmp_path))

    assert payload["ok"] is True
    assert payload["local_only"] is True
    assert payload["report_only"] is True
    assert payload["project_count"] == 0
    assert payload["repo_count"] == 0
    assert payload["queue_status_counts"] == {}
    assert payload["agent_count"] == 0
    assert payload["warnings"]
    assert payload["next_recommended_actions"]
    assert payload["project_management_readiness"]
    assert any("No network service calls" in item for item in payload["boundary_confirmations"])


def test_api_docs_status_response(tmp_path: Path) -> None:
    payload = get_docs_status(_config(tmp_path))

    assert payload["ok"] is True
    assert payload["local_only"] is True
    assert payload["report_only"] is True
    assert isinstance(payload["docs"], list)
    assert payload["missing_count"] >= 0
    assert "boundary_confirmations" in payload


def test_reports_dashboard_with_missing_files_returns_report_and_warnings(tmp_path: Path) -> None:
    payload = get_reports_dashboard(_config(tmp_path))

    assert payload["ok"] is True
    assert payload["local_only"] is True
    assert payload["report_only"] is True
    assert "project_summary" in payload
    assert "queue_summary" in payload
    assert "agent_summary" in payload
    assert "docs_summary" in payload
    assert payload["warnings"]
    assert payload["boundary_confirmations"]


def test_reports_action_center_readiness_workflows_and_export_endpoints(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project(config, "p1")
    _seed_repo(config, "p1", "r1")
    _seed_queue_item(config, "q1")
    _seed_agent(config, "agent-a")
    _seed_handoff_target(config, "target-a")

    action_center = get_reports_action_center(config)
    readiness = get_reports_readiness(config)
    workflows = get_reports_operator_workflows(config)
    exported = get_reports_export(config, {"format": "json"})

    assert action_center["ok"] is True
    assert "action_center" in action_center
    assert action_center["boundary_confirmations"]

    assert readiness["ok"] is True
    assert "readiness_indicators" in readiness
    assert "overall_status" in readiness["readiness_indicators"]
    assert readiness["boundary_confirmations"]

    assert workflows["ok"] is True
    assert isinstance(workflows["operator_workflows"], list)
    assert workflows["operator_workflows"]
    assert workflows["boundary_confirmations"]

    assert exported["ok"] is True
    assert exported["report_only"] is True
    assert "report" in exported
    assert "content" in exported
    assert exported["write_performed"] is False
    assert exported["boundary_confirmations"]


def test_get_projects_returns_empty_state_when_registry_missing(tmp_path: Path) -> None:
    config = _config(tmp_path)
    payload = get_projects(config)

    assert payload["ok"] is True
    assert payload["local_only"] is True
    assert payload["projects"] == []
    assert payload["project_count"] == 0
    assert payload["warnings"]
    assert payload["boundary_confirmations"]


def test_post_project_creates_and_updates_project(tmp_path: Path) -> None:
    config = _config(tmp_path)

    created = post_project(
        config,
        {
            "project_id": "p1",
            "name": "Project One",
            "root_path": str(tmp_path),
            "status": "active",
            "default_branch": "main",
            "github_owner": "example-org",
            "github_repo": "sample-repo",
            "github_default_branch": "main",
            "tags": ["m38"],
            "notes": "initial",
        },
    )
    assert created["ok"] is True
    assert created["created"] is True

    updated = post_project(
        config,
        {
            "project_id": "p1",
            "name": "Project One Updated",
            "root_path": str(tmp_path),
            "status": "paused",
            "tags": ["m38", "updated"],
        },
    )
    assert updated["ok"] is True
    assert updated["created"] is False
    assert updated["project"]["name"] == "Project One Updated"
    assert updated["project"]["status"] == "paused"
    assert updated["project"]["github_url"] == "https://github.com/example-org/sample-repo"


def test_get_project_returns_project_details_and_repos(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project(config, "p1")
    _seed_repo(config, "p1", "r1")

    payload = get_project(config, "p1")

    assert payload["ok"] is True
    assert payload["project"]["project_id"] == "p1"
    assert payload["project"]["github_owner"] == "example-org"
    assert payload["project"]["github_repo"] == "sample-repo"
    assert payload["project"]["github_url"] == "https://github.com/example-org/sample-repo"
    assert len(payload["repos"]) == 1
    assert payload["repos"][0]["repo_id"] == "r1"
    assert payload["repos"][0]["github_owner"] == "example-org"
    assert payload["repos"][0]["github_repo"] == "sample-repo"


def test_get_project_repos_returns_repos_for_project(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project(config, "p1")
    _seed_repo(config, "p1", "r1")

    payload = get_project_repos(config, "p1")

    assert payload["ok"] is True
    assert payload["project_id"] == "p1"
    assert payload["repo_count"] == 1
    assert payload["repos"][0]["github_url"] == "https://github.com/example-org/sample-repo"


def test_post_project_repo_creates_and_updates_repo(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project(config, "p1")

    created = post_project_repo(
        config,
        "p1",
        {
            "repo_id": "r1",
            "name": "Repo One",
            "path": str(tmp_path),
            "role": "primary",
            "status": "active",
            "github_url": "https://github.com/example-org/sample-repo",
        },
    )
    assert created["ok"] is True
    assert created["created"] is True

    updated = post_project_repo(
        config,
        "p1",
        {
            "repo_id": "r1",
            "name": "Repo One Updated",
            "path": str(tmp_path),
            "role": "automation",
            "status": "paused",
            "tags": ["x"],
        },
    )
    assert updated["ok"] is True
    assert updated["created"] is False
    assert updated["repo"]["name"] == "Repo One Updated"
    assert updated["repo"]["role"] == "automation"


def test_get_project_repo_github_link_returns_local_only_payload(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project(config, "p1")
    non_git_dir = tmp_path / "non-git"
    non_git_dir.mkdir(parents=True, exist_ok=True)
    created = post_project_repo(
        config,
        "p1",
        {
            "repo_id": "r1",
            "name": "Repo One",
            "path": str(non_git_dir),
            "role": "primary",
            "github_owner": "example-org",
            "github_repo": "sample-repo",
        },
    )
    assert created["ok"] is True

    payload = get_project_repo_github_link(config, "p1", "r1", inspect_local_git=True)
    assert payload["ok"] is True
    assert payload["local_only"] is True
    assert payload["project_id"] == "p1"
    assert payload["repo_id"] == "r1"
    assert payload["github_owner"] == "example-org"
    assert payload["github_repo"] == "sample-repo"
    assert payload["github_url"] == "https://github.com/example-org/sample-repo"
    assert isinstance(payload["warnings"], list)
    assert payload["boundary_confirmations"]


def test_post_repo_fails_clearly_when_project_missing(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project(config, "p1")
    payload = post_project_repo(
        config,
        "missing",
        {
            "repo_id": "r1",
            "name": "Repo One",
            "path": str(tmp_path),
        },
    )

    assert payload["ok"] is False
    assert payload["error"] == "managed_project_not_found"
    assert payload["_status"] == 404


def test_get_queue_returns_empty_state_when_queue_missing(tmp_path: Path) -> None:
    config = _config(tmp_path)
    payload = get_queue(config, {})

    assert payload["ok"] is True
    assert payload["local_only"] is True
    assert payload["items"] == []
    assert payload["counts_by_status"] == {}
    assert payload["counts_by_type"] == {}
    assert payload["counts_by_priority"] == {}
    assert payload["warnings"]


def test_post_queue_creates_and_updates_item(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project(config, "p1")
    _seed_repo(config, "p1", "r1")

    created = post_queue_item(
        config,
        {
            "item_id": "q1",
            "project_id": "p1",
            "repo_id": "r1",
            "title": "Queue One",
            "status": "ready",
            "priority": "high",
            "item_type": "task",
            "dependencies": ["future-item"],
        },
    )
    assert created["ok"] is True
    assert created["created"] is True
    assert any("reference not found" in warning for warning in created["warnings"])

    updated = post_queue_item(
        config,
        {
            "item_id": "q1",
            "project_id": "p1",
            "repo_id": "r1",
            "title": "Queue One Updated",
            "status": "in_progress",
            "priority": "urgent",
            "item_type": "feature",
        },
    )
    assert updated["ok"] is True
    assert updated["created"] is False
    assert updated["item"]["status"] == "in_progress"
    assert updated["item"]["priority"] == "urgent"


def test_get_queue_item_returns_item_details(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue_item(config, "q1")

    payload = get_queue_item(config, "q1")

    assert payload["ok"] is True
    assert payload["item"]["item_id"] == "q1"


def test_patch_queue_updates_only_supplied_fields(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue_item(config, "q1")

    payload = patch_queue_item(
        config,
        "q1",
        {
            "status": "blocked",
            "notes": "waiting",
        },
    )

    assert payload["ok"] is True
    assert payload["item"]["status"] == "blocked"
    assert payload["item"]["notes"] == "waiting"
    assert payload["item"]["priority"] == "high"


def test_patch_queue_missing_item_fails_clearly(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue_item(config, "q1")
    payload = patch_queue_item(config, "missing", {"status": "ready"})

    assert payload["ok"] is False
    assert payload["error"] == "queue_item_not_found"
    assert payload["_status"] == 404


def test_queue_filters_for_project_repo_status_type_and_assigned_agent(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue_item(config, "q1")
    post_queue_item(
        config,
        {
            "item_id": "q2",
            "project_id": "p1",
            "repo_id": "r1",
            "title": "Queue Two",
            "status": "blocked",
            "priority": "normal",
            "item_type": "bug",
            "assigned_agent": "agent-b",
        },
    )

    payload = get_queue(
        config,
        {
            "project_id": "p1",
            "repo_id": "r1",
            "status": "ready",
            "type": "task",
            "assigned_agent": "agent-a",
        },
    )

    assert payload["ok"] is True
    assert len(payload["items"]) == 1
    assert payload["items"][0]["item_id"] == "q1"


def test_invalid_project_repo_queue_values_return_json_errors(tmp_path: Path) -> None:
    config = _config(tmp_path)

    invalid_project = post_project(
        config,
        {
            "project_id": "p1",
            "name": "Project One",
            "root_path": str(tmp_path),
            "status": "bad-status",
        },
    )
    assert invalid_project["ok"] is False
    assert invalid_project["error"] == "invalid_project_status"

    _seed_project(config, "p1")

    invalid_repo = post_project_repo(
        config,
        "p1",
        {
            "repo_id": "r1",
            "name": "Repo One",
            "path": str(tmp_path),
            "role": "bad-role",
        },
    )
    assert invalid_repo["ok"] is False
    assert invalid_repo["error"] == "invalid_repo_role"

    invalid_queue = post_queue_item(
        config,
        {
            "item_id": "q1",
            "project_id": "p1",
            "repo_id": "r1",
            "title": "Queue One",
            "priority": "bad-priority",
        },
    )
    assert invalid_queue["ok"] is False
    assert invalid_queue["error"] == "invalid_queue_priority"


def test_boundary_confirmations_remain_present_for_m38_endpoints(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue_item(config, "q1")

    projects = get_projects(config)
    queue = get_queue(config, {})
    settings = get_settings(config)

    for payload in (projects, queue, settings):
        assert payload["local_only"] is True
        assert payload["boundary_confirmations"]
    assert settings["m41_boundary_confirmations"]


def test_get_agents_returns_empty_state_when_profiles_missing(tmp_path: Path) -> None:
    payload = get_agents(_config(tmp_path))
    assert payload["ok"] is True
    assert payload["agents"] == []
    assert payload["agent_count"] == 0
    assert payload["counts_by_role"] == {}
    assert payload["counts_by_execution_mode"] == {}
    assert payload["counts_by_status"] == {}
    assert payload["warnings"]
    assert payload["boundary_confirmations"]


def test_post_agent_creates_and_updates_profile(tmp_path: Path) -> None:
    config = _config(tmp_path)
    created = post_agent(
        config,
        {
            "agent_id": "agent-a",
            "name": "Agent A",
            "role": "implementer",
            "execution_mode": "codex",
            "status": "active",
            "escalation_allowed": True,
            "allowed_item_types": ["task"],
        },
    )
    assert created["ok"] is True
    assert created["created"] is True

    updated = post_agent(
        config,
        {
            "agent_id": "agent-a",
            "name": "Agent A Updated",
            "role": "implementer",
            "execution_mode": "scripted",
            "status": "paused",
            "escalation_allowed": False,
        },
    )
    assert updated["ok"] is True
    assert updated["created"] is False
    assert updated["agent"]["name"] == "Agent A Updated"
    assert updated["agent"]["execution_mode"] == "scripted"


def test_get_agent_returns_details_and_linked_target_when_available(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_handoff_target(config, "target-a")
    post_agent(
        config,
        {
            "agent_id": "agent-a",
            "name": "Agent A",
            "role": "implementer",
            "handoff_target_id": "target-a",
        },
    )

    payload = get_agent(config, "agent-a")
    assert payload["ok"] is True
    assert payload["agent"]["agent_id"] == "agent-a"
    assert payload["linked_handoff_target"]["target_id"] == "target-a"


def test_post_agent_rejects_invalid_role_execution_mode_status_and_escalation_flag(tmp_path: Path) -> None:
    config = _config(tmp_path)

    invalid_role = post_agent(config, {"agent_id": "a", "name": "A", "role": "invalid"})
    assert invalid_role["ok"] is False
    assert invalid_role["error"] == "invalid_role"

    invalid_mode = post_agent(
        config,
        {"agent_id": "a", "name": "A", "role": "operator", "execution_mode": "invalid"},
    )
    assert invalid_mode["ok"] is False
    assert invalid_mode["error"] == "invalid_execution_mode"

    invalid_status = post_agent(
        config,
        {"agent_id": "a", "name": "A", "role": "operator", "status": "invalid"},
    )
    assert invalid_status["ok"] is False
    assert invalid_status["error"] == "invalid_status"

    invalid_escalation = post_agent(
        config,
        {
            "agent_id": "a",
            "name": "A",
            "role": "operator",
            "escalation_allowed": "yes",
        },
    )
    assert invalid_escalation["ok"] is False
    assert invalid_escalation["error"] == "invalid_escalation_allowed"


def test_get_handoff_targets_returns_empty_state_when_profiles_missing(tmp_path: Path) -> None:
    payload = get_handoff_targets(_config(tmp_path))
    assert payload["ok"] is True
    assert payload["handoff_targets"] == []
    assert payload["target_count"] == 0
    assert payload["counts_by_target_type"] == {}
    assert payload["counts_by_status"] == {}
    assert payload["warnings"]


def test_post_handoff_target_creates_and_updates_target(tmp_path: Path) -> None:
    config = _config(tmp_path)
    created = post_handoff_target(
        config,
        {
            "target_id": "target-a",
            "name": "Target A",
            "target_type": "markdown_packet",
            "status": "active",
        },
    )
    assert created["ok"] is True
    assert created["created"] is True

    updated = post_handoff_target(
        config,
        {
            "target_id": "target-a",
            "name": "Target A Updated",
            "target_type": "json_packet",
            "status": "paused",
        },
    )
    assert updated["ok"] is True
    assert updated["created"] is False
    assert updated["handoff_target"]["target_type"] == "json_packet"


def test_get_handoff_target_returns_target_details(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_handoff_target(config, "target-a")
    payload = get_handoff_target(config, "target-a")
    assert payload["ok"] is True
    assert payload["handoff_target"]["target_id"] == "target-a"


def test_post_handoff_target_rejects_invalid_type_and_status(tmp_path: Path) -> None:
    config = _config(tmp_path)
    invalid_type = post_handoff_target(
        config,
        {"target_id": "t", "name": "T", "target_type": "invalid"},
    )
    assert invalid_type["ok"] is False
    assert invalid_type["error"] == "invalid_target_type"

    invalid_status = post_handoff_target(
        config,
        {
            "target_id": "t",
            "name": "T",
            "target_type": "markdown_packet",
            "status": "invalid",
        },
    )
    assert invalid_status["ok"] is False
    assert invalid_status["error"] == "invalid_status"


def test_get_handoff_preview_returns_local_only_response(tmp_path: Path) -> None:
    payload = get_handoff_preview(_config(tmp_path))
    assert payload["ok"] is True
    assert payload["local_only"] is True
    assert payload["preview_format"] == "markdown"
    assert isinstance(payload["preview"], str)
    assert payload["boundary_confirmations"]


def test_get_orchestration_plan_returns_plan_only_with_empty_inputs(tmp_path: Path) -> None:
    payload = get_orchestration_plan(_config(tmp_path))
    assert payload["ok"] is True
    assert payload["local_only"] is True
    assert payload["plan_only"] is True
    assert isinstance(payload["selected_work_items"], list)
    assert "recommended_assignments" in payload
    assert payload["boundary_confirmations"]


def test_post_orchestration_plan_supports_filters(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue_item(config, "q1")
    _seed_agent(config, "agent-a")
    payload = post_orchestration_plan(
        config,
        {"project_id": "p1", "repo_id": "r1", "status": "ready", "format": "json"},
    )
    assert payload["ok"] is True
    assert payload["filters"]["project_id"] == "p1"
    assert payload["plan_only"] is True


def test_get_escalation_plan_returns_plan_only_with_empty_inputs(tmp_path: Path) -> None:
    payload = get_escalation_plan(_config(tmp_path))
    assert payload["ok"] is True
    assert payload["local_only"] is True
    assert payload["plan_only"] is True
    assert "classifications" in payload
    assert "prompt_guidance" in payload
    assert payload["boundary_confirmations"]


def test_post_escalation_plan_supports_filters(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue_item(config, "q1")
    _seed_agent(config, "agent-a")
    _seed_handoff_target(config, "target-a")
    payload = post_escalation_plan(
        config,
        {
            "item_id": "q1",
            "project_id": "p1",
            "repo_id": "r1",
            "status": "ready",
            "format": "json",
        },
    )
    assert payload["ok"] is True
    assert payload["filters"]["item_id"] == "q1"
    assert payload["plan_only"] is True


def test_boundary_confirmations_remain_present_for_m39_endpoints(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue_item(config, "q1")
    _seed_agent(config, "agent-a")

    for payload in (
        get_agents(config),
        get_handoff_targets(config),
        get_handoff_preview(config),
        get_orchestration_plan(config),
        get_escalation_plan(config),
    ):
        assert payload["local_only"] is True
        assert payload["boundary_confirmations"]


def test_m44_active_project_intake_static_contract() -> None:
    index_text = (_static_dir() / "index.html").read_text(encoding="utf-8")
    combined_text = _combined_frontend_script_text()
    app_text = (_static_dir() / "app.js").read_text(encoding="utf-8")

    assert "Active Project Task Intake" in index_text
    assert "intake-form" in index_text
    assert "intake-title" in index_text
    assert "intake-type" in index_text
    assert "intake-priority" in index_text
    assert "intake-source" in index_text
    assert "Task Summary / Details" in index_text
    assert "Requested Outcome" in index_text
    assert "intake-requested-outcome" in index_text
    assert "intake-acceptance-notes" in index_text
    assert "intake-validation-notes" in index_text
    assert "Create Local Queue Item" in index_text
    assert "intake-active-project-summary" in index_text
    assert "intake-result" in index_text
    assert "Local-only intake for the selected active project." in index_text

    assert 'fetchJson("/api/project-factory/new-project"' in combined_text
    assert 'fetchJson("/api/local-queue/items"' in combined_text
    assert '"active_project_workspace"' in combined_text
    assert "requested_outcome" in combined_text
    assert "acceptance_notes" in combined_text
    assert "validation_notes" in combined_text
    assert "active-project-intake" in combined_text
    assert "No queue items available. Add or load queue items to inspect details." in combined_text
    assert 'fetchJson(`/api/queue/${encodeURIComponent(normalizedItemId)}`' in combined_text
    assert 'fetchJson(`/api/local-queue/items/${encodeURIComponent(normalizedItemId)}/readiness`' in combined_text
    assert "View Details" in combined_text
    assert "Readiness data unavailable for this item. Use Inspect Readiness in lifecycle controls if needed." in combined_text
    assert 'intakeType === "direction" || intakeType === "ui" || intakeType === "refactor"' in app_text
    assert 'intakeType === "docs"' in app_text
    assert "loadLocalProjectReportFoundation" in combined_text
    assert "renderLocalProjectReportFoundation" in combined_text


def test_m45_active_project_workbench_static_contract() -> None:
    index_text = (_static_dir() / "index.html").read_text(encoding="utf-8")
    combined_text = _combined_frontend_script_text()

    assert "Active Project Workbench" in index_text
    assert "Current Active Work" in index_text
    assert "Workbench Actions" in index_text
    assert "Add Active Project Intake" in index_text

    assert "home-quick-intake" in combined_text
    assert 'activateSection("queue")' in combined_text
    assert 'byId("intake-title")' in combined_text
    assert ".focus()" in combined_text


def test_static_frontend_source_excludes_github_mutation_cli_and_api_strings() -> None:
    combined_text = _combined_frontend_script_text()
    forbidden_strings = (
        "gh issue",
        "gh pr",
        "api.github.com",
    )
    for token in forbidden_strings:
        assert token not in combined_text.lower()


def test_local_queue_agent_summary_api_contract(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project(config, "aresforge")
    _seed_repo(config, "aresforge", "aresforge-primary")
    post_active_project(config, {"project_id": "aresforge"})
    _seed_queue_item(config, "queue-one")

    payload = get_local_queue_agent_summary(config)

    assert payload["ok"] is True
    assert payload["local_only"] is True
    assert payload["active_project"]["active_project_id"] == "aresforge"
    assert "queue_totals" in payload
    assert "items_by_status" in payload
    assert "next_safe_action" in payload
