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

The canonical source-of-truth for the local-first model-routing and LLM escalation strategy is `docs/architecture/MODEL_ROUTING_STRATEGY.md`.

The canonical source-of-truth for queue-record meaning, work-item state fields, transition rules, blocked handling, and corrective-loop routing is now `docs/architecture/QUEUE_REGISTRY_SCHEMA.md`.

The canonical source-of-truth for reusable label and milestone governance across managed repositories is `docs/architecture/REPOSITORY_GOVERNANCE_CONTRACT.md`.

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
- `list-artifacts`
- `list-review-packages`
- `inspect-artifact`
- `inspect-review-package`
- `run-local-review`
- `list-evidence-packages`
- `inspect-evidence-package`
- `list-ready-issues`
- `inspect-ready-issue`
- `plan-ready-issue`
- `run-ready-issue-pipeline`
- `run-ready-issue-batch`
- `automation-readiness-report`
- `project-state-summary`
- `inspect-repo-governance`
- `inspect-repo-bootstrap-contract`
- `inspect-managed-repos`
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

The `list-artifacts` command is a read-only local summary helper for generated review artifacts under the configured artifact root. It emits deterministic JSON sorted by relative artifact path, reports empty and missing artifact-root cases explicitly, and infers artifact category plus likely human-triggered source command where the generated path or filename makes that safe. It does not create missing directories, require PostgreSQL, call Ollama, mutate files, route work, or change GitHub state.

The `inspect-artifact` command is a read-only local inspection helper for one generated review artifact under the configured artifact root. It accepts one safe relative path from `list-artifacts`, rejects empty, traversal, absolute, and out-of-root paths, and emits deterministic JSON with bounded preview metadata for safe UTF-8 text artifacts. It does not create missing directories, require PostgreSQL, call Ollama, mutate files, route work, or change GitHub state.

The `list-review-packages` command is a read-only local summary helper for generated local review packages under `artifacts/local_reviews/generated/`. It emits deterministic JSON sorted by relative review path, reports empty and missing review-package-root cases explicitly, and keeps review packages visible as generated review aids rather than source of truth. It does not create missing directories, require PostgreSQL, call Ollama, mutate files, route work, or change GitHub state.

The `inspect-review-package` command is a read-only local inspection helper for one generated local review package under `artifacts/local_reviews/generated/`. It accepts one safe relative path from `list-review-packages`, rejects empty, traversal, absolute, and out-of-root paths, and emits deterministic JSON with bounded preview metadata for safe UTF-8 text artifacts plus parsed summary metadata only when the existing JSON package format makes that safe and deterministic. It does not create missing directories, require PostgreSQL, call Ollama, mutate files, route work, or change GitHub state.

The `run-local-review` command is a human-triggered local orchestration helper that runs a fixed sequence of existing local validation and inspection checks, records executed and skipped checks in deterministic JSON, and continues surfacing later check results even when an earlier check fails. Optional artifact and evidence-package inspection inputs remain explicit and bounded, and optional review package generation under `artifacts/local_reviews/generated/` is allowed only when the operator explicitly requests it.

The `list-evidence-packages` command is a read-only local summary helper for generated evidence packages under the configured evidence root. It emits deterministic JSON sorted by relative evidence path, reports empty and missing evidence-root cases explicitly, and keeps evidence packages visible as review artifacts rather than source of truth. It does not create missing directories, require PostgreSQL, call Ollama, mutate files, route work, or change GitHub state.

The `inspect-evidence-package` command is a read-only local inspection helper for one generated evidence package under the configured evidence root. It accepts one safe relative path from `list-evidence-packages`, rejects empty, traversal, absolute, and out-of-root paths, and emits deterministic JSON with bounded preview metadata for safe UTF-8 text artifacts. It does not create missing directories, require PostgreSQL, call Ollama, mutate files, route work, or change GitHub state.

