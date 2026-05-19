# AresForge Agent Skills Model

## Purpose

This document defines how AresForge should represent reusable agent skills inside the repository.

The model exists so future human-guided agents, documentation agents, local AI reviewers, PR validation agents, and the future AresForge dashboard can reuse project-specific operating instructions without depending on an external agent framework.

During M0, M1, and M2 foundation work, this is a documentation model only. It does not create runnable skills, agent automation, auto-merge, autonomous issue closure, or autonomous approval.

## Decision Summary

AresForge will define its own repo-owned markdown skill model first.

External skill frameworks may be used as references, inspiration, or future adapter targets, but they are not required to build, review, or operate AresForge during M0, M1, or M2 foundation work.

The canonical AresForge skill format is a reviewable markdown file stored in the repository. Each skill must describe its purpose, scope, required inputs, execution boundaries, human approval boundaries, documentation impact, validation expectations, and evidence requirements.

## What An AresForge Skill Is

An AresForge skill is a reusable, repo-owned markdown instruction package for a bounded agent capability.

A skill should help an agent perform a repeatable project task consistently, such as planning an issue, synchronizing documentation, reviewing Ollama evidence, validating a PR, or updating build state.

A skill is part of the project memory layer. It should be understandable by a human reviewer without requiring a specific agent product, plugin runtime, model provider, or local automation system.

## What An AresForge Skill Is Not

An AresForge skill is not:

- A hidden prompt stored outside the repository.
- A required dependency on Codex, Superpowers, Claude, ChatGPT, Ollama, or any other external framework.
- A script, workflow, package, or executable automation by default.
- Permission to merge, approve, close issues, delete data, publish releases, or change repository settings.
- A replacement for issue acceptance criteria, governance documentation, PR validation, or human approval.
- Evidence that a future capability is already active.

## Required Properties Of Every Skill

Every AresForge skill should include:

| Property | Requirement |
|---|---|
| Name | Stable human-readable skill name. |
| Purpose | The reusable capability the skill provides. |
| When to use | Conditions that should trigger the skill. |
| When not to use | Conditions that should prevent or limit use. |
| Inputs | Source-of-truth files, issue data, PR data, validation evidence, or human decisions required before use. |
| Outputs | Expected edits, summaries, evidence, warnings, or recommendations. |
| Scope boundaries | What the skill is allowed to affect. |
| Execution boundaries | Whether the skill is documentation-only, advisory, command-guided, or future automated. |
| Human approval boundaries | Actions that require explicit human approval. |
| Documentation impact | Docs the skill must review or update when relevant. |
| Validation expectations | Checks or review steps expected after use. |
| Evidence requirements | What the agent must report back for review. |
| Related docs | Links to source-of-truth docs that govern the skill. |
| Lifecycle status | Draft, active, deprecated, or archived. |

During M0, M1, and M2 foundation work, all skills should be treated as advisory and manually executed unless a later human-approved issue changes that boundary.

## Repo Structure

The initial draft repo-owned skill structure is:

- .agent/
  - AGENT_REGISTRY.md
  - skills/
    - github-operations/
      - SKILL.md
    - documentation-sync/
      - SKILL.md
    - ollama-evidence-review/
      - SKILL.md
    - issue-planning/
      - SKILL.md
    - pr-validation/
      - SKILL.md
    - build-state-update/
      - SKILL.md

The `.agent` folder is a documentation scaffold only. Draft skill files are advisory and manually executed until future governance explicitly approves a different execution model.

The local operator workflow defined in `docs/architecture/LOCAL_OPERATOR_WORKFLOW.md` may package skill inputs, prompt context, validation checklists, and evidence summaries for human-guided sessions. During M2, it is a design-only operator model and does not execute skills or turn markdown skills into runnable automation.

## Initial Proposed Skill Set

Initial AresForge skills should map to already documented M0 work:

