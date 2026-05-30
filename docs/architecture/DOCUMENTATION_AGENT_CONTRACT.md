# Documentation Agent Contract

## M91 Documentation Agent v1

Documentation Agent v1 is a local-only, source-of-truth documentation reconciliation contract.

The agent exists to prepare future automation that can update documentation after validated local changes. M91 is contract-first: the implemented surface is read-only contract inspection, not documentation mutation.

## Scope

Allowed work:

- inspect changed files, queue evidence, validation results, and smoke checks
- prepare a documentation reconciliation plan
- identify source-of-truth docs that need updates
- list evidence gaps before documentation is updated
- prepare future operator-reviewed documentation patch proposals

Forbidden work:

- automatic documentation updates from model output
- automatic queue completion
- automatic next-item execution
- GitHub API calls
- `gh` calls
- issues, PRs, workflows, daemon, watcher, scheduler, or external workflow behavior

## Source Docs

Documentation Agent v1 treats these as source-of-truth docs:

- `docs/context/BUILD_STATE.md`
- `docs/context/AGENT_CONTEXT.md`
- `docs/roadmap/ROADMAP.md`
- `docs/architecture/RUNNABLE_SKELETON.md`
- `docs/operator/LOCAL_OPERATOR_USAGE.md`

Future milestones may expand this list only through an explicit contract update.

M95 confirms the documentation agent contract also treats these architecture docs as required review inputs when local LLM, routing, and documentation-agent behavior changes:

- `docs/architecture/LOCAL_LLM_ENVIRONMENT_CONTRACT.md`
- `docs/architecture/AGENT_LLM_ROUTING_STRATEGY.md`
- `docs/architecture/DOCUMENTATION_AGENT_CONTRACT.md`

## Evidence Required

Before documentation is updated, the operator must have:

- implementation commit hash or local diff summary
- queue item id and milestone identifier
- validation commands and results
- smoke checks and results
- `git diff --check` result
- files changed summary
- operator statement that documentation reconciliation is required
- explicit source docs selected for update

## Modes

Plan mode is available now and is non-mutating. It may produce:

- docs to review
- evidence gaps
- recommended documentation updates
- blocked reasons
- next safe action

Future gated apply mode is not available in M91. It requires a later milestone and explicit operator approval phrase:

    APPROVE DOCUMENTATION AGENT APPLY

Apply mode must also require validation evidence, selected source docs, worktree review, and post-apply validation. Queue completion remains a separate explicit evidence command.

M92 plan generation and M95 reconciliation are manual documentation workflows. They may identify stale sections and recommended updates, but they do not authorize automatic documentation rewrites or model-generated apply behavior.

M96 is post-sprint planning and prioritization. It may update source-of-truth docs directly as an operator-authored reconciliation step, but it does not add Documentation Agent apply mode and does not permit model-generated documentation rewrites.

M97 may select `documentation_agent_dry_run` for documentation or reconciliation queue items. This is only a dispatch plan lane and planned artifact intent. It does not execute a documentation agent, generate documentation patches, apply documentation changes, complete queue items, or create an apply mode. M100 remains the planned milestone for a documentation-agent dry-run review workflow.

M98 generates Codex prompt dispatch artifacts only for `codex_prompt_artifact`. If M97 selects `documentation_agent_dry_run`, M98 blocks generation and emits no Codex prompt text. This preserves M100 as the future documentation-agent dry-run review workflow and does not add documentation-agent execution, patch generation, apply mode, or automatic documentation mutation.

M99 validates Local LLM advisory dry-run readiness only for `local_llm_advisory`. If M97 selects `documentation_agent_dry_run`, M99 blocks readiness and emits no local LLM advisory approval. This preserves M100 as the future documentation-agent dry-run review workflow and does not add documentation-agent execution, patch generation, apply mode, or automatic documentation mutation.

## Safety Boundaries

- local-only
- read-only from contract inspection
- no automatic documentation updates
- no documentation mutation from model output
- no queue mutation or queue completion
- no automatic next-item execution
- no GitHub API or `gh`
- no issues, PRs, workflows, daemons, watchers, schedulers, or external workflow behavior
