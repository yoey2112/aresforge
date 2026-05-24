# AresForge Agent Context

## Purpose

Provide minimum operating context for M42 first-run bootstrap/setup with a local-first, self-managed operator model.

## Current Operating Model

- Active milestone context: M42 first-run bootstrap and seed wizard in local registry and Hub.
- AresForge now has a local-first foundation for self-managed operation.
- GitHub is optional/syncable and not mandatory for local planning.
- M26 added local handoff package generation.
- M27 added the local project state ledger.
- M28 added plan-only documentation reconciliation.
- M29 added plan-only offline-to-GitHub sync planning.
- M30 added local self-managed milestone lifecycle support.
- M32 added local managed-project/multi-repo registry support.
- M33 added local project queue/work tracking support.
- M34 added local agent profiles and handoff target descriptors.
- M35 added local multi-agent orchestration planning (assignment + sequencing + handoff prompts).
- M36 added local escalation planning that classifies queue/orchestration work for local LLM, Codex, cloud advisory, human-required, and blocked/clarification paths.
- M37 added a local Hub server/API/frontend foundation intended to become the primary local entry point for AresForge.
- M38 added interactive local Hub screens and API workflows for M32 managed-project registry and M33 local queue management.
- M39 adds interactive local Hub screens and API workflows for M34 local agent profiles/handoff targets, M26 handoff preview, M35 orchestration planning, and M36 escalation planning.
- M40 adds unified local control-plane reporting, readiness indicators, action-center guidance, and operator workflow cards in Hub Home/Reports/Settings.
- M41 adds explicit local GitHub identity for managed projects/repos, primary repo linkage, local git-link inspection, and Hub GitHub linkage readiness/reporting surfaces.
- M42 adds first-run bootstrap status/plan/apply support for local file initialization and default seed data.
- Foundation-batch boundaries (M26-M30):
  - no `gh`
  - no GitHub API calls
  - no LLM API calls
  - no network-required execution path