| Skill | Purpose | Primary source-of-truth docs |
|---|---|---|
| GitHub operations | Guide safe issue, branch, PR, label, milestone, and evidence handling. | docs/context/PROJECT_CONTEXT.md, docs/governance/SELF_MANAGEMENT_MODEL.md |
| Documentation sync | Run freshness checks and apply required documentation updates for changed work. | docs/agents/DOCUMENTATION_FRESHNESS_CHECKS.md, docs/agents/DOCUMENTATION_AGENTS.md, docs/context/AGENT_CONTEXT.md |
| Ollama evidence review | Review local model validation evidence and limitations. | docs/validation/, docs/governance/PR_VALIDATION_MODEL.md |
| Issue planning | Convert approved project goals into scoped issues, prompts, and review expectations. | docs/roadmap/ROADMAP.md, docs/prompts/CODEX_PROMPT_STANDARD.md |
| PR validation | Evaluate PR evidence, risk, documentation impact, and merge-readiness recommendation. | docs/governance/PR_VALIDATION_MODEL.md |
| Build-state update | Keep current phase, active work, completed work, blockers, and next steps current. | docs/context/BUILD_STATE.md, docs/governance/SELF_MANAGEMENT_MODEL.md |

## Skill Lifecycle

Skills should follow a lightweight lifecycle:

| Status | Meaning |
|---|---|
| Draft | Proposed skill under review. Not canonical yet. |
| Active | Human-approved skill that agents may use as repo-owned guidance. |
| Deprecated | Superseded skill retained for history. Agents should avoid using it except for context. |
| Archived | Historical skill no longer relevant to active work. |

Skill changes should be made through normal branch and PR review. Material changes to scope, approval boundaries, validation expectations, or autonomy level should be treated as governance-relevant changes.

## Skill Execution Boundaries

During M0, M1, and M2 foundation work:

- Skills are markdown guidance, not autonomous services.
- A human-guided agent session may follow a skill manually.
- Skills may recommend commands, checks, or documentation updates only when those actions are already allowed by the issue and governance docs.
- Skills must not create hidden execution paths outside GitHub, repository docs, or human-reviewed PRs.
- Skills must not imply that future automation exists before it is implemented and approved.

Future phases may introduce adapters, dashboards, registries, or execution logs, but the repo-owned markdown skill remains the canonical source unless governance explicitly changes that rule.

## Human Approval Boundaries

Skills must require explicit human approval before any action that would:

- Enable auto-merge, autonomous approval, or autonomous issue closure.
- Delete branches or files outside approved cleanup scope.
- Change repository visibility, permissions, secrets, runner settings, or release state.
- Add new external dependencies, package files, workflows, or service integrations.
- Promote future architecture claims as completed functionality.
- Treat AI-generated recommendations as approved decisions.
- Change skill execution from manual guidance to automation.

## Documentation Update Requirements

Skill changes must update related documentation when they affect agent behavior, source-of-truth rules, governance, PR validation, roadmap sequencing, prompt expectations, or build state.

At minimum:

- Agent behavior changes should be reflected in docs/context/AGENT_CONTEXT.md.
- Documentation-agent behavior changes should be reflected in docs/agents/DOCUMENTATION_AGENTS.md.
- Governance or autonomy boundary changes should be reflected in docs/governance/SELF_MANAGEMENT_MODEL.md.
- PR validation impacts should be reflected in docs/governance/PR_VALIDATION_MODEL.md.
- Active work and next-step changes should be reflected in docs/context/BUILD_STATE.md.

Skills should reference existing source-of-truth docs instead of duplicating full governance, validation, or documentation-agent models.

## Validation And Evidence Requirements

Every new or changed skill should include enough evidence for manual review.

Expected evidence includes:

- Skill file changed.
- Related docs reviewed and updated or explicitly left unchanged.
- Reason the skill is needed.
- Scope and non-scope summary.
- Human approval boundaries.
- Validation expectations.
- Known risks and limitations.
- Documentation impact summary.
- Commands or checks run for the PR.

For M0, M1, and M2 foundation documentation-only skill work, a diff review, `git diff --check`, `git status --short`, and issue-specific documentation scans are usually sufficient.

## External Framework Evaluation

### AresForge-Native Markdown Skills

Repo-owned markdown skills best match the current M0 source-of-truth model.

Strengths:

- Reviewable through normal GitHub PRs.
- Portable across human reviewers and future agents.
- Aligned with documentation-as-project-memory.
- Does not require new dependencies or runtimes.
- Easy to audit for scope, boundaries, evidence, and approval requirements.

