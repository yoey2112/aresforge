# AresForge Self-Management Model

## Purpose

This document defines how AresForge manages itself as its first customer.

The model exists so future human-guided agents, Codex sessions, local AI validators, documentation agents, and the future AresForge dashboard can understand the current project state, decide what work is safe to perform, and preserve project memory across implementation sessions.

## Core Principle

AresForge must become its own first managed project.

Every major AresForge capability should first be validated against AresForge itself before being treated as reusable for other managed projects.

## Current Managed Project

The first managed project is:

- Project name: AresForge
- Repository: yoey2112/aresforge
- Local path on Ares: C:\Projects\aresforge
- Current phase: M0 — Self-Bootstrap Foundation
- Current source of truth: GitHub plus repository documentation
- Current execution model: human-guided implementation sessions
- Current review model: human-reviewed pull requests
- Current local AI model validated for review evidence: qwen2.5:32b through Ollama on Ares

## Temporary Source Of Truth

Until the AresForge dashboard exists, the temporary source of truth is split across:

- GitHub repository state
- GitHub issues
- GitHub milestones
- GitHub pull requests
- GitHub labels
- GitHub Actions results and artifacts when available
- Repository documentation under docs/
- Local validation evidence captured during implementation work

When these sources conflict during M0, repository documentation and human decisions take priority over inferred automation behavior.

## Self-Management Loop

AresForge should use the following loop to build itself:

1. Define or refine project context in documentation.
2. Create or update GitHub issues tied to the active milestone.
3. Assign issue scope using labels, milestone, risk, evidence expectations, and agent role.
4. Generate an implementation prompt or command sequence.
5. Perform work on a dedicated branch.
6. Update documentation as part of the work, not after the work.
7. Capture validation evidence.
8. Open a pull request linked to the issue.
9. Review the pull request manually during M0.
10. Merge only after acceptance criteria and documentation impact are satisfied.
11. Let GitHub close linked issues only after merge.
12. Update build state and handoff context for the next implementation session.

## Current M0 Operating Rules

During M0:

- All implementation work is manually guided.
- All documentation updates are manually reviewed.
- All pull requests require human review before merge.
- Local AI review may produce evidence, but it is not a merge gate yet.
- Agents may recommend work, but they must not autonomously merge, close issues, delete data, or enable destructive automation.
- Temporary evidence folders such as tmp/ must not be committed unless explicitly required by an issue.
- GitHub milestone number or ID should be preferred over milestone title matching in scripts and validation commands.
- Documentation must remain the durable project memory layer until the dashboard exists.

## Future Dashboard State Fields

The future AresForge dashboard should represent project state using fields such as:

| Field | Purpose |
|---|---|
| Project Name | Human-readable project identity |
| Project Key | Stable project identifier |
| Repository Owner | GitHub owner or organization |
| Repository Name | GitHub repository name |
| Local Path | Local working path when applicable |
| Current Phase | Active roadmap phase or milestone |
| Current Milestone | GitHub milestone or dashboard milestone |
| Current Issue | Active issue number and title |
| Current Branch | Active implementation branch |
| Current PR | Active pull request number and title |
| Assigned Agent Role | Primary role responsible for the task |
| Supporting Agent Roles | Secondary roles involved in review or documentation |
| Risk Level | Required review and autonomy boundary |
| Evidence Required | Whether validation evidence is required |
| Current Status | Planned, ready, in progress, blocked, review, merged, closed |
| Blockers | Known impediments or missing inputs |
| Acceptance Criteria | Issue-level completion requirements |
| Documentation Impact | Docs changed or docs requiring review |
| Validation Summary | Tests, checks, local AI review, or manual validation result |
| AI Review Decision | PASS, PASS_WITH_LIMITATIONS, NEEDS_HUMAN_REVIEW, or FAIL |
| Human Decision | Human approval, rejection, exception, or requested changes |
| Next Step | Next command, prompt, or implementation action |
| Handoff Summary | Short context package for the next session |
| Last Updated | Last known project-state update timestamp |

## Handoff Process

Every implementation chat should end with a handoff prompt for the next chat when work is complete or when the chat is reaching its turn limit.

The handoff should include:

- Project name
- Repository URL
- Local path
- Current branch
- Latest known main commit, when known
- Current milestone
- Completed issues and PRs relevant to the current phase
- Current issue status
- Files changed
- Validation completed
- Known limitations
- Next recommended step
- Any context docs the next chat should request first

At the start of each new implementation chat, the assistant should state what current context or documentation is needed before continuing.

## Autonomy Levels

Future autonomy should be configurable per project.

Initial proposed levels:

| Level | Name | Description |
|---:|---|---|
| 0 | Manual Execution | Human executes all commands and decisions. |
| 1 | Prompt Assistance | Agents draft plans, prompts, commands, and review checklists. |
| 2 | Branch And PR Assistance | Agents create branches, edits, issues, and PRs; human merges. |
| 3 | Validation Recommendation | Agents validate PRs and recommend merge or changes. |
| 4 | Controlled Auto-Merge | Agents may auto-merge low-risk PRs above a configured score. |
| 5 | Managed Release Loop | Agents manage full release loops with human escalation only. |

AresForge remains at Level 0 or Level 1 during M0.

## Risk Boundaries

The following actions require explicit human approval:

- Enabling auto-merge
- Enabling autonomous issue closure
- Deleting branches or files outside approved cleanup scope
- Changing repository visibility or permissions
- Changing runner security settings
- Adding secrets
- Running destructive local commands
- Publishing releases
- Promoting future architecture claims as completed functionality

## M0 Completion Expectations

The self-management model is considered usable for M0 when:

- AresForge is clearly documented as its own first managed project.
- GitHub plus repository documentation are documented as the temporary source of truth.
- Future dashboard state fields are documented.
- Current M0 constraints are documented.
- The next-step handoff process is documented.