The `list-ready-issues` command is a read-only GitHub intake helper for manually labeled ready issues. It queries the configured GitHub repository for open issues labeled `aresforge-ready`, excludes Issue #39, emits deterministic JSON sorted by issue number, and records explicit automation boundary confirmations. It does not create or modify issues, labels, pull requests, or any GitHub state.

The `inspect-ready-issue` command is a read-only GitHub intake helper for one manually labeled ready issue. It rejects Issue #39, requires the `aresforge-ready` label, emits deterministic JSON for the issue metadata and manual trigger confirmation, and does not create or modify issues, labels, pull requests, or any GitHub state.

The `plan-ready-issue` command is a decision-only GitHub intake helper for one ready issue. It inspects the target issue, confirms the `aresforge-ready` trigger label, excludes Issue #39, and emits deterministic JSON describing the recommended handling agent and model tier. It does not run implementation, create PRs, merge PRs, close issues, comment on issues, label issues, or mutate GitHub state.

The `run-ready-issue-pipeline` command is a reusable human-triggered orchestration helper for one ready issue. It composes existing `inspect-ready-issue`, `plan-ready-issue`, `qa-review-pr`, `qa-closeout-pr`, and `run-local-review` behavior into three explicit modes: `plan-only`, `review-pr`, and `closeout-when-eligible`. Default behavior is safe and non-mutating. Any GitHub mutation is permitted only through `qa-closeout-pr` behavior in explicit closeout execute mode after all required QA and label gates pass, including `aresforge-ready`, `aresforge-automerge`, and Issue #39 protection.

The `run-ready-issue-batch` command is a reusable human-triggered orchestration helper for all currently ready issues. In required `--plan-only` mode it reuses existing `list-ready-issues`, `inspect-ready-issue`, and `plan-ready-issue` logic for deterministic per-issue summaries, always excludes Issue #39, and writes local JSON plus Markdown batch artifacts under `artifacts/ready_issue_batches/generated/`. Optional local-only handoff package generation for Copilot or Codex selected issues is available through explicit `--write-selected-handoffs` mode.

The `automation-readiness-report` command is a human-triggered read-only reporting helper. It summarizes current automation command surfaces, ready issue count, protected issue handling, required labels, closeout gates, mutation boundaries, local-only behavior, known blocked conditions, and recommended human workflow. It does not mutate GitHub state and does not authorize queue or routing mutation.

The `project-state-summary` command is a human-triggered local-first read-only reporting helper. It summarizes local git branch and cleanliness, local and `origin/main` commit posture where available, open GitHub issues and PRs where available, source-of-truth document presence, latest generated artifacts from known artifact roots, and current milestone direction inferred from source-of-truth docs. It degrades gracefully with explicit warnings when `git`, `gh`, `origin/main`, or network access are unavailable. It does not mutate git state, files, GitHub state, labels, issues, PRs, milestones, or artifacts.

The `inspect-repo-governance` command is a human-triggered read-only governance helper for the configured managed repository slug. It evaluates reusable platform-required labels, platform-optional labels, automation-trigger labels, canonical platform milestone naming, open issue readiness signals, and open PR readiness signals. It reports warnings plus recommended next action and degrades gracefully when `gh` or network access is unavailable. It does not create or modify labels, milestones, issues, PRs, branches, settings, workflows, or artifacts.

The `inspect-repo-bootstrap-contract` command is a human-triggered read-only managed repository bootstrap helper. It summarizes reusable setup readiness expectations across required, recommended, optional, and deferred contract areas; reuses repository governance inspection where practical; and emits deterministic JSON with clear status signals such as satisfied, attention-needed, advisory, unavailable, and deferred. It degrades gracefully when `gh` or network access is unavailable and does not create or modify labels, milestones, issues, PRs, branches, settings, workflows, artifacts, or git state.