Limitations:

- Manual use depends on agent discipline.
- No built-in discovery, execution logging, or compatibility layer yet.
- Requires future registry and validation conventions as the skill set grows.

Decision: Use as the canonical AresForge model.

### Codex-Compatible Prompt, Plugin, And Extension Patterns

Codex-compatible patterns may help future implementation sessions discover or apply skills more consistently.

Strengths:

- Useful for coding-agent handoffs and local repository work.
- Can align with the existing Codex prompt standard.
- May support future plugin or extension adapters.

Limitations:

- Product-specific formats can reduce portability.
- Hidden or external configuration would conflict with repo-owned source-of-truth rules.
- Codex compatibility should not become a requirement for AresForge skill use.

Decision: Treat as a possible adapter target, not the canonical model.

### Superpowers-Style Reusable Agent Capability Frameworks

Superpowers-style frameworks are useful references for reusable agent capabilities, capability discovery, and repeatable agent workflows.

Strengths:

- Encourages modular reusable instructions.
- Helps separate general capability guidance from one-off prompts.
- Provides a useful mental model for future agent capability libraries.

Limitations:

- External framework dependency would reduce AresForge ownership.
- Framework-specific lifecycle or execution behavior may not match M0 governance.
- Reviewers should not need a Superpowers runtime to understand or approve AresForge skills.

Decision: Use as inspiration only unless a future issue approves an adapter.

### Ollama And Local-Agent Reusable Instruction Patterns

Ollama and local-agent instruction patterns are relevant because AresForge already expects local model review and validation evidence.

Strengths:

- Supports local-first operation.
- Can help standardize prompts for local evidence review.
- Aligns with AresForge's future local model validation service.

Limitations:

- Local model behavior varies by model and prompt format.
- Ollama itself does not define a repo-owned skill governance model.
- Reusable local instructions still need source-of-truth docs, boundaries, and evidence expectations.

Decision: Use for future local adapters and evidence-review prompts, while keeping the canonical skill definition in markdown.

### Portable Markdown Instructions Across Agents

Portable markdown instructions can be read by ChatGPT, Claude, Codex, Ollama-driven local agents, and future agent systems.

Strengths:

- Maximizes portability.
- Keeps review visible in normal diffs.
- Reduces dependency on any single vendor or runtime.
- Matches the current AresForge documentation-first approach.

Limitations:

- Different agents may interpret guidance differently.
- Some platforms may need adapter metadata or prompt wrapping.
- Portability requires plain, explicit boundaries and evidence expectations.

Decision: Use portable markdown as the baseline authoring style for all AresForge skills.

## Risks And Limitations

Risks:

- Skill sprawl if every one-off instruction becomes a skill.
- Confusion between future-state skills and currently active automation.
- Hidden behavior if adapters introduce external configuration not represented in the repo.
- Inconsistent execution if skills do not define inputs, outputs, boundaries, and evidence.
- Governance drift if skills quietly expand agent authority.

Limitations during M0, M1, and M2 foundation work:

- No skill execution engine exists.
- The `.agent` registry exists as draft documentation only.
- No automated skill validation exists.
- Skills are not merge gates, approval mechanisms, or autonomous agents.
- Human review remains required for all PRs and governance-relevant decisions.

## Recommendation

AresForge should adopt repo-owned markdown skills as the canonical reusable agent skills model.

The next implementation step after the draft scaffold is human review of the registry and skill files, followed by focused updates through normal issues and pull requests as the skill model matures.

## Future Adapter Strategy

Future adapters may translate AresForge skills into agent-specific formats when useful.

Potential adapters include:

- Codex prompt or plugin wrappers.
- Local Ollama prompt templates.
- Dashboard skill registry views.
- PR validation checklists derived from skill metadata.
- Cross-agent prompt bundles for ChatGPT, Claude, Codex, Ollama, and future agents.
- Local operator prompt and evidence packages.

Adapter rules:

- The repo-owned markdown skill remains canonical.
- Adapters must not add hidden authority or broaden scope.
- Adapter output must preserve human approval boundaries.
- Adapter behavior must be reviewable and documented before use.
- Any automated adapter execution requires a future governance decision and human approval.
