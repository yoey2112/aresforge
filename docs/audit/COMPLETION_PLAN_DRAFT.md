# COMPLETION_PLAN_DRAFT

## 1. Definition of complete for AresForge
AresForge is complete when it can locally manage multiple projects end-to-end with deterministic state, enforce standardized project operating contracts, execute approved agent workflows with human gates, validate outputs, and produce auditable handoff/reporting artifacts before optional external sync.

## 2. Target architecture
- Hub dashboard for portfolio visibility.
- Managed project registry with active-project selection.
- Project factory that provisions standardized project operating bundles.
- Local intake and queue for tasks/directions/features.
- Agent profile system plus execution lifecycle engine.
- Agent-to-agent context and artifact handoff protocol.
- LLM provider abstraction with local Ollama-first path and optional cloud handoff adapters.
- Validation/documentation agents and evidence emitters.
- Human approval gates at mutation and release boundaries.
- Reporting and audit layer.
- Optional GitHub sync/mutation as explicitly approved downstream integration.

## 3. Current-state architecture
- Implemented: local CLI/governance/audit foundation, DB layer, artifact generation, hub foundation, broad planning/reporting modules, strong tests, local assessment command.
- Partial: queue/orchestration surfaces with mixed active vs plan-only modules.
- Incomplete: production-grade agent runtime lifecycle, hardened multi-LLM routing, unambiguous state authority model, managed-project baseline enforcement, and safe external mutation lifecycle.

## 4. Gap-to-milestone mapping
- `docs_claim_runtime_gap` -> Documentation/source-of-truth reconciliation milestone.
- `state_strategy_unclear` -> State authority and lifecycle contract milestone.
- Plan-only execution surfaces -> Agent runtime MVP milestone.
- Managed-project intent vs enforcement -> Project standardization/bootstrap enforcement milestone.
- Missing external workflow automation -> deferred (not required for local-first immediate phase).

## 5. Proposed milestone sequence from current state to complete
1. Audit reconciliation and source-of-truth normalization.
2. State authority contract (DB vs file) and migration policy finalization.
3. Managed-project standardization bootstrap (required files/rules/validation contract generation and verification).
4. Local queue-to-agent execution MVP with strict human gates and replayable state transitions.
5. Validation/documentation agent integration into the lifecycle.
6. Agent-to-agent context handoff and artifact contract hardening.
7. Multi-LLM routing abstraction rollout (local-first, then optional cloud adapters).
8. Optional GitHub sync/mutation reintroduction (explicitly gated and auditable).
9. Production deployment hardening and release criteria.

## 6. Explicit phase gates
- Gate A: Audit truth gate: docs and implementation claims reconciled; no critical claim drift.
- Gate B: State gate: approved single state authority model with deterministic transitions.
- Gate C: Execution gate: local runtime can execute, pause, resume, and recover queued work deterministically.
- Gate D: Validation gate: automated validation and documentation outputs required for lifecycle progression.
- Gate E: Routing gate: provider abstraction passes fallback/consistency tests.
- Gate F: Mutation gate: external mutation path remains disabled until policy, approvals, and audit logs pass acceptance.
- Gate G: Production gate: reliability, observability, rollback, and human-approval policies validated.

## 7. What must happen before agent execution is implemented
- Finalize lifecycle state machine and authoritative storage model.
- Define hard safety boundaries (allowed tools, mutation boundaries, approval checkpoints).
- Establish minimal execution contract for queued task -> agent run -> validation -> outcome recording.
- Add deterministic replay/recovery tests for interrupted runs.

## 8. What must happen before multi-LLM routing is implemented
- Prove single-provider local runtime reliability first (Ollama path).
- Define provider-neutral request/response contract and error taxonomy.
- Add routing policy tests (capability, cost/latency class, fallback behavior).
- Define data handling policy for local-only vs cloud escalation.

## 9. What must happen before GitHub mutation/sync is reintroduced
- Keep mutation operations disabled by default.
- Require explicit human approval gates per mutation class.
- Enforce audit-log completeness and traceability for every proposed mutation.
- Validate local-only dry-run simulation parity with expected mutation plans.

## 10. What must happen before production deployment
- Phase gates A-F passed.
- Stability and recovery burn-in across representative managed projects.
- Validation strategy baselined with pass/fail thresholds.
- Documentation and runbooks complete for operators and contributors.
- Human approval matrix adopted for high-risk operations.

## 11. Recommended first 5 implementation milestones after audit completion
1. Reconcile and update docs to remove runtime overstatement and mark plan-only surfaces.
2. Approve and implement explicit state authority matrix (DB/file) with migration notes.
3. Implement managed-project bootstrap standard package generator and verifier.
4. Deliver local agent execution MVP (single-agent, single-queue lane, human-gated).
5. Integrate validation+documentation post-run gates with mandatory evidence artifacts.

## 12. Risks and mitigations
- Risk: scope sprawl in orchestration modules.
  - Mitigation: enforce phase gates and milestone WIP limits.
- Risk: state inconsistency across DB/file stores.
  - Mitigation: single authority per lifecycle entity + reconciliation checks.
- Risk: false confidence from planning/test artifacts.
  - Mitigation: require runtime acceptance tests per gate.
- Risk: premature external mutation.
  - Mitigation: default-off policy until mutation gate completion.

## 13. Validation strategy
- Preserve full regression suite (`pytest`) as baseline.
- Add gate-oriented integration tests per milestone.
- Add deterministic scenario fixtures for queue execution, pause/resume, and recovery.
- Add contract tests for project bootstrap standardization outputs.

## 14. Documentation strategy
- Separate docs into: implemented, experimental, and planned.
- Enforce source-of-truth tags in architecture and lifecycle docs.
- Require doc updates as completion criteria for each milestone gate.
- Keep audit snapshots in `docs/audit/` for periodic drift checks.

## 15. Human approval strategy
- Define approval checkpoints for: execution enablement, routing expansion, external mutation, and production release.
- Use explicit approver roles (operator/maintainer) and signed decision entries in local decision logs.
- Block gate advancement without recorded approval artifacts.
