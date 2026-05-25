# ARESFORGE_RECOVERY_BASELINE

## 1. Executive summary
AresForge is in a controlled production pause because the repository currently demonstrates strong local planning, governance, audit, and evidence-generation capability, but is not yet runtime-complete as a local AI software factory. This baseline consolidates current implementation truth, plan-only scope, gates, and required approvals into one recovery source of truth.

## 2. Reason for production pause
Production implementation is paused to prevent mismatch between documented/runtime claims and proven execution behavior, and to avoid premature expansion into high-risk areas (state ambiguity, multi-LLM routing, external mutation).

Pause drivers:
- High-severity documentation/runtime drift (`docs_claim_runtime_gap`).
- Unresolved state authority boundary between file-backed and DB-backed state (`state_strategy_unclear`).
- Significant plan-only orchestration surface that should not be treated as runtime-complete.
- External mutation/sync pathways must remain deferred until strict mutation gates are satisfied.

## 3. Verified current baseline
Verified from existing audit artifacts and baselines:
- Deterministic local read-only assessment capability is operational (`aresforge assess-repo` outputs under `docs/audit`).
- Local foundation exists across CLI, config, DB connectivity/migrations/repository, artifact storage, and routing primitives.
- Hub foundation exists (backend/static frontend baseline) with corresponding tests.
- Local governance/planning/reporting operators are broad and heavily test-covered.
- Local Ollama adapter exists as current LLM integration foundation.
- Validation baseline remains strong (`python -m pytest` previously established at 797 passed).
- `git diff --check` baseline indicates no blocking errors; LF/CRLF warnings may still appear.

## 4. What is implemented
Implemented and evidenced at repository level:
- CLI command surface for local operations and audit workflows.
- Database schema and migrations for core platform state.
- Artifact and evidence generation/reporting mechanisms.
- Managed project registry and local project workflow scaffolding.
- Project queue/planning surfaces and milestone/readiness reporting surfaces.
- Local review, handoff packaging, and validation summary generation surfaces.
- Substantial automated test coverage across operator and CLI modules.

Important implementation qualifier:
- Implemented modules are not equivalent to production runtime completeness. Test-backed planning/reporting behavior is strong; end-to-end autonomous runtime hardening is still incomplete.

## 5. What is plan-only or aspirational
The current audit classification indicates meaningful plan-only and aspirational scope remains.

Plan-only / contract-heavy / simulation-heavy areas include representative families such as:
- `self_managed_*_contract`, `*_simulation`, `*_planner` modules.
- `ready_issue_*` and `sprint_issue_*` pipelines where behavior is planning-first.
- Closeout/PR evidence preflight/marker/template contract layers.
- Repo governance/bootstrap contract and planning layers.
- GitHub sync/mutation planning/audit-related surfaces not approved for active external mutation.

Aspirational/stale signals:
- Files flagged as stale_or_aspirational in audit outputs.
- Docs that imply runtime automation beyond implementation proof.

## 6. Critical gaps
Critical and medium-priority gaps currently governing recovery:
- `docs_claim_runtime_gap` (high): documentation claims exceed verified implementation proof.
- `state_strategy_unclear` (medium): authoritative source model between DB and file-state is unresolved.
- No `.github/workflows` automation baseline (medium), and external mutation/sync remains intentionally deferred.
- Production-grade queue-to-execution lifecycle (pause/resume/recovery determinism) is not yet accepted as complete.
- Managed-project standardization is not yet enforced as a hard execution contract across all managed projects.
- Multi-provider LLM routing is not yet hardened beyond local-first foundation.

## 7. Definition of complete
AresForge is complete when it can locally manage multiple projects end-to-end with deterministic, auditable execution and enforced managed-project standards before any optional external sync.

Completion criteria:
- Deterministic state authority and transitions are implemented, tested, and approved.
- Managed-project standardization contract is bootstrap-enforced and verification-gated.
- Local queue-to-agent execution supports execute/pause/resume/recover with reproducible evidence.
- Validation and documentation gates are mandatory for progression and closeout.
- Human approval checkpoints are enforced for high-risk operations.
- External mutation/sync remains optional and disabled by default unless mutation gate approval is achieved.

## 8. Approved target architecture
Approved target architecture (local-first path):
- Hub dashboard for portfolio visibility.
- Managed project registry and active project selection.
- Project factory generating standardized managed-project operating bundles.
- Local intake/queue lifecycle with deterministic status transitions.
- Agent profile system and execution lifecycle engine.
- Agent-to-agent context/artifact handoff protocol.
- LLM routing abstraction with Ollama-first local path and optional later cloud adapters.
- Validation/documentation/evidence emission integrated as lifecycle gates.
- Human approval model at mutation/release boundaries.
- Reporting/audit layer as continuous controls.
- Optional GitHub sync/mutation integration only after explicit gate approval.

## 9. Freeze rules before production resumes
The following freezes remain in force:
- Freeze expansion into new orchestration domains until state authority is resolved.
- Freeze external GitHub mutation/sync to planning/audit-only mode.
- Freeze multi-provider routing rollout until single-provider local runtime reliability is accepted.
- Freeze autonomous execution beyond sandboxed/local gated runs until deterministic recovery criteria pass.
- Allow only audit reconciliation, state model normalization, gate definition, managed-project standardization enforcement, and runtime-hardening work tied to this baseline.

## 10. Phase gates
Gate A - Audit Truth Gate:
- Implementation-vs-doc claims reconciled.
- Critical claim drift removed or explicitly marked as planned.

Gate B - State Authority Gate:
- Approved DB/file authority matrix.
- Deterministic lifecycle transitions defined and tested.