The `inspect-managed-repos` command is a human-triggered read-only managed repository registry helper. It always includes the configured AresForge repository as the first/default managed repository and can merge optional additional managed repository records from `config/managed_repositories.json` when present. It emits deterministic JSON for repository identity, local path posture, bootstrap and governance-derived status posture, documentation and artifact roots, and bounded automation capabilities. It degrades gracefully when local paths, `gh`, or network access are unavailable and does not mutate files, git state, labels, milestones, issues, PRs, branches, settings, workflows, or artifacts.

The `qa-review-pr` command is a validation-only GitHub PR inspection helper. It reads PR metadata, detects linked issues and changed files, checks for validation evidence, and emits deterministic JSON with pass/fail/blocked decisions. It does not create PRs, merge PRs, close issues, comment on PRs, label issues, or mutate GitHub state.

The `qa-closeout-pr` command is a human-triggered QA-gated closeout helper with dry-run as the default safety mode. In dry-run mode it performs no GitHub mutation and emits deterministic JSON describing pass/fail gate status. Execute mode is explicit (`--execute`) and allowed only when all closeout gates pass, including required manual labels (`aresforge-ready` and `aresforge-automerge`) on the linked issue, pass-level `qa-review-pr` decision, and Issue #39 protection checks. When fully eligible, execute mode may squash-merge the target PR, delete the remote branch through merge flow, comment on the linked issue, and close only that linked issue.

The `inspect-queue` and `inspect-work-item` commands are read-only registry-aware inspection helpers. They expand local queue and work-item records into richer JSON views, but they do not transition queues, mutate routing, authorize autonomous routing, or authorize GitHub-state-changing behavior.

The `list-models` command is a read-only local listing helper for seeded local model rows. It emits deterministic JSON, does not require Ollama to be running, and does not select a model, recommend a model, or route a task.

The `inspect-model` command is a read-only local inspection helper for one stored model row. It reads only from the local `models` table and existing seeded model registry metadata, expands stored JSON metadata into visible top-level fields such as approval posture, allowed task classes, governance-sensitive task posture, fallback rules, and source document references, and returns explicit `ok` / `model_not_found` JSON without selecting a model, recommending a model, routing work, or calling Ollama.

The `inspect-project` command is a read-only local inspection helper for one stored project row. It reads only from the local `projects` table, expands stored JSON metadata into visible top-level fields such as autonomy posture and issue references, and returns explicit `ok` / `project_not_found` JSON without bootstrapping state, creating work items, routing work, or calling Ollama.

The current implementation layer also includes read-only inspection report artifact wiring for `inspect-queue --write-artifact` and `inspect-work-item --write-artifact`, read-only artifact discovery through `list-artifacts`, read-only single-artifact inspection through `inspect-artifact`, read-only review package discovery through `list-review-packages`, read-only single review-package inspection through `inspect-review-package`, deterministic human-triggered `run-local-review` orchestration, read-only evidence package discovery through `list-evidence-packages`, and read-only single evidence-package inspection through `inspect-evidence-package`. The write-artifact options turn inspection payloads into human-reviewable Markdown and JSON artifacts under `artifacts/inspection_reports/generated/`, `run-local-review --write-review-package` can optionally write a bounded local review package under `artifacts/local_reviews/generated/`, `record-evidence-package --include-artifact-discovery` can optionally embed a deterministic local `list-artifacts` snapshot for auditability, and `record-evidence-package --include-latest-review-package` plus `prepare-codex-handoff --include-latest-review-package` can optionally embed deterministic summaries of the latest generated local review package. These remain local-only, human-triggered helper surfaces and do not change queue state, routing state, GitHub state, or protected Issue #39.

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
9. optionally run a bounded local review orchestration across existing inspection commands
10. optionally inspect or reuse the latest generated local review package
11. record evidence metadata
12. prepare a Codex handoff artifact
13. optionally test a local Ollama model call
14. optionally use the explicit PR lifecycle helper to reduce repetitive post-Codex review steps without hiding them

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
- unauthorized modification or closure of protected validation evidence

The runnable skeleton is local-first and human-triggered by design.