- Current local-first command surface:
  - `python -m aresforge generate-handoff-package --output <path> [--format markdown|json] [--include-doc-excerpts] [--force]`
  - `python -m aresforge init-project-state [--path <path>] [--force]`
  - `python -m aresforge inspect-project-state [--path <path>]`
  - `python -m aresforge update-project-state [--path <path>] [--current-milestone <value>] [--current-phase <value>] [--current-mode <value>] [--validation-status <value>] [--documentation-status <value>] [--warning <text>]...`
  - `python -m aresforge append-operation-log [--state-path <path>] --event-type <type> --summary <summary> [--details <json>]`
  - `python -m aresforge inspect-operation-log [--state-path <path>] [--limit <n>]`
  - `python -m aresforge plan-doc-reconciliation [--output <path>] [--format json|markdown] [--include-git-state] [--force]`
  - `python -m aresforge plan-github-sync [--state-file <path>] [--project-state <path>] [--output <path>] [--format json|markdown] [--force]`
  - `python -m aresforge generate-local-milestone-template --milestone-id <id> --output <path> [--title <title>] [--force]`
  - `python -m aresforge inspect-local-milestone --definition <path> [--format json|markdown]`
  - `python -m aresforge check-local-milestone-readiness --definition <path> [--project-state <path>] [--format json|markdown]`
  - `python -m aresforge generate-local-milestone-closeout --definition <path> --output <path> [--format json|markdown] [--force]`
  - `python -m aresforge init-managed-project-registry [--path <path>] [--force]`
  - `python -m aresforge register-managed-project --project-id <id> --name <name> --root-path <path> [--registry-path <path>] [--description <text>] [--status <status>] [--default-branch <branch>] [--tag <tag>]... [--notes <text>]`
  - `python -m aresforge register-managed-project --project-id <id> --name <name> --root-path <path> [--registry-path <path>] [--description <text>] [--status <status>] [--default-branch <branch>] [--github-url <url>] [--github-owner <owner>] [--github-repo <repo>] [--github-default-branch <branch>] [--primary-repo-id <repo_id>] [--tag <tag>]... [--notes <text>]`
  - `python -m aresforge register-managed-repo --project-id <id> --repo-id <id> --name <name> --path <path> [--registry-path <path>] [--remote-url <url>] [--default-branch <branch>] [--github-url <url>] [--github-owner <owner>] [--github-repo <repo>] [--github-default-branch <branch>] [--inspect-local-git] [--role <role>] [--status <status>] [--tag <tag>]... [--notes <text>]`
  - `python -m aresforge inspect-managed-project-registry [--registry-path <path>] [--format json|markdown]`
  - `python -m aresforge inspect-managed-project --project-id <id> [--registry-path <path>] [--format json|markdown]`
  - `python -m aresforge inspect-managed-repo --project-id <id> --repo-id <id> [--registry-path <path>] [--format json|markdown]`
  - `python -m aresforge inspect-managed-repo-github-link --project-id <id> --repo-id <id> [--registry-path <path>] [--inspect-local-git] [--format json|markdown]`
  - `python -m aresforge inspect-bootstrap-status [--repo-path <path>]`
  - `python -m aresforge plan-bootstrap [--repo-path <path>] [--format json|markdown] [--seed-sample-work]`
  - `python -m aresforge apply-bootstrap [--repo-path <path>] [--force] [--seed-sample-work] [--format json|markdown]`
  - `python -m aresforge init-project-queue [--path <path>] [--force]`
  - `python -m aresforge add-queue-item --item-id <id> --project-id <id> --repo-id <id> --title <title> [--queue-path <path>] [--registry-path <path>] [--description <text>] [--status <status>] [--priority <priority>] [--type <type>] [--tag <tag>]... [--depends-on <item_id>]... [--blocked-by <item_id>]... [--assigned-agent <agent_id>] [--source <source>] [--notes <text>]`
  - `python -m aresforge update-queue-item --item-id <id> [--queue-path <path>] [--project-id <id>] [--repo-id <id>] [--status <status>] [--priority <priority>] [--type <type>] [--title <title>] [--description <text>] [--tag <tag>]... [--depends-on <item_id>]... [--blocked-by <item_id>]... [--assigned-agent <agent_id>] [--source <source>] [--notes <text>]`
  - `python -m aresforge inspect-project-queue [--queue-path <path>] [--project-id <id>] [--repo-id <id>] [--status <status>] [--type <type>] [--assigned-agent <agent_id>] [--format json|markdown]`
  - `python -m aresforge inspect-queue-item --item-id <id> [--queue-path <path>] [--format json|markdown]`
  - `python -m aresforge init-agent-profiles [--path <path>] [--force] [--with-defaults]`
  - `python -m aresforge register-agent-profile --agent-id <id> --name <name> --role <role> [--profiles-path <path>] [--description <text>] [--execution-mode <mode>] [--model-preference <value>] [--strength <text>]... [--constraint <text>]... [--allowed-type <type>]... [--escalation-allowed true|false] [--handoff-target-id <id>] [--status <status>] [--tag <tag>]... [--notes <text>]`
  - `python -m aresforge register-handoff-target --target-id <id> --name <name> --target-type <type> [--profiles-path <path>] [--description <text>] [--local-command <command>] [--input-format <format>] [--output-format <format>] [--safety-note <text>]... [--status <status>] [--tag <tag>]... [--notes <text>]`
  - `python -m aresforge inspect-agent-profiles [--profiles-path <path>] [--role <role>] [--execution-mode <mode>] [--status <status>] [--format json|markdown]`
  - `python -m aresforge inspect-agent-profile --agent-id <id> [--profiles-path <path>] [--format json|markdown]`
  - `python -m aresforge inspect-handoff-target --target-id <id> [--profiles-path <path>] [--format json|markdown]`
  - `python -m aresforge plan-agent-orchestration [--project-id <id>] [--repo-id <id>] [--status <status>] [--queue-path <path>] [--profiles-path <path>] [--registry-path <path>] [--output <path>] [--format json|markdown] [--force]`
  - `python -m aresforge plan-llm-escalation [--item-id <id>] [--project-id <id>] [--repo-id <id>] [--status <status>] [--queue-path <path>] [--profiles-path <path>] [--orchestration-plan <path>] [--output <path>] [--format json|markdown] [--force]`
  - `python -m aresforge serve-hub [--host <host>] [--port <port>] [--open-browser]`
