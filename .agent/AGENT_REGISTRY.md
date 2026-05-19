# AresForge Agent Registry

## Purpose

This registry lists repo-owned AresForge agent skills and their current lifecycle status.

The registry is documentation only. During M2 foundation work, skills are advisory project assets that may guide a human-directed agent session, but they are not runnable automation, approval mechanisms, merge gates, or issue-closing systems.

## Operating Boundary

All skills in this registry are manually executed until future governance explicitly approves a different execution model.

This registry does not enable:

- Auto-merge.
- Autonomous approval.
- Autonomous issue closure.
- Autonomous issue creation.
- Destructive automation.
- External framework adapters.
- Runnable skill execution.

## Source Of Truth

Skills must reference source-of-truth documentation instead of replacing it.

Primary governing docs:

- docs/context/PROJECT_CONTEXT.md
- docs/context/AGENT_CONTEXT.md
- docs/context/BUILD_STATE.md
- docs/learning/ERROR_PATTERNS.md
- docs/agents/AGENT_SKILLS_MODEL.md
- docs/agents/DOCUMENTATION_AGENTS.md
- docs/agents/DOCUMENTATION_FRESHNESS_CHECKS.md
- docs/agents/DOCUMENTATION_SYNC_EVIDENCE_PACKAGES.md
- docs/agents/DOCUMENTATION_SYNC_HANDOFF_TEMPLATE.md
- docs/architecture/LOCAL_OPERATOR_WORKFLOW.md
- docs/governance/SELF_MANAGEMENT_MODEL.md
- docs/governance/PR_VALIDATION_MODEL.md
- docs/prompts/CODEX_PROMPT_STANDARD.md
- docs/roadmap/ROADMAP.md

## Registered Skills

| Skill | Path | Lifecycle status | Summary |
|---|---|---|---|
| GitHub operations | .agent/skills/github-operations/SKILL.md | Draft | Guidance for safe issue, branch, PR, label, milestone, and GitHub evidence handling. |
| Documentation sync | .agent/skills/documentation-sync/SKILL.md | Draft | Guidance for running freshness checks and applying required documentation updates. |
| Ollama evidence review | .agent/skills/ollama-evidence-review/SKILL.md | Draft | Guidance for reviewing local Ollama validation evidence and limitations. |
| Issue planning | .agent/skills/issue-planning/SKILL.md | Draft | Guidance for turning approved goals into scoped issues and implementation prompts. |
| PR validation | .agent/skills/pr-validation/SKILL.md | Draft | Guidance for advisory PR review, scoring, evidence review, and merge-readiness recommendations. |
| Build-state update | .agent/skills/build-state-update/SKILL.md | Draft | Guidance for keeping active project state and handoff context current. |

## Registry Maintenance

Skill additions, removals, lifecycle changes, and material scope changes must be made through normal repository changes and human-reviewed pull requests.

Any change that expands a skill from manual guidance toward automation must also update the relevant governance documentation and receive explicit human approval.

Local operator workflow packages may reference registered skills as advisory inputs. They do not execute skills, change skill lifecycle status, or grant automation authority.

Documentation-sync evidence packages may reference registered skills as reviewed source documents. They are evidence artifacts only and do not execute skills, approve changes, merge PRs, close issues, or automate repository behavior.
