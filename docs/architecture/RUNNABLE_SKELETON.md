# Runnable Skeleton

## Purpose

Issue #81 is the pivot from documentation-only planning into a first runnable local skeleton.

The goal is not a polished autonomous system. The goal is to make AresForge executable enough that a human operator can:

- validate local config
- stand up PostgreSQL locally
- apply migrations
- inspect state
- create and list work items
- generate prompt artifacts
- record evidence metadata
- test local Ollama connectivity
- prepare Codex handoff files

The canonical source-of-truth for model-record meaning and bounded local routing rules is now `docs/architecture/MODEL_REGISTRY_SCHEMA.md`.

The canonical source-of-truth for queue-record meaning, work-item state fields, transition rules, blocked handling, and corrective-loop routing is now `docs/architecture/QUEUE_REGISTRY_SCHEMA.md`.

## Implemented Structure

The runnable skeleton introduces these repo areas:

- `src/aresforge/`
- `src/aresforge/operator/`
- `src/aresforge/db/`
- `src/aresforge/integrations/`
- `src/aresforge/routing/`
- `src/aresforge/artifacts/`
- `migrations/`
- `config/`
- `artifacts/prompts/`
- `artifacts/evidence/`
- `artifacts/codex_handoffs/`
- `tests/`

## Operator Shape

The local operator is a Python CLI exposed as `python -m aresforge` or `aresforge` after installation.

Supported commands:

- `validate-config`
- `validate-registries`
- `migrate`
- `inspect-project-state`
- `inspect-registries`
- `inspect-project`
- `inspect-model`
- `inspect-queue`
- `inspect-work-item`
- `list-projects`
- `list-agents`
- `list-models`
- `list-queues`
- `create-work-item`
- `list-work-items`
- `generate-prompt-package`
- `record-evidence-package`
- `test-ollama`
- `prepare-codex-handoff`

These commands are human-triggered only and operate as local-only helper surfaces.

The `validate-registries` command is a read-only local validation helper for seeded agent and queue registry data. It emits structured findings without requiring queue transitions, autonomous routing, or GitHub-state-changing behavior.

The `inspect-registries` command is a read-only local summary helper for repo-owned registry and lifecycle source documents. It inspects the documented project, agent, model, and queue registry sources plus the documented work-item lifecycle schema view, reuses existing seed-validation findings where applicable, and emits deterministic JSON that makes found, missing, empty, malformed, read-error, and validation-problem states visible without mutating files, requiring PostgreSQL, or calling the network.

The `inspect-queue` and `inspect-work-item` commands are read-only registry-aware inspection helpers. They expand local queue and work-item records into richer JSON views, but they do not transition queues, mutate routing, authorize autonomous routing, or authorize GitHub-state-changing behavior.

The `list-models` command is a read-only local listing helper for seeded local model rows. It emits deterministic JSON, does not require Ollama to be running, and does not select a model, recommend a model, or route a task.

The `inspect-model` command is a read-only local inspection helper for one stored model row. It reads only from the local `models` table and existing seeded model registry metadata, expands stored JSON metadata into visible top-level fields such as approval posture, allowed task classes, governance-sensitive task posture, fallback rules, and source document references, and returns explicit `ok` / `model_not_found` JSON without selecting a model, recommending a model, routing work, or calling Ollama.

The `inspect-project` command is a read-only local inspection helper for one stored project row. It reads only from the local `projects` table, expands stored JSON metadata into visible top-level fields such as autonomy posture and issue references, and returns explicit `ok` / `project_not_found` JSON without bootstrapping state, creating work items, routing work, or calling Ollama.

The current implementation layer also includes read-only inspection report artifact wiring for `inspect-queue --write-artifact` and `inspect-work-item --write-artifact`. Those options turn inspection payloads into human-reviewable Markdown and JSON artifacts under `artifacts/inspection_reports/generated/` while preserving the normal JSON command output. They remain local-only, human-triggered reporting helpers and do not change queue state, routing state, GitHub state, or protected Issue #39.

The current M2 implementation layer also includes a human-triggered PowerShell helper at `scripts/Invoke-AresForgePrLifecycle.ps1`. That helper is intentionally phase-based and visible. It supports explicit working-branch validation, explicit staging and commit and push flow, explicit PR creation, explicit PR verification, explicit merge execution only when directly selected, explicit post-merge verification, and read-only source-of-truth scanning.

## Vertical Slice Achieved

The current vertical slice is:

1. configure local environment
2. start PostgreSQL locally
3. apply repo-stored migrations
4. bootstrap minimal reference data
5. inspect documented registry and lifecycle sources plus seeded project, agent, queue, and model records, including a single model view
6. inspect a specific queue or work item through registry-aware read-only views
7. create a work item and assign a queue
8. generate a prompt package
9. record evidence metadata
10. prepare a Codex handoff artifact
11. optionally test a local Ollama model call
12. optionally use the explicit PR lifecycle helper to reduce repetitive post-Codex review steps without hiding them

That is enough to prove the local execution path without over-designing agents, routing intelligence, or background automation.

The current runnable seed data now includes the full canonical initial M2 queue ID set. The local database still remains conservative in field richness, with broader queue and work-item semantics continuing to live in the documentation-defined queue registry and JSON metadata.

## Ollama Boundary

The Ollama adapter is intentionally small:

- one HTTP generate call
- one dry-run/test command
- graceful failure when Ollama is not running

It is a connectivity and interface check, not a full orchestration runtime.
It does not implement autonomous routing, policy-driven model selection, hosted fallback, or governance-sensitive task handling.

## Codex Boundary

Codex integration is intentionally output-file generation only.

The CLI can prepare a reviewable handoff artifact, but it does not invoke Codex autonomously and it does not grant GitHub or repository mutation authority.

The PR lifecycle helper follows the same boundary. It can run explicit human-triggered local validation plus visible `git` and `gh` commands, but it does not select issues autonomously, invoke Codex, mutate routing, approve changes, close issues, or create hidden background behavior.

## Automation Boundary

Issue #81 does not authorize:

- autonomous PR merge
- autonomous issue closure
- autonomous approval
- autonomous GitHub issue mutation
- autonomous branch or repo setting changes
- branch protection or ruleset changes
- secret changes
- release or tag changes
- GitHub Project changes
- any modification or closure of protected Issue #39

The runnable skeleton is local-first and human-triggered by design.