- M33 boundary confirmations:
  - queue is local-only and can track work without GitHub issues
  - no `gh`
  - no GitHub API calls
  - no network access
  - no LLM calls
  - `assigned_agent` is data-only for future orchestration and does not execute agents
  - M32 registry validation is local-only when registry exists or `--registry-path` is supplied
- M34 boundary confirmations:
  - local-only configuration for agent and handoff metadata
  - handoff targets are descriptive/advisory only
  - no agent execution path is introduced yet
  - no local LLM invocation is introduced yet
  - no cloud LLM invocation is introduced yet
  - no `gh`, no GitHub API calls, no network access
  - M33 `assigned_agent` can reference M34 `agent_id`
- M35 boundary confirmations:
  - local-only orchestration planning
  - plan-only output (assignment and sequencing guidance only)
  - no agent execution
  - no local LLM invocation
  - no cloud LLM invocation
  - no `gh`, no GitHub API calls, no network access
  - reads M32 registry, M33 queue, and M34 profiles where available
- M36 boundary confirmations:
  - local-only escalation planning
  - plan-only classification output only (no execution)
  - cloud escalation is advisory only
  - no LLM invocation
  - no local LLM calls
  - no cloud LLM calls
  - no Codex execution
  - no ChatGPT calls
  - no `gh`, no GitHub API calls, no network access
  - reads M33 queue and M34 profiles where available and optional M35 orchestration artifact input when supplied
- M37 boundary confirmations:
  - local-first local UI serving path
  - binds to `127.0.0.1` by default
  - no `gh`, no GitHub API calls, no network service calls
  - no local LLM calls, no cloud LLM calls
  - no Codex calls, no ChatGPT calls, no Ollama calls
  - no external API calls
  - no agent execution
  - no live GitHub sync
  - no authentication implementation yet
  - no production deployment implementation yet
- M38 boundary confirmations:
  - local-first, file-backed project/repo/queue management via Hub API and static UI
  - no `gh`, no GitHub API calls, no network services
  - no local LLM calls, no cloud LLM calls, no Codex/ChatGPT/Ollama calls
  - no external API calls
  - no agent execution, no live GitHub sync
  - M40 reporting/dashboard/operator workflow surfaces are implemented as local-only report/plan-only flows
  - authentication and production deployment remain unimplemented
- M39 boundary confirmations:
- M40 boundary confirmations:
  - local-first, file-backed reporting and workflow guidance
  - report-only and plan-only control-plane surfaces
  - no agent execution
  - no local/cloud/Codex/ChatGPT/Ollama model invocation
  - no GitHub calls, no `gh` calls, no network/external API calls
  - no live GitHub sync execution
  - authentication and production deployment remain unimplemented
  - future work includes guided workflow depth, optional execution gates, auth hardening when exposed beyond localhost, controlled sync execution, and optional LLM execution behind explicit user approval gates
- M41 boundary confirmations:
  - GitHub links are local metadata only
  - local git inspection is local-only and non-networked
  - no GitHub API calls
  - no `gh` calls
  - no GraphQL/REST calls
  - no network service calls
  - no live GitHub validation
- M42 boundary confirmations:
  - bootstrap is local-only and file-backed
  - no GitHub API calls
  - no `gh` calls
  - no GraphQL/REST calls
  - no network service calls
  - no local/cloud/Codex/ChatGPT/Ollama calls
  - no live GitHub discovery/validation
- M39 boundary confirmations:
  - local-first, file-backed agent/handoff/orchestration/escalation management via Hub API and static UI
  - no `gh`, no GitHub API calls, no network services
  - no local LLM calls, no cloud LLM calls, no Codex/ChatGPT/Ollama calls
  - no external API calls
  - orchestration and escalation remain plan-only
  - no agent execution and no model invocation
  - handoff preview is local-only and does not post anywhere
  - M40 reporting/dashboard/operator workflow surfaces are implemented as local-only report/plan-only flows
  - authentication and production deployment remain unimplemented
