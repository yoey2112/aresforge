# PROJECT_STANDARDIZATION_PLAN

## Scope
This standardization plan applies to every AresForge-managed project. It defines the minimum operating package AresForge must generate, validate, and maintain so managed projects are execution-ready, auditable, and locally operable.

## 1. Required project docs
Each managed project must include:
- `README.md` with purpose, status, local run/test commands.
- `docs/ARCHITECTURE.md` with current implementation boundaries.
- `docs/ROADMAP.md` with milestone phases and gates.
- `docs/CURRENT_STATE.md` separating implemented vs planned.
- `docs/OPERATIONS.md` with local execution/recovery procedures.

## 2. Required coding-agent context files
Each managed project must include:
- `.agent/AGENT_CONTEXT.md` with repo-specific constraints and workflows.
- `.agent/AGENT_REGISTRY.md` with available agent profiles and responsibilities.
- `.agent/EXECUTION_BOUNDARIES.md` defining mutation and approval limits.

## 3. Required AI-agent rules/guidelines
Each managed project must include:
- `.agent/RULES.md` with local-first policy, safety constraints, and prohibited operations.
- `.agent/QUALITY_GATES.md` defining test/lint/validation thresholds.
- `.agent/APPROVAL_GATES.md` describing required human approvals by risk level.

## 4. Required architecture files
Each managed project must include:
- `docs/architecture/SYSTEM_CONTEXT.md`.
- `docs/architecture/COMPONENT_MAP.md`.
- `docs/architecture/STATE_MODEL.md` (authoritative state boundaries).
- `docs/architecture/INTEGRATION_BOUNDARIES.md` (local and external adapter limits).

## 5. Required task/queue structure
Each managed project must include local queue artifacts:
- `artifacts/queue/intake/` for raw task intake.
- `artifacts/queue/ready/` for approved executable tasks.
- `artifacts/queue/runs/` for execution run records.
- `artifacts/queue/archive/` for completed/aborted tasks.
- Deterministic task schema with status transitions: `intake -> planned -> approved -> running -> validated -> closed`.

## 6. Required validation commands
Each managed project must declare and keep green:
- Primary regression command (e.g., `python -m pytest` or equivalent).
- Focused smoke command for core runtime.
- Static quality command(s) (lint/type checks where applicable).
- Diff hygiene check (`git diff --check`).
All commands must be listed in `docs/OPERATIONS.md` and runnable locally.

## 7. Required completion criteria
A task is complete only when:
- Implementation matches task scope.
- Required validation commands pass.
- Required docs/context artifacts are updated.
- Decision log and gap register are reconciled.
- Human approval recorded when crossing defined risk gates.

## 8. Required project handoff package
Each completed milestone must emit a local handoff package including:
- Scope summary and changed files.
- Validation evidence.
- Outstanding risks.
- Follow-up queue entries.
- Approval records and decision references.

## 9. Required decision log
Each managed project must maintain `docs/DECISION_LOG.md` with:
- Date, decision, rationale, alternatives considered.
- Impacted components and rollback implications.
- Approver identity when approval gates apply.

## 10. Required gap register
Each managed project must maintain `docs/GAP_REGISTER.md` with:
- Gap ID, severity, status, owner.
- Evidence source and last-reviewed date.
- Planned resolution milestone and acceptance criteria.

## 11. Required project-specific agent profiles
Each managed project must define profiles such as:
- Implementation agent.
- Validation agent.
- Documentation agent.
- Reconciliation/review agent.
Profiles must include permitted actions, required inputs, and output contract.

## 12. Required project-specific LLM routing notes
Each managed project must define `docs/LLM_ROUTING_NOTES.md` covering:
- Default local model/provider path.
- Escalation criteria for cloud/provider handoff.
- Data sensitivity constraints and redaction rules.
- Fallback strategy and failure handling.

## 13. Required documentation update process
Each project must enforce:
- Doc update checklist for every milestone/task closeout.
- Implemented-vs-planned labeling in architecture and roadmap docs.
- Periodic local audit reconciliation (scheduled assess-repo snapshots).

## 14. Required source-of-truth rules
Each project must explicitly define and enforce:
- Authoritative source for runtime state entities.
- Authoritative source for roadmap/status entities.
- Precedence rules when docs, config, and runtime behavior disagree.
- Conflict resolution workflow and required human approval for overrides.

## Enforcement model for AresForge
AresForge should treat this package as a bootstrap-and-verify contract for every managed project:
- Bootstrap: generate required files/templates/structures for new or adopted projects.
- Verify: run contract checks that fail when required artifacts are missing or stale.
- Gate: block agent execution progression when mandatory standardization elements are noncompliant.