Gate C - Local Execution Gate:
- Queue -> execution -> pause/resume/recover behavior proven locally with replayable run records.

Gate D - Validation/Documentation Gate:
- Mandatory validation commands and evidence artifacts enforced before task closeout.

Gate E - Routing Gate:
- Provider-neutral contract and fallback/consistency tests pass for local-first routing.

Gate F - Mutation Gate:
- External mutation/sync remains disabled until approvals, audit logs, and dry-run parity criteria pass.

Gate G - Production Gate:
- Reliability, observability, recovery, rollback, and approval policies validated on representative managed projects.

## 11. Milestone sequence from current state to complete
1. Audit reconciliation and source-of-truth normalization.
2. State authority contract finalization (DB vs file) with transition rules and migration policy.
3. Managed-project standardization bootstrap-and-verify enforcement.
4. Local queue-to-agent execution MVP with strict human gates and replayability.
5. Validation/documentation gates integrated into execution lifecycle progression.
6. Agent-to-agent handoff and artifact contract hardening.
7. Multi-LLM routing abstraction rollout (local-first, then optional provider expansion).
8. External GitHub sync/mutation reintroduction (still optional), only after Mutation Gate approval.
9. Production hardening and release acceptance across managed-project portfolio.

## 12. First five implementation milestones after audit
1. Reconcile docs to clearly label implemented vs planned surfaces and remove runtime overstatement.
2. Approve and implement an explicit state authority matrix with deterministic transition tests.
3. Implement managed-project bootstrap package generator plus compliance verifier.
4. Deliver local single-lane queue-to-agent execution MVP with enforceable human approval checkpoints.
5. Enforce validation + documentation + evidence artifacts as mandatory post-run closeout gates.

## 13. Managed-project standardization contract
Managed-project standardization is a core product capability, not documentation overhead.

Contract requirements (must be bootstrapped and verified by AresForge):
- Required project docs: `README.md`, `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, `docs/CURRENT_STATE.md`, `docs/OPERATIONS.md`.
- Required agent context: `.agent/AGENT_CONTEXT.md`, `.agent/AGENT_REGISTRY.md`, `.agent/EXECUTION_BOUNDARIES.md`.
- Required rules/gates: `.agent/RULES.md`, `.agent/QUALITY_GATES.md`, `.agent/APPROVAL_GATES.md`.
- Required architecture artifacts: `docs/architecture/SYSTEM_CONTEXT.md`, `COMPONENT_MAP.md`, `STATE_MODEL.md`, `INTEGRATION_BOUNDARIES.md`.
- Required queue structure and deterministic status model.
- Required validation commands declared and kept green.
- Required decision log and gap register maintenance.
- Required milestone handoff package contents.

Enforcement model:
- Bootstrap required package for each managed project.
- Verify compliance continuously.
- Gate execution progression when noncompliant.

## 14. State authority decision required
Unresolved decision (blocking Gate B):
- For each lifecycle entity, decide one authoritative state source (DB or file) and define read/write precedence.

Decision artifact required:
- Approved state authority matrix covering runtime entities, planning entities, queue/run entities, and reconciliation artifacts.
- Conflict-resolution workflow and human override policy.
- Migration/reconciliation policy for existing mixed-state records.

No production execution resume is permitted without this signed decision.

## 15. Agent execution readiness requirements
Before broader execution rollout:
- Final lifecycle state machine approved.
- Tool/mutation boundaries codified and enforced.
- Minimal execution contract implemented: queued task -> run -> validation -> recorded outcome.
- Deterministic pause/resume/recovery tests passing.
- Replayability and audit trail integrity validated.
- Human gate checkpoints functioning and mandatory.

## 16. Multi-LLM routing readiness requirements
Before multi-provider rollout:
- Single-provider local (Ollama-first) reliability accepted first.
- Provider-neutral request/response contract defined.
- Error taxonomy and fallback policy implemented and tested.
- Routing policy tests for capability/latency/cost classes pass.
- Data sensitivity and local-vs-cloud escalation policy approved.

## 17. GitHub sync/mutation readiness requirements
External sync/mutation remains deferred.

Readiness prerequisites:
- Mutation disabled-by-default policy remains active.
- Per-mutation-class human approvals implemented.
- Complete mutation audit logging and traceability validated.
- Local dry-run simulation parity demonstrated for proposed mutations.
- Mutation Gate (Gate F) explicitly approved before any enablement.

## 18. Documentation/source-of-truth rules
Required operating rule set:
- Every architecture/lifecycle document must label status: implemented, experimental, or planned.
- When docs and runtime diverge, authoritative precedence follows approved source-of-truth policy.
- Gate advancement requires doc updates matching implementation evidence.
- Audit snapshots in `docs/audit/` remain periodic drift controls.
- Plan-only modules must never be represented as runtime-complete.

## 19. Human approval model
Approval model is mandatory for risk-managed progression:
- Defined approver roles (operator/maintainer).
- Signed decision entries for gate passage.
- Approval checkpoints required at execution enablement, routing expansion, external mutation, and production release boundaries.
- Gate advancement is blocked without recorded approval artifacts.

## 20. Immediate next recommended action
Execute Milestone 1 immediately:
- Run a focused documentation reconciliation pass to remove runtime overstatement and apply implemented/planned labeling across operator/runtime architecture docs, then record the reconciliation in the audit decision log and prepare Gate A evidence for approval.

Unresolved decisions requiring explicit human approval now:
- Final state authority matrix ownership and precedence model.
- Exact acceptance thresholds for Gate C deterministic recovery tests.
- Approval role assignments for Gates B through G.
