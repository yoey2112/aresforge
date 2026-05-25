# REPO_FILE_MAP

- Repo path: `C:\Projects\aresforge`
- File count: 493

## Summary by domain
- active_project: 1
- agents: 3
- artifacts: 177
- cli: 1
- config: 1
- configuration: 4
- core_runtime: 4
- database: 7
- docs: 57
- github_integration: 4
- hub_backend: 5
- hub_frontend: 3
- llm_integration: 2
- orchestration: 83
- project_factory: 1
- project_registry: 1
- queue: 1
- scripts: 1
- tests: 118
- unknown: 17
- validation_evidence: 2

## Summary by classification
- active: 42
- candidate_for_review: 16
- docs_only: 40
- foundation: 16
- generated_artifact: 177
- plan_only: 59
- stale_or_aspirational: 17
- test_only: 118
- unknown: 8

## File inventory
| path | domain | classification | purpose | refs (cli/hub/tests/docs) |
|---|---|---|---|---|
| `.agent/AGENT_REGISTRY.md` | unknown | candidate_for_review | # AresForge Agent Registry | 0/0/0/1 |
| `.agent/skills/build-state-update/SKILL.md` | unknown | candidate_for_review | # Build State Update Skill | 0/0/0/1 |
| `.agent/skills/documentation-sync/SKILL.md` | unknown | candidate_for_review | # Documentation Sync Skill | 0/0/0/1 |
| `.agent/skills/github-operations/SKILL.md` | unknown | plan_only | # GitHub Operations Skill | 0/0/0/1 |
| `.agent/skills/issue-planning/SKILL.md` | unknown | candidate_for_review | # Issue Planning Skill | 0/0/0/1 |
| `.agent/skills/ollama-evidence-review/SKILL.md` | unknown | candidate_for_review | # Ollama Evidence Review Skill | 0/0/0/0 |
| `.agent/skills/pr-validation/SKILL.md` | unknown | candidate_for_review | # PR Validation Skill | 0/0/0/1 |
| `.aresforge/state/project_state.json` | unknown | candidate_for_review | { | 1/0/0/1 |
| `.env.example` | unknown | candidate_for_review | ARESFORGE_REPO_ROOT=C:\Projects\aresforge | 0/0/0/1 |
| `.gitignore` | unknown | candidate_for_review | .venv/ | 0/0/0/0 |
| `README.md` | unknown | candidate_for_review | ﻿# AresForge | 0/0/0/0 |
| `artifacts/codex_handoffs/README.md` | artifacts | generated_artifact | # Codex Handoff Artifacts | 0/0/0/0 |
| `artifacts/codex_handoffs/generated/20260520T000257Z-issue-81-codex-handoff.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/codex_handoffs/generated/20260520T000257Z-issue-81-codex-handoff.md` | artifacts | generated_artifact | # Issue 81 Codex handoff | 0/0/0/0 |
| `artifacts/codex_handoffs/generated/20260520T165259Z-issue-112-validation-handoff.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/codex_handoffs/generated/20260520T165259Z-issue-112-validation-handoff.md` | artifacts | generated_artifact | # Issue 112 validation handoff | 0/0/0/0 |
| `artifacts/codex_handoffs/generated/20260520T165416Z-issue-112-validation-handoff.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/codex_handoffs/generated/20260520T165416Z-issue-112-validation-handoff.md` | artifacts | generated_artifact | # Issue 112 validation handoff | 0/0/0/0 |
| `artifacts/codex_handoffs/generated/20260522T161907Z-m15-define-self-managed-milestone-planning-contract-handoff.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/codex_handoffs/generated/20260522T161907Z-m15-define-self-managed-milestone-planning-contract-handoff.md` | artifacts | generated_artifact | # M15: Define self-managed milestone planning contract handoff | 0/0/0/0 |
| `artifacts/codex_handoffs/generated/20260522T163054Z-m15-database-backed-self-managed-milestone-planner-and-run-queue-initializer-handoff.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/codex_handoffs/generated/20260522T163054Z-m15-database-backed-self-managed-milestone-planner-and-run-queue-initializer-handoff.md` | artifacts | generated_artifact | # M15: Database-backed self-managed milestone planner and run queue initializer handoff | 0/0/0/0 |
| `artifacts/codex_handoffs/generated/20260522T164303Z-m15-generate-human-gated-issue-scripts-and-advance-db-backed-run-queue-handoff.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/codex_handoffs/generated/20260522T164303Z-m15-generate-human-gated-issue-scripts-and-advance-db-backed-run-queue-handoff.md` | artifacts | generated_artifact | # M15: Generate human-gated issue scripts and advance DB-backed run queue handoff | 0/0/0/0 |
| `artifacts/codex_handoffs/generated/20260522T165419Z-m15-reconcile-source-of-truth-docs-for-self-managed-milestone-planning-handoff.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/codex_handoffs/generated/20260522T165419Z-m15-reconcile-source-of-truth-docs-for-self-managed-milestone-planning-handoff.md` | artifacts | generated_artifact | # M15: Reconcile source-of-truth docs for self-managed milestone planning handoff | 0/0/0/0 |
| `artifacts/evidence/README.md` | artifacts | generated_artifact | # Evidence Artifacts | 0/0/0/0 |
| `artifacts/evidence/generated/20260520T000257Z-issue-81-evidence-package.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260520T000257Z-issue-81-evidence-package.md` | artifacts | generated_artifact | # Issue 81 evidence package | 0/0/0/0 |
| `artifacts/evidence/generated/20260520T165259Z-issue-112-validation-evidence.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260520T165259Z-issue-112-validation-evidence.md` | artifacts | generated_artifact | # Issue 112 validation evidence | 0/0/0/0 |
| `artifacts/evidence/generated/20260520T165416Z-issue-112-validation-evidence.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260520T165416Z-issue-112-validation-evidence.md` | artifacts | generated_artifact | # Issue 112 validation evidence | 0/0/0/0 |
| `artifacts/evidence/generated/20260520T175506Z-issue-118-pr-124-validation-evidence.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260520T175506Z-issue-118-pr-124-validation-evidence.md` | artifacts | generated_artifact | # Issue 118 PR 124 validation evidence | 0/0/0/0 |
| `artifacts/evidence/generated/20260520T180400Z-issue-119-pr-125-validation-evidence.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260520T180400Z-issue-119-pr-125-validation-evidence.md` | artifacts | generated_artifact | # Issue 119 PR 125 validation evidence | 0/0/0/0 |
| `artifacts/evidence/generated/20260520T181200Z-issue-120-pr-126-validation-evidence.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260520T181200Z-issue-120-pr-126-validation-evidence.md` | artifacts | generated_artifact | # Issue 120 PR 126 validation evidence | 0/0/0/0 |
| `artifacts/evidence/generated/20260520T182832Z-issue-127-validation-evidence-for-batch-ready-issue-operations.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260520T182832Z-issue-127-validation-evidence-for-batch-ready-issue-operations.md` | artifacts | generated_artifact | # Issue 127 validation evidence for batch ready issue operations | 0/0/0/0 |
| `artifacts/evidence/generated/20260520T185120Z-issue-129-pr-130-validation-evidence-for-project-state-summary-command.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260520T185120Z-issue-129-pr-130-validation-evidence-for-project-state-summary-command.md` | artifacts | generated_artifact | # Issue #129 PR #130 validation evidence for project state summary command | 0/0/0/0 |
| `artifacts/evidence/generated/20260520T190045Z-issue-131-reusable-repo-governance-inspection.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260520T190045Z-issue-131-reusable-repo-governance-inspection.md` | artifacts | generated_artifact | # issue-131-reusable-repo-governance-inspection | 0/0/0/0 |
| `artifacts/evidence/generated/20260520T190116Z-pr-137-issue-131-reusable-repo-governance-inspection.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260520T190116Z-pr-137-issue-131-reusable-repo-governance-inspection.md` | artifacts | generated_artifact | # pr-137-issue-131-reusable-repo-governance-inspection | 0/0/0/0 |
| `artifacts/evidence/generated/20260520T191123Z-issue-132-pr-139-managed-repo-bootstrap-contract.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260520T191123Z-issue-132-pr-139-managed-repo-bootstrap-contract.md` | artifacts | generated_artifact | # issue-132-pr-139-managed-repo-bootstrap-contract | 0/0/0/0 |
| `artifacts/evidence/generated/20260520T191957Z-issue-133-pr-140-managed-repo-registry-extension.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260520T191957Z-issue-133-pr-140-managed-repo-registry-extension.md` | artifacts | generated_artifact | # issue-133-pr-140-managed-repo-registry-extension | 0/0/0/0 |
| `artifacts/evidence/generated/20260520T192849Z-issue-134-pr-141-managed-repo-readiness-report.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260520T192849Z-issue-134-pr-141-managed-repo-readiness-report.md` | artifacts | generated_artifact | # issue-134-pr-141-managed-repo-readiness-report | 0/0/0/0 |
| `artifacts/evidence/generated/20260520T193711Z-issue-135-pr-142-bootstrap-plan-generator-evidence.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260520T193711Z-issue-135-pr-142-bootstrap-plan-generator-evidence.md` | artifacts | generated_artifact | # issue-135-pr-142-bootstrap-plan-generator-evidence | 0/0/0/0 |
| `artifacts/evidence/generated/20260520T194852Z-issue-136-pr-143-managed-repo-governance-demo-evidence.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260520T194852Z-issue-136-pr-143-managed-repo-governance-demo-evidence.md` | artifacts | generated_artifact | # issue-136 pr-143 managed-repo-governance-demo evidence | 0/0/0/0 |
| `artifacts/evidence/generated/20260520T200041Z-issue-138-pr-144-governance-stack-source-of-truth-reconciliation-evidence.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260520T200041Z-issue-138-pr-144-governance-stack-source-of-truth-reconciliation-evidence.md` | artifacts | generated_artifact | # issue-138 pr-144 governance-stack-source-of-truth-reconciliation evidence | 0/0/0/0 |
| `artifacts/evidence/generated/20260520T215121Z-issue-158-final-closeout-evidence-pr-161.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260520T215121Z-issue-158-final-closeout-evidence-pr-161.md` | artifacts | generated_artifact | # Issue 158 final closeout evidence PR 161 | 0/0/0/0 |
| `artifacts/evidence/generated/20260520T220053Z-issue-156-final-closeout-evidence-pr-162.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260520T220053Z-issue-156-final-closeout-evidence-pr-162.md` | artifacts | generated_artifact | # Issue 156 final closeout evidence PR 162 | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T163746Z-m15-self-managed-milestone-plan-read-only.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T163746Z-m15-self-managed-milestone-plan-read-only.md` | artifacts | generated_artifact | # M15 self-managed milestone plan read-only | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T163756Z-m15-self-managed-milestone-plan-local-write.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T163756Z-m15-self-managed-milestone-plan-local-write.md` | artifacts | generated_artifact | # M15 self-managed milestone plan local-write | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T163805Z-m15-self-managed-milestone-plan-local-write.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T163805Z-m15-self-managed-milestone-plan-local-write.md` | artifacts | generated_artifact | # M15 self-managed milestone plan local-write | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T164004Z-m15-self-managed-milestone-plan-read-only.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T164004Z-m15-self-managed-milestone-plan-read-only.md` | artifacts | generated_artifact | # M15 self-managed milestone plan read-only | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T164008Z-m15-self-managed-milestone-plan-local-write.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T164008Z-m15-self-managed-milestone-plan-local-write.md` | artifacts | generated_artifact | # M15 self-managed milestone plan local-write | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T164102Z-m15-self-managed-milestone-plan-read-only.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T164102Z-m15-self-managed-milestone-plan-read-only.md` | artifacts | generated_artifact | # M15 self-managed milestone plan read-only | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T164105Z-m15-self-managed-milestone-plan-local-write.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T164105Z-m15-self-managed-milestone-plan-local-write.md` | artifacts | generated_artifact | # M15 self-managed milestone plan local-write | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T164802Z-m15-self-managed-issue-script-read-only.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T164802Z-m15-self-managed-issue-script-read-only.md` | artifacts | generated_artifact | # M15 self-managed issue script read-only | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T164802Z-m15-self-managed-milestone-plan-read-only.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T164802Z-m15-self-managed-milestone-plan-read-only.md` | artifacts | generated_artifact | # M15 self-managed milestone plan read-only | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T164826Z-m15-self-managed-issue-script-read-only.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T164826Z-m15-self-managed-issue-script-read-only.md` | artifacts | generated_artifact | # M15 self-managed issue script read-only | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T164826Z-m15-self-managed-milestone-plan-read-only.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T164826Z-m15-self-managed-milestone-plan-read-only.md` | artifacts | generated_artifact | # M15 self-managed milestone plan read-only | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T164859Z-m15-self-managed-issue-script-read-only.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T164859Z-m15-self-managed-issue-script-read-only.md` | artifacts | generated_artifact | # M15 self-managed issue script read-only | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T164859Z-m15-self-managed-milestone-plan-read-only.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T164859Z-m15-self-managed-milestone-plan-read-only.md` | artifacts | generated_artifact | # M15 self-managed milestone plan read-only | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T164900Z-m15-self-managed-milestone-plan-local-write.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T164900Z-m15-self-managed-milestone-plan-local-write.md` | artifacts | generated_artifact | # M15 self-managed milestone plan local-write | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T165158Z-m15-self-managed-milestone-plan-read-only.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T165158Z-m15-self-managed-milestone-plan-read-only.md` | artifacts | generated_artifact | # M15 self-managed milestone plan read-only | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T165202Z-m15-self-managed-milestone-plan-local-write.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T165202Z-m15-self-managed-milestone-plan-local-write.md` | artifacts | generated_artifact | # M15 self-managed milestone plan local-write | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T165206Z-m15-self-managed-issue-script-read-only.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T165206Z-m15-self-managed-issue-script-read-only.md` | artifacts | generated_artifact | # M15 self-managed issue script read-only | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T165206Z-m15-self-managed-milestone-plan-read-only.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T165206Z-m15-self-managed-milestone-plan-read-only.md` | artifacts | generated_artifact | # M15 self-managed milestone plan read-only | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T165210Z-m15-self-managed-issue-script-read-only.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T165210Z-m15-self-managed-issue-script-read-only.md` | artifacts | generated_artifact | # M15 self-managed issue script read-only | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T165210Z-m15-self-managed-milestone-plan-read-only.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T165210Z-m15-self-managed-milestone-plan-read-only.md` | artifacts | generated_artifact | # M15 self-managed milestone plan read-only | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T165326Z-m15-self-managed-milestone-plan-read-only.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T165326Z-m15-self-managed-milestone-plan-read-only.md` | artifacts | generated_artifact | # M15 self-managed milestone plan read-only | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T165330Z-m15-self-managed-milestone-plan-local-write.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T165330Z-m15-self-managed-milestone-plan-local-write.md` | artifacts | generated_artifact | # M15 self-managed milestone plan local-write | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T165334Z-m15-self-managed-issue-script-read-only.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T165334Z-m15-self-managed-issue-script-read-only.md` | artifacts | generated_artifact | # M15 self-managed issue script read-only | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T165334Z-m15-self-managed-milestone-plan-read-only.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T165334Z-m15-self-managed-milestone-plan-read-only.md` | artifacts | generated_artifact | # M15 self-managed milestone plan read-only | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T165732Z-m15-self-managed-milestone-plan-read-only.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T165732Z-m15-self-managed-milestone-plan-read-only.md` | artifacts | generated_artifact | # M15 self-managed milestone plan read-only | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T165743Z-m15-self-managed-issue-script-read-only.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T165743Z-m15-self-managed-issue-script-read-only.md` | artifacts | generated_artifact | # M15 self-managed issue script read-only | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T165743Z-m15-self-managed-milestone-plan-local-write.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T165743Z-m15-self-managed-milestone-plan-local-write.md` | artifacts | generated_artifact | # M15 self-managed milestone plan local-write | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T165743Z-m15-self-managed-milestone-plan-read-only.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T165743Z-m15-self-managed-milestone-plan-read-only.md` | artifacts | generated_artifact | # M15 self-managed milestone plan read-only | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T165910Z-m15-self-managed-milestone-plan-read-only.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T165910Z-m15-self-managed-milestone-plan-read-only.md` | artifacts | generated_artifact | # M15 self-managed milestone plan read-only | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T165913Z-m15-self-managed-milestone-plan-local-write.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T165913Z-m15-self-managed-milestone-plan-local-write.md` | artifacts | generated_artifact | # M15 self-managed milestone plan local-write | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T165917Z-m15-self-managed-issue-script-read-only.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T165917Z-m15-self-managed-issue-script-read-only.md` | artifacts | generated_artifact | # M15 self-managed issue script read-only | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T165917Z-m15-self-managed-milestone-plan-read-only.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T165917Z-m15-self-managed-milestone-plan-read-only.md` | artifacts | generated_artifact | # M15 self-managed milestone plan read-only | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T170014Z-m15-self-managed-milestone-plan-read-only.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T170014Z-m15-self-managed-milestone-plan-read-only.md` | artifacts | generated_artifact | # M15 self-managed milestone plan read-only | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T170018Z-m15-self-managed-issue-script-read-only.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T170018Z-m15-self-managed-issue-script-read-only.md` | artifacts | generated_artifact | # M15 self-managed issue script read-only | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T170018Z-m15-self-managed-milestone-plan-read-only.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T170018Z-m15-self-managed-milestone-plan-read-only.md` | artifacts | generated_artifact | # M15 self-managed milestone plan read-only | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T173952Z-autonomous-run-run-m16-259-3b3ac68ce1.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T173952Z-autonomous-run-run-m16-259-3b3ac68ce1.md` | artifacts | generated_artifact | # Autonomous run run-m16-259-3b3ac68ce1 | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T174006Z-autonomous-run-run-m16-260-e2e24000e4.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T174006Z-autonomous-run-run-m16-260-e2e24000e4.md` | artifacts | generated_artifact | # Autonomous run run-m16-260-e2e24000e4 | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T174016Z-autonomous-run-run-m16-261-a9017ec308.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T174016Z-autonomous-run-run-m16-261-a9017ec308.md` | artifacts | generated_artifact | # Autonomous run run-m16-261-a9017ec308 | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T174016Z-autonomous-run-run-m16-262-23b486bbb9.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T174016Z-autonomous-run-run-m16-262-23b486bbb9.md` | artifacts | generated_artifact | # Autonomous run run-m16-262-23b486bbb9 | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T174016Z-autonomous-run-run-m16-263-87ab2071e7.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T174016Z-autonomous-run-run-m16-263-87ab2071e7.md` | artifacts | generated_artifact | # Autonomous run run-m16-263-87ab2071e7 | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T174536Z-autonomous-run-run-m16-261-8bb4fcb80c.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T174536Z-autonomous-run-run-m16-261-8bb4fcb80c.md` | artifacts | generated_artifact | # Autonomous run run-m16-261-8bb4fcb80c | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T174610Z-autonomous-run-run-m16-262-3e050d9ef9.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T174610Z-autonomous-run-run-m16-262-3e050d9ef9.md` | artifacts | generated_artifact | # Autonomous run run-m16-262-3e050d9ef9 | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T175157Z-autonomous-run-run-m16-262-9145abdb43.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T175157Z-autonomous-run-run-m16-262-9145abdb43.md` | artifacts | generated_artifact | # Autonomous run run-m16-262-9145abdb43 | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T175251Z-autonomous-run-run-m16-262-0bf31d83bc.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T175251Z-autonomous-run-run-m16-262-0bf31d83bc.md` | artifacts | generated_artifact | # Autonomous run run-m16-262-0bf31d83bc | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T175940Z-autonomous-run-run-m16-262-2cfd176882.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T175940Z-autonomous-run-run-m16-262-2cfd176882.md` | artifacts | generated_artifact | # Autonomous run run-m16-262-2cfd176882 | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T180409Z-autonomous-run-run-m16-262-bf416386e1.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T180409Z-autonomous-run-run-m16-262-bf416386e1.md` | artifacts | generated_artifact | # Autonomous run run-m16-262-bf416386e1 | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T180705Z-autonomous-run-run-m16-262-d85f210ca7.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T180705Z-autonomous-run-run-m16-262-d85f210ca7.md` | artifacts | generated_artifact | # Autonomous run run-m16-262-d85f210ca7 | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T214303Z-m19-sequential-handoff-package-parent-309.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/20260522T214303Z-m19-sequential-handoff-package-parent-309.md` | artifacts | generated_artifact | # Sequential Handoff Package | 0/0/0/0 |
| `artifacts/evidence/generated/m24-400-docs-snapshot.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/evidence/generated/m24-400-final-baseline.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/local_reviews/generated/20260520T182832Z-local-review-project-aresforge-model-ollama-default.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/local_reviews/generated/20260520T182832Z-local-review-project-aresforge-model-ollama-default.md` | artifacts | generated_artifact | # Local Review Package | 0/0/0/0 |
| `artifacts/mutation_audit/github-mutation-audit-log.jsonl` | artifacts | generated_artifact | {"logged_at": "2026-05-23T16:55:40.432560Z", "record": {"command": "plan-github-mutation", "mutation_intent": "issue_com | 0/0/0/0 |
| `artifacts/prompts/README.md` | artifacts | generated_artifact | # Prompt Artifacts | 0/0/0/0 |
| `artifacts/prompts/generated/20260520T000257Z-issue-81-prompt-package.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/prompts/generated/20260520T000257Z-issue-81-prompt-package.md` | artifacts | generated_artifact | # Issue 81 prompt package | 0/0/0/0 |
| `artifacts/prompts/generated/m18_issue_bodies_tmp/child1.md` | artifacts | generated_artifact | Summary | 0/0/0/0 |
| `artifacts/prompts/generated/m18_issue_bodies_tmp/child2.md` | artifacts | generated_artifact | Summary | 0/0/0/0 |
| `artifacts/prompts/generated/m18_issue_bodies_tmp/child3.md` | artifacts | generated_artifact | Summary | 0/0/0/0 |
| `artifacts/prompts/generated/m18_issue_bodies_tmp/child4.md` | artifacts | generated_artifact | Summary | 0/0/0/0 |
| `artifacts/prompts/generated/m18_issue_bodies_tmp/child5.md` | artifacts | generated_artifact | Summary | 0/0/0/0 |
| `artifacts/prompts/generated/m18_issue_bodies_tmp/child6.md` | artifacts | generated_artifact | Summary | 0/0/0/0 |
| `artifacts/prompts/generated/m18_issue_bodies_tmp/child7.md` | artifacts | generated_artifact | Summary | 0/0/0/0 |
| `artifacts/prompts/generated/m18_issue_bodies_tmp/create_m18_issues.ps1` | artifacts | generated_artifact | $ErrorActionPreference = "Stop" | 0/0/0/0 |
| `artifacts/prompts/generated/m18_issue_bodies_tmp/parent.md` | artifacts | generated_artifact | Summary | 0/0/0/0 |
| `artifacts/prompts/generated/m18_issue_bodies_tmp/parent_children_comment.md` | artifacts | generated_artifact | M18 child issues created: | 0/0/0/0 |
| `artifacts/ready_issue_batches/generated/20260520T182152Z-ready-issue-batch.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/ready_issue_batches/generated/20260520T182152Z-ready-issue-batch.md` | artifacts | generated_artifact | # Ready Issue Batch Plan | 0/0/0/0 |
| `artifacts/ready_issue_batches/generated/20260522T161845Z-ready-issue-batch.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/ready_issue_batches/generated/20260522T161845Z-ready-issue-batch.md` | artifacts | generated_artifact | # Ready Issue Batch Plan | 0/0/0/0 |
| `artifacts/ready_issue_batches/generated/20260522T163054Z-ready-issue-batch.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/ready_issue_batches/generated/20260522T163054Z-ready-issue-batch.md` | artifacts | generated_artifact | # Ready Issue Batch Plan | 0/0/0/0 |
| `artifacts/ready_issue_batches/generated/20260522T164234Z-ready-issue-batch.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/ready_issue_batches/generated/20260522T164234Z-ready-issue-batch.md` | artifacts | generated_artifact | # Ready Issue Batch Plan | 0/0/0/0 |
| `artifacts/ready_issue_batches/generated/20260522T165419Z-ready-issue-batch.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `artifacts/ready_issue_batches/generated/20260522T165419Z-ready-issue-batch.md` | artifacts | generated_artifact | # Ready Issue Batch Plan | 0/0/0/0 |
| `artifacts/samples/m6-agent-queue-input.json` | artifacts | generated_artifact | { | 0/0/0/0 |
| `config/README.md` | configuration | unknown | # Local Configuration | 0/0/0/0 |
| `config/managed_repositories.json` | configuration | unknown | { | 0/0/0/0 |
| `docker-compose.yml` | configuration | unknown | services: | 0/0/0/0 |
| `docs/agents/AGENT_SKILLS_MODEL.md` | docs | docs_only | Project documentation and design narrative. | 0/0/0/1 |
| `docs/agents/CLOSEOUT_EVIDENCE_PACKAGE_TEMPLATE.md` | docs | stale_or_aspirational | Project documentation and design narrative. | 0/0/1/1 |
| `docs/agents/DOCUMENTATION_AGENTS.md` | docs | docs_only | Project documentation and design narrative. | 0/0/0/1 |
| `docs/agents/DOCUMENTATION_FRESHNESS_CHECKS.md` | docs | docs_only | Project documentation and design narrative. | 0/0/0/1 |
| `docs/agents/DOCUMENTATION_SYNC_EVIDENCE_PACKAGES.md` | docs | docs_only | Project documentation and design narrative. | 0/0/0/1 |
| `docs/agents/DOCUMENTATION_SYNC_HANDOFF_TEMPLATE.md` | docs | docs_only | Project documentation and design narrative. | 0/0/0/1 |
| `docs/agents/PR_EVIDENCE_PACKAGE_TEMPLATE.md` | docs | docs_only | Project documentation and design narrative. | 0/0/1/1 |
| `docs/architecture/AGENT_QUEUE_ORCHESTRATION_CONTRACT.md` | docs | docs_only | Project documentation and design narrative. | 0/0/0/1 |
| `docs/architecture/AGENT_REGISTRY_SCHEMA.md` | docs | stale_or_aspirational | Project documentation and design narrative. | 0/0/0/1 |
| `docs/architecture/AUTOMATIC_CANONICAL_EVIDENCE_EMISSION_CONTRACT.md` | docs | docs_only | Project documentation and design narrative. | 0/0/1/1 |
| `docs/architecture/CANONICAL_EVIDENCE_MARKER_CONTRACT.md` | docs | docs_only | Project documentation and design narrative. | 0/0/1/1 |
| `docs/architecture/CLOSEOUT_CHILD_LINK_DISCOVERY_CONTRACT.md` | docs | docs_only | Project documentation and design narrative. | 0/0/0/0 |
| `docs/architecture/CLOSEOUT_EVIDENCE_RECOGNITION_CONTRACT.md` | docs | docs_only | Project documentation and design narrative. | 0/0/0/0 |
| `docs/architecture/CODEX_BATCH_EXECUTION_WORKFLOW.md` | docs | docs_only | Project documentation and design narrative. | 0/0/0/1 |
| `docs/architecture/CONTROLLED_AUTONOMOUS_GITHUB_EXECUTION_CONTRACT.md` | docs | stale_or_aspirational | Project documentation and design narrative. | 0/0/0/0 |
| `docs/architecture/EVIDENCE_BUNDLE_AUTOMATION_CONTRACT.md` | docs | docs_only | Project documentation and design narrative. | 0/0/1/1 |
| `docs/architecture/ISSUE_LIFECYCLE_AGENT_PIPELINE.md` | docs | docs_only | Project documentation and design narrative. | 0/0/0/1 |
| `docs/architecture/LOCAL_OPERATOR_WORKFLOW.md` | docs | stale_or_aspirational | Project documentation and design narrative. | 0/0/0/1 |
| `docs/architecture/LOCAL_STATE_STORE.md` | docs | stale_or_aspirational | Project documentation and design narrative. | 0/0/0/1 |
| `docs/architecture/M21_SELF_MANAGED_EXECUTION_CONTRACT.md` | docs | docs_only | Project documentation and design narrative. | 0/0/0/1 |
| `docs/architecture/MANAGED_REPOSITORY_BOOTSTRAP_CONTRACT.md` | docs | docs_only | Project documentation and design narrative. | 0/0/0/0 |
| `docs/architecture/MANAGED_REPOSITORY_REGISTRY.md` | docs | docs_only | Project documentation and design narrative. | 0/0/0/1 |
| `docs/architecture/MILESTONE_CLOSEOUT_PREFLIGHT_CONTRACT.md` | docs | docs_only | Project documentation and design narrative. | 0/0/1/1 |
| `docs/architecture/MILESTONE_EXECUTION_PLAN_CONTRACT.md` | docs | docs_only | Project documentation and design narrative. | 0/0/0/0 |
| `docs/architecture/MODEL_REGISTRY_SCHEMA.md` | docs | stale_or_aspirational | Project documentation and design narrative. | 0/0/1/1 |
| `docs/architecture/MODEL_ROUTING_STRATEGY.md` | docs | stale_or_aspirational | Project documentation and design narrative. | 0/0/0/0 |
| `docs/architecture/OPERATOR_APPROVED_GITHUB_MUTATION_ORCHESTRATION_CONTRACT.md` | docs | docs_only | Project documentation and design narrative. | 0/0/0/0 |
| `docs/architecture/PERSISTED_LOCAL_PLANNING_STATE.md` | docs | docs_only | Project documentation and design narrative. | 0/0/0/0 |
| `docs/architecture/PLANNING_STATE_CLOSEOUT_COMPARISON_CONTRACT.md` | docs | docs_only | Project documentation and design narrative. | 0/0/0/0 |
| `docs/architecture/PROJECT_FACTORY_WORKFLOW.md` | docs | docs_only | Project documentation and design narrative. | 0/0/1/1 |
| `docs/architecture/PROJECT_REGISTRY_SCHEMA.md` | docs | stale_or_aspirational | Project documentation and design narrative. | 0/0/0/1 |
| `docs/architecture/QUEUE_REGISTRY_SCHEMA.md` | docs | stale_or_aspirational | Project documentation and design narrative. | 0/0/1/1 |
| `docs/architecture/REGISTRY_AND_QUEUE_ARCHITECTURE.md` | docs | stale_or_aspirational | Project documentation and design narrative. | 0/0/0/1 |
| `docs/architecture/REPOSITORY_GOVERNANCE_CONTRACT.md` | docs | docs_only | Project documentation and design narrative. | 0/0/1/0 |
| `docs/architecture/RUNNABLE_SKELETON.md` | docs | docs_only | Project documentation and design narrative. | 0/0/1/1 |
| `docs/architecture/SELF_MANAGED_MILESTONE_PLANNING_CONTRACT.md` | docs | stale_or_aspirational | Project documentation and design narrative. | 0/0/1/0 |
| `docs/architecture/SEQUENTIAL_MILESTONE_EXECUTION_CONTRACT.md` | docs | docs_only | Project documentation and design narrative. | 0/0/0/0 |
| `docs/architecture/SEQUENTIAL_RUN_STATE_SCHEMA.md` | docs | docs_only | Project documentation and design narrative. | 0/0/0/0 |
| `docs/architecture/SPRINT_ISSUE_CREATION_PLANNING_CONTRACT.md` | docs | docs_only | Project documentation and design narrative. | 0/0/0/0 |
| `docs/architecture/STRUCTURED_SPRINT_ISSUE_DEFINITION_CONTRACT.md` | docs | docs_only | Project documentation and design narrative. | 0/0/0/1 |
| `docs/architecture/SYSTEM_OVERVIEW.md` | docs | stale_or_aspirational | Project documentation and design narrative. | 0/0/0/1 |
| `docs/context/AGENT_CONTEXT.md` | docs | docs_only | Project documentation and design narrative. | 0/0/1/1 |
| `docs/context/BUILD_STATE.md` | docs | docs_only | Project documentation and design narrative. | 0/0/1/1 |
| `docs/context/PROJECT_CONTEXT.md` | docs | docs_only | Project documentation and design narrative. | 0/0/0/1 |
| `docs/governance/PR_VALIDATION_MODEL.md` | docs | docs_only | Project documentation and design narrative. | 0/0/0/1 |
| `docs/governance/SELF_MANAGEMENT_MODEL.md` | docs | stale_or_aspirational | Project documentation and design narrative. | 0/0/0/1 |
| `docs/history/M0_M2_COMPLETED_WORK_SUMMARY.md` | docs | stale_or_aspirational | Project documentation and design narrative. | 0/0/0/0 |
| `docs/learning/ERROR_PATTERNS.md` | docs | docs_only | Project documentation and design narrative. | 0/0/0/1 |
| `docs/operator/BATCH_READY_ISSUE_OPERATIONS.md` | docs | docs_only | Project documentation and design narrative. | 0/0/0/0 |
| `docs/operator/HARDENED_SPRINT_ISSUE_CREATION_TEMPLATE.md` | docs | docs_only | Project documentation and design narrative. | 0/0/0/1 |
| `docs/operator/LOCAL_OPERATOR_USAGE.md` | docs | stale_or_aspirational | Project documentation and design narrative. | 0/0/1/1 |
| `docs/planning/FUTURE_FEATURE_IDEAS.md` | docs | docs_only | Project documentation and design narrative. | 0/0/0/0 |
| `docs/prompts/CODEX_PROMPT_PACKAGE_TEMPLATE.md` | docs | docs_only | Project documentation and design narrative. | 0/0/0/1 |
| `docs/prompts/CODEX_PROMPT_STANDARD.md` | docs | docs_only | Project documentation and design narrative. | 0/0/0/1 |
| `docs/roadmap/ROADMAP.md` | docs | docs_only | Project documentation and design narrative. | 0/0/1/1 |
| `docs/validation/GITHUB_CAPABILITY_VALIDATION.md` | docs | stale_or_aspirational | Project documentation and design narrative. | 0/0/0/1 |
| `docs/validation/OLLAMA_GITHUB_OPERATION_REVIEW.md` | docs | stale_or_aspirational | Project documentation and design narrative. | 0/0/0/0 |
| `migrations/0001_initial_schema.sql` | database | foundation | CREATE TABLE IF NOT EXISTS projects ( | 0/0/0/0 |
| `migrations/0002_m15_autonomous_run_queue.sql` | database | foundation | CREATE TABLE IF NOT EXISTS autonomous_runs ( | 0/0/0/0 |
| `migrations/0003_m16_autonomous_run_pr_linkage.sql` | database | foundation | ALTER TABLE autonomous_runs | 0/0/0/0 |
| `pyproject.toml` | configuration | unknown | [build-system] | 0/0/0/0 |
| `scripts/Invoke-AresForgePrLifecycle.ps1` | scripts | unknown | [CmdletBinding()] | 0/0/0/0 |
| `src/aresforge.egg-info/PKG-INFO` | unknown | candidate_for_review | Metadata-Version: 2.4 | 0/0/0/0 |
| `src/aresforge.egg-info/SOURCES.txt` | unknown | candidate_for_review | README.md | 0/0/0/0 |
| `src/aresforge.egg-info/dependency_links.txt` | unknown | candidate_for_review | Purpose inference unavailable. | 0/0/0/0 |
| `src/aresforge.egg-info/entry_points.txt` | unknown | candidate_for_review | [console_scripts] | 0/0/0/0 |
| `src/aresforge.egg-info/requires.txt` | unknown | candidate_for_review | psycopg[binary]<4.0,>=3.2 | 0/0/0/0 |
| `src/aresforge.egg-info/top_level.txt` | unknown | candidate_for_review | aresforge | 0/0/0/0 |
| `src/aresforge/__init__.py` | core_runtime | foundation | __all__ = ["__version__"] | 0/0/0/0 |
| `src/aresforge/__main__.py` | core_runtime | foundation | from aresforge.cli import main | 0/0/0/0 |
| `src/aresforge/artifacts/__init__.py` | core_runtime | foundation | """Artifact helpers for AresForge.""" | 0/0/0/0 |
| `src/aresforge/artifacts/store.py` | core_runtime | foundation | from __future__ import annotations | 0/0/0/0 |
| `src/aresforge/cli.py` | cli | plan_only | CLI command registration and dispatch entrypoint. | 0/0/1/0 |
| `src/aresforge/config.py` | config | foundation | from __future__ import annotations | 0/0/0/1 |
| `src/aresforge/db/__init__.py` | database | foundation | Database connectivity, migrations, and repositories. | 0/0/0/0 |
| `src/aresforge/db/connection.py` | database | foundation | Database connectivity, migrations, and repositories. | 0/0/0/0 |
| `src/aresforge/db/migrations.py` | database | foundation | Database connectivity, migrations, and repositories. | 0/0/0/0 |
| `src/aresforge/db/repository.py` | database | foundation | Database connectivity, migrations, and repositories. | 0/0/0/0 |
| `src/aresforge/hub/__init__.py` | hub_backend | foundation | Hub backend/frontend serving and route handling. | 0/0/0/0 |
| `src/aresforge/hub/api.py` | hub_backend | plan_only | Hub backend/frontend serving and route handling. | 0/0/1/1 |
| `src/aresforge/hub/server.py` | hub_backend | foundation | Hub backend/frontend serving and route handling. | 0/0/0/1 |
| `src/aresforge/hub/static/app.js` | hub_frontend | plan_only | Hub backend/frontend serving and route handling. | 0/0/0/1 |
| `src/aresforge/hub/static/index.html` | hub_frontend | plan_only | Hub backend/frontend serving and route handling. | 0/0/0/1 |
| `src/aresforge/hub/static/styles.css` | hub_frontend | unknown | Hub backend/frontend serving and route handling. | 0/0/0/1 |
| `src/aresforge/integrations/__init__.py` | llm_integration | active | """External and local integration adapters for AresForge.""" | 0/0/0/0 |
| `src/aresforge/integrations/ollama.py` | llm_integration | active | from __future__ import annotations | 0/0/0/0 |
| `src/aresforge/operator/__init__.py` | orchestration | active | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/agent_queue_planning.py` | agents | plan_only | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/artifact_discovery.py` | orchestration | active | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/automatic_canonical_evidence_emission_contract.py` | orchestration | plan_only | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/automation_readiness_report.py` | orchestration | plan_only | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/autonomous_cycle.py` | orchestration | active | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/batch_closeout_planner.py` | orchestration | plan_only | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/batch_readiness_report.py` | orchestration | plan_only | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/canonical_evidence_marker_contract.py` | orchestration | plan_only | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/canonical_evidence_markers.py` | orchestration | active | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/child_closeout_evidence_bundle.py` | orchestration | plan_only | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/child_closeout_script_generator.py` | orchestration | plan_only | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/child_evidence_marker_preflight.py` | orchestration | plan_only | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/child_evidence_marker_template.py` | orchestration | plan_only | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/child_execution_gates.py` | orchestration | active | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/closeout_planning_drift.py` | orchestration | active | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/closeout_readiness_by_construction.py` | orchestration | active | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/closeout_repair_guidance.py` | orchestration | plan_only | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/evidence_bundle.py` | orchestration | active | Local operator workflow/inspection logic. | 0/0/1/0 |
| `src/aresforge/operator/evidence_bundle_automation_contract.py` | orchestration | plan_only | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/evidence_bundle_simulation.py` | orchestration | active | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/evidence_comment_template_generator.py` | orchestration | plan_only | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/evidence_completeness_checker.py` | orchestration | active | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/evidence_mapping_parser.py` | orchestration | active | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/evidence_templates.py` | orchestration | active | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/github_issue_close_executor.py` | github_integration | active | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/github_issue_comment_executor.py` | github_integration | active | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/github_mutation_audit_log.py` | github_integration | plan_only | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/github_mutation_planner.py` | github_integration | active | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/inspection_reports.py` | orchestration | active | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/lineage_mapping_signals.py` | orchestration | active | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/local_active_project.py` | active_project | active | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/local_agent_orchestration.py` | agents | plan_only | Local operator workflow/inspection logic. | 0/0/0/1 |
| `src/aresforge/operator/local_agent_profiles.py` | agents | plan_only | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/local_bootstrap_wizard.py` | orchestration | plan_only | Local operator workflow/inspection logic. | 0/0/0/1 |
| `src/aresforge/operator/local_doc_reconciliation.py` | orchestration | plan_only | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/local_github_sync_planner.py` | orchestration | plan_only | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/local_handoff_package.py` | orchestration | active | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/local_llm_escalation.py` | orchestration | plan_only | Local operator workflow/inspection logic. | 0/0/0/1 |
| `src/aresforge/operator/local_milestone_lifecycle.py` | orchestration | active | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/local_project_dashboard.py` | orchestration | plan_only | Local operator workflow/inspection logic. | 0/0/0/1 |
| `src/aresforge/operator/local_project_factory.py` | project_factory | plan_only | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/local_project_queue.py` | queue | active | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/local_project_state.py` | orchestration | active | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/local_review.py` | orchestration | active | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/managed_project_registry_local.py` | project_registry | active | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/managed_repo_governance_demo.py` | orchestration | plan_only | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/managed_repo_readiness_report.py` | orchestration | plan_only | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/managed_repo_registry.py` | orchestration | plan_only | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/milestone_closeout_preflight.py` | orchestration | plan_only | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/milestone_closeout_preflight_contract.py` | orchestration | plan_only | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/milestone_dashboard.py` | orchestration | plan_only | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/milestone_execution_queue_planner.py` | orchestration | active | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/milestone_reconciliation_planner.py` | orchestration | active | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/milestone_state_inspector.py` | orchestration | active | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/offline_state_template.py` | orchestration | active | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/parent_child_linkage_preflight.py` | orchestration | plan_only | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/parent_closeout_evidence_bundle.py` | orchestration | plan_only | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/parent_closeout_marker_template.py` | orchestration | plan_only | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/parent_closeout_readiness.py` | orchestration | plan_only | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/planning_state.py` | orchestration | active | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/pr_body_update_helper.py` | orchestration | active | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/pr_evidence_bundle.py` | orchestration | plan_only | Local operator workflow/inspection logic. | 0/0/1/0 |
| `src/aresforge/operator/pr_evidence_extraction.py` | orchestration | active | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/pr_evidence_marker_template.py` | orchestration | plan_only | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/pr_mapping_preflight.py` | orchestration | plan_only | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/preflight_snapshot.py` | orchestration | plan_only | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/project_state_summary.py` | orchestration | plan_only | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/qa_closeout_pr.py` | orchestration | active | Local operator workflow/inspection logic. | 0/0/1/0 |
| `src/aresforge/operator/qa_pr_validation.py` | orchestration | plan_only | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/ready_issue_batch.py` | orchestration | plan_only | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/ready_issue_intake.py` | orchestration | plan_only | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/ready_issue_pipeline.py` | orchestration | plan_only | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/ready_issue_planning.py` | orchestration | active | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/registry_inspection.py` | orchestration | active | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/repo_assessment.py` | orchestration | plan_only | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/repo_bootstrap_contract.py` | orchestration | plan_only | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/repo_bootstrap_plan.py` | orchestration | plan_only | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/repo_governance.py` | orchestration | plan_only | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/self_managed_issue_script_generator.py` | orchestration | plan_only | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/self_managed_milestone_execution_contract.py` | orchestration | plan_only | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/self_managed_milestone_handoff.py` | orchestration | active | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/self_managed_milestone_planner.py` | orchestration | plan_only | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/self_managed_milestone_simulation.py` | orchestration | plan_only | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/sequential_child_closeout_flow.py` | orchestration | active | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/sequential_closeout_execution_package.py` | orchestration | plan_only | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/sequential_handoff_package.py` | orchestration | plan_only | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/sequential_recovery_planner.py` | orchestration | active | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/sequential_run_state.py` | orchestration | active | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/service.py` | orchestration | active | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/sprint_issue_planner.py` | orchestration | plan_only | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/sprint_issue_script_generator.py` | orchestration | plan_only | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/validate_pr_end_to_end.py` | orchestration | plan_only | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/operator/validation_summary.py` | orchestration | active | Local operator workflow/inspection logic. | 0/0/0/0 |
| `src/aresforge/routing/__init__.py` | hub_backend | foundation | """Routing primitives for AresForge.""" | 0/0/0/0 |
| `src/aresforge/routing/routes.py` | hub_backend | foundation | from __future__ import annotations | 0/0/0/0 |
| `src/aresforge/validation/__init__.py` | validation_evidence | unknown | from .registry import ( | 0/0/0/0 |
| `src/aresforge/validation/registry.py` | validation_evidence | unknown | from __future__ import annotations | 0/0/0/0 |
| `tests/fixtures/m12-manual-closeout-comments.json` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/fixtures/m12-sprint-definition.json` | tests | test_only | Automated verification coverage. | 0/0/1/0 |
| `tests/fixtures/m12-verification-failure-observed.json` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/fixtures/m25-readiness-by-construction-regression.json` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/fixtures/m8-sprint-definition.json` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/fixtures/offline_state/parent_closeout_ready.json` | tests | test_only | Automated verification coverage. | 0/0/1/1 |
| `tests/test_agent_queue_planning.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_agent_registry.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_artifact_discovery.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_artifacts.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_automatic_canonical_evidence_emission_contract.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_autonomous_cycle.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_batch_closeout_planner.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_batch_readiness_report.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_canonical_evidence_marker_contract.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_canonical_evidence_markers.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_child_closeout_evidence_bundle.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_child_closeout_script_generator.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_child_evidence_marker_preflight.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_child_evidence_marker_template.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_child_execution_gates.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_cli.py` | tests | test_only | Automated verification coverage. | 0/0/1/0 |
| `tests/test_cli_doc_reconciliation.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_cli_github_sync_planner.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_cli_handoff_package.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_cli_hub_server.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_cli_local_agent_orchestration.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_cli_local_agent_profiles.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_cli_local_bootstrap_wizard.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_cli_local_llm_escalation.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_cli_local_milestone_lifecycle.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_cli_local_project_queue.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_cli_m6_commands.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_cli_managed_project_registry.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_cli_project_state_ledger.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_closeout_planning_drift.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_closeout_readiness_by_construction.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_closeout_repair_guidance.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_config_and_migrations.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_evidence_bundle.py` | tests | test_only | Automated verification coverage. | 0/0/1/0 |
| `tests/test_evidence_bundle_automation_contract.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_evidence_bundle_simulation.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_evidence_comment_template_generator.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_evidence_completeness_checker.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_evidence_mapping_parser.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_github_issue_close_executor.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_github_issue_comment_executor.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_github_mutation_audit_log.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_github_mutation_planner.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_hub_active_project_api.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_hub_project_factory_api.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_hub_ui_foundation.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_lineage_mapping_signals.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_local_active_project.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_local_agent_orchestration.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_local_agent_profiles.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_local_bootstrap_wizard.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_local_doc_reconciliation.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_local_github_sync_planner.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_local_handoff_package.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_local_llm_escalation.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_local_milestone_lifecycle.py` | tests | test_only | Automated verification coverage. | 0/0/1/0 |
| `tests/test_local_project_dashboard.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_local_project_factory.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_local_project_queue.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_local_project_state.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_local_review.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_managed_project_registry.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_managed_repo_governance_demo.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_managed_repo_readiness_report.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_managed_repo_registry.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_milestone_closeout_preflight.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_milestone_closeout_preflight_contract.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_milestone_dashboard.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_milestone_execution_queue_planner.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_milestone_reconciliation_planner.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_milestone_state_inspector.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_offline_state_example_fixture.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_offline_state_template.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_parent_child_linkage_preflight.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_parent_closeout_evidence_bundle.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_parent_closeout_marker_template.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_parent_closeout_readiness.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_planning_state.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_pr_body_update_helper.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_pr_evidence_bundle.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_pr_evidence_extraction.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_pr_evidence_marker_template.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_pr_mapping_preflight.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_preflight_snapshot.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_project_factory_workflow_docs.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_project_state_summary.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_qa_closeout_pr.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_qa_review_pr.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_ready_issue_batch.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_ready_issue_intake.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_ready_issue_pipeline.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_ready_issue_planning.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_registry_inspection.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_registry_validation.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_repo_assessment.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_repo_bootstrap_contract.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_repo_bootstrap_plan.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_repo_governance.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_self_managed_issue_script_generator.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_self_managed_milestone_execution_contract.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_self_managed_milestone_handoff.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_self_managed_milestone_planner.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_self_managed_milestone_simulation.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_sequential_child_closeout_flow.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_sequential_closeout_execution_package.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_sequential_handoff_package.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_sequential_recovery_planner.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_sequential_run_state.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_sprint_issue_planner.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_sprint_issue_script_generator.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_validate_pr_end_to_end.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |
| `tests/test_validation_summary.py` | tests | test_only | Automated verification coverage. | 0/0/0/0 |

## Unknown and candidate for review
- `.agent/AGENT_REGISTRY.md` (candidate_for_review)
- `.agent/skills/build-state-update/SKILL.md` (candidate_for_review)
- `.agent/skills/documentation-sync/SKILL.md` (candidate_for_review)
- `.agent/skills/issue-planning/SKILL.md` (candidate_for_review)
- `.agent/skills/ollama-evidence-review/SKILL.md` (candidate_for_review)
- `.agent/skills/pr-validation/SKILL.md` (candidate_for_review)
- `.aresforge/state/project_state.json` (candidate_for_review)
- `.env.example` (candidate_for_review)
- `.gitignore` (candidate_for_review)
- `README.md` (candidate_for_review)
- `config/README.md` (unknown)
- `config/managed_repositories.json` (unknown)
- `docker-compose.yml` (unknown)
- `pyproject.toml` (unknown)
- `scripts/Invoke-AresForgePrLifecycle.ps1` (unknown)
- `src/aresforge.egg-info/PKG-INFO` (candidate_for_review)
- `src/aresforge.egg-info/SOURCES.txt` (candidate_for_review)
- `src/aresforge.egg-info/dependency_links.txt` (candidate_for_review)
- `src/aresforge.egg-info/entry_points.txt` (candidate_for_review)
- `src/aresforge.egg-info/requires.txt` (candidate_for_review)
- `src/aresforge.egg-info/top_level.txt` (candidate_for_review)
- `src/aresforge/hub/static/styles.css` (unknown)
- `src/aresforge/validation/__init__.py` (unknown)
- `src/aresforge/validation/registry.py` (unknown)