- Next-phase planning focus:
  - richer guided Hub workflows and cross-section automation
  - optional execution gates with explicit user approval
  - authentication hardening if exposed beyond localhost
  - controlled GitHub sync execution behind explicit safety gates
  - optional LLM execution behind explicit user-approved gates

## Canonical Documents

- `docs/context/BUILD_STATE.md`
- `docs/context/AGENT_CONTEXT.md`
- `docs/roadmap/ROADMAP.md`
- `docs/operator/LOCAL_OPERATOR_USAGE.md`
- `docs/architecture/AUTOMATIC_CANONICAL_EVIDENCE_EMISSION_CONTRACT.md`
- `docs/architecture/MILESTONE_CLOSEOUT_PREFLIGHT_CONTRACT.md`
- `docs/architecture/RUNNABLE_SKELETON.md`

## Current M25 Commands

- `python -m aresforge inspect-automatic-canonical-evidence-emission-contract`
- `python -m aresforge generate-child-closeout-evidence-bundle --parent-issue <parent> --child-issue <child>`
- `python -m aresforge generate-pr-evidence-bundle --issue <child> --pr <pr>`
- `python -m aresforge generate-parent-closeout-evidence-bundle --parent-issue <parent>`
- `python -m aresforge generate-evidence-comment-template --issue <issue>`
- `python -m aresforge check-closeout-readiness-by-construction --parent-issue <parent>`

## M26 Continuity Command

- `python -m aresforge generate-handoff-package --output <path> [--format markdown|json] [--include-doc-excerpts] [--force]`
- If `--output` is omitted:
  - markdown is printed to stdout by default
  - JSON is printed to stdout when `--format json`

## Offline State-File Commands

- `python -m aresforge inspect-milestone-state --parent-issue <n> --state-file <path>`
- `python -m aresforge check-milestone-evidence-readiness --parent-issue <n> --state-file <path>`
- `python -m aresforge inspect-parent-closeout-readiness --parent-issue <n> --state-file <path>`
- `python -m aresforge generate-parent-closeout-evidence-bundle --parent-issue <n> --state-file <path>`
- `python -m aresforge check-closeout-readiness-by-construction --parent-issue <n> --state-file <path>`
- Example fixture: `tests/fixtures/offline_state/parent_closeout_ready.json`.
- Validation checkpoint: `python -m pytest` passed with `502` tests.

## M25 Child/PR Mapping

- `#431` -> child `#422`
- `#432` -> child `#423`
- `#433` -> child `#424`
- `#434` -> child `#425`
- `#435` -> child `#426`
- `#436` -> child `#427`
- `#437` -> child `#428`
- `#438` -> child `#429`
- `pending` -> child `#430` (this reconciliation PR)

## Prohibited Behaviors

- autonomous broad mutation
- bulk issue closure
- parent closeout before all children are closed/accounted for
- prior milestone mutation unless explicitly required
- nested markdown fences inside PowerShell here-string issue/comment bodies

## Validation Snapshot

- `git diff --check`
- `python -m pytest`
- `python -m aresforge inspect-repo-governance`
- `python -m aresforge inspect-milestone-state --parent-issue 421`
- `python -m aresforge check-milestone-evidence-readiness --parent-issue 421`
- `python -m aresforge inspect-parent-closeout-readiness --parent-issue 421`
- `python -m aresforge inspect-milestone-closeout-preflight --parent-issue 421`
- `python -m aresforge inspect-automatic-canonical-evidence-emission-contract`
- `python -m aresforge check-closeout-readiness-by-construction --parent-issue 421`

## Known Limitations

- No actual LLM invocation yet.
- No cloud LLM API integration yet.
- No GitHub sync execution yet.
- Hub now provides M40 local management/planning/reporting workflows; execution gates/auth/deployment hardening remain future work.
- No cross-machine coordination yet.
- No background daemon/scheduler yet.
