# Local Operator Usage

## Purpose

This guide explains how to run the current local AresForge operator surfaces introduced during M2.

## Setup

1. Copy `.env.example` to `.env` and adjust values if needed.
2. Create a virtual environment.
3. Install the package and dev dependencies.
4. Start PostgreSQL locally if you want database-backed commands.

Example:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .[dev]
docker compose up -d postgres
```

## Validate Config

```powershell
python -m aresforge validate-config
```

This checks local config shape and ensures artifact directories exist.

Validate registry seed data without requiring PostgreSQL:

```powershell
python -m aresforge validate-registries
```

This command is read-only and local-only. It emits JSON with `ok` and structured `findings`, returns exit code `0` when validation passes, and returns exit code `1` when any finding has `error` severity. It does not transition queues, mutate routing, or perform GitHub-state-changing behavior.

Summarize documented local registry and lifecycle sources without requiring PostgreSQL:

```powershell
python -m aresforge inspect-registries
```

This command is read-only and local-only. It inspects the repo-owned project, agent, model, and queue registry source documents plus the documented work-item lifecycle schema view, reuses existing queue and agent seed validation findings where applicable, and emits deterministic JSON that distinguishes `ok`, `missing`, `empty`, `malformed`, `read_error`, and `validation_problem` states per registry surface. It does not mutate files, call the network, require PostgreSQL, transition queues, mutate routing, or change GitHub state.

Summarize generated local review artifacts without requiring PostgreSQL:

```powershell
python -m aresforge list-artifacts
```

This command is read-only and local-only. It reads only from the configured artifact root when that directory already exists and emits deterministic JSON sorted by relative artifact path. It does not create missing artifact directories, mutate files, call the network, require PostgreSQL, call Ollama, transition queues, mutate routing, or change GitHub state.

## Database Commands

See pending migrations:

```powershell
python -m aresforge migrate --plan
```

Apply migrations and bootstrap the local reference rows:

```powershell
python -m aresforge migrate
```

Inspect local state:

```powershell
python -m aresforge inspect-project-state
```

Inspect one local project record with expanded metadata:

```powershell
python -m aresforge inspect-project --project-id project-aresforge
```

List projects and queues:

```powershell
python -m aresforge list-projects
python -m aresforge list-agents
python -m aresforge list-models
python -m aresforge list-queues
```

Inspect one model with expanded registry-aware metadata:

```powershell
python -m aresforge inspect-model --model-id model-ollama-default
```

Inspect one queue with registry-aware metadata expansion:

```powershell
python -m aresforge inspect-queue --queue-id queue-implementation
```

Write local inspection report artifacts while preserving JSON output:

```powershell
python -m aresforge inspect-queue --queue-id queue-implementation --write-artifact
```

`list-agents` is read-only. It shows the seeded M2 agent-role records that align the local skeleton with the canonical schema in `docs/architecture/AGENT_REGISTRY_SCHEMA.md`.

`list-models` is read-only and local-only. It emits deterministic JSON for seeded local `models` rows without calling Ollama, selecting a model, recommending a model, routing a task, or mutating local or GitHub state. It exposes stored row fields plus any existing model metadata already present in the local state store.

`inspect-model` is read-only and local-only. It reads only from the local `models` table and existing seeded model registry metadata, emits deterministic JSON shaped as `{"ok": true, "model": {...}}` when found, and expands visible metadata fields such as `display_name`, `provider`, `runtime`, `execution_location`, `hosting_posture`, `approval_posture`, `allowed_task_classes`, `restricted_task_classes`, `governance_sensitive_task_posture`, `fallback_rules`, and `source_document`. If the requested model row is missing, it emits `{"ok": false, "error": "model_not_found", "model_id": "<requested id>"}` and returns exit code `1`.

`inspect-project` is read-only and local-only. It reads only from the local `projects` table and emits JSON shaped as `{"ok": true, "project": {...}}` when found. It expands stored project metadata into visible top-level fields such as `autonomy_level`, `protected_issue`, `active_issue`, and `completed_issue`. If the requested project row is missing, it emits `{"ok": false, "error": "project_not_found", "project_id": "<requested id>"}` and returns exit code `1`.

`inspect-registries` is read-only and local-only. It reads only repo-owned source documents and existing seeded registry-validation surfaces. It emits JSON shaped as `{"ok": <bool>, "inspection_mode": "local_repo_only", "summary": {...}, "registries": [...]}` and reports project, agent, model, queue, and work-item lifecycle inspection status in deterministic order. Missing files, empty files, malformed documents, and validation findings are surfaced explicitly instead of causing hidden mutation or fallback behavior.

`list-artifacts` is read-only and local-only. It reads only from the configured artifact root when that directory already exists and emits JSON shaped as `{"ok": true, "inspection_mode": "local_artifact_root_only", "artifact_root": "...", "artifact_root_exists": <bool>, "artifact_count": <int>, "artifacts": [...]}`. Results are sorted deterministically by relative path. Known generated paths are labeled with inferred artifact type and a safe command-source hint when available. Missing or empty artifact roots are reported explicitly instead of causing directory creation or fallback behavior.

`inspect-queue` is read-only and local-only. It emits JSON that expands queue metadata into registry-aware fields such as lifecycle-stage mapping, accepted work-item types, allowed next queues, human approval requirements, local operator visibility expectations, and the source document path. With `--write-artifact`, it still emits JSON and additionally includes `inspection_payload`, `markdown_path`, and `json_path` for a local report written under `artifacts/inspection_reports/generated/`.

The current CLI still does not expose queue-transition commands or autonomous routing behavior. Canonical queue meaning, full M2 queue coverage, transition rules, blocked handling, corrective loops, and work-item state fields are defined by `docs/architecture/QUEUE_REGISTRY_SCHEMA.md`.

## Work Item Commands

Create a work item:

```powershell
python -m aresforge create-work-item `
  --title "Build local operator skeleton" `
  --queue-id queue-implementation `
  --description "Runnable foundation for issue 81"
```

List work items:

```powershell
python -m aresforge list-work-items
```

Inspect one work item with registry-aware queue, agent, and model context:

```powershell
python -m aresforge inspect-work-item --work-item-id work-123
```

Write local inspection report artifacts while preserving JSON output:

```powershell
python -m aresforge inspect-work-item --work-item-id work-123 --write-artifact
```

The current runtime can create and list work items against the seeded canonical M2 queue set. `inspect-work-item` is read-only and local-only. It emits JSON that combines the work item with queue metadata, optional agent/model references, and work-item metadata fields such as lifecycle state, approval state, blocked reason, failure reason, and retry or correction context when present. With `--write-artifact`, it still emits JSON and additionally includes `inspection_payload`, `markdown_path`, and `json_path` for a local report written under `artifacts/inspection_reports/generated/`.

These inspection commands do not transition queues, mutate routing, approve anything, merge anything, close anything, or change GitHub state. Issue #39 remains protected and must not be modified or closed by this operator surface.

## Prompt, Evidence, And Handoff Artifacts

Generate a prompt package:

```powershell
python -m aresforge generate-prompt-package `
  --title "Issue 81 implementation prompt" `
  --objective "Build and validate the runnable local skeleton." `
  --notes "Human review required before execution."
```

Record evidence metadata:

```powershell
python -m aresforge record-evidence-package `
  --title "Issue 81 evidence package" `
  --files-changed src/aresforge/cli.py docs/operator/LOCAL_OPERATOR_USAGE.md `
  --validations-run "python -m pytest" "python -m aresforge validate-config" `
  --protected-issue-checks "Issue #39 was not modified or closed."
```

Prepare a Codex handoff file:

```powershell
python -m aresforge prepare-codex-handoff `
  --title "Issue 81 Codex handoff" `
  --summary "Review the runnable local skeleton state." `
  --requested-output "Produce a human-reviewable implementation or review handoff."
```

## Ollama Check

Test the configured Ollama endpoint:

```powershell
python -m aresforge test-ollama
```

If Ollama is not running, the command fails gracefully with a clear skip message. That is expected in environments where the local model service is not active.

This command is a connectivity check only. Model approval posture, task-class boundaries, routing priority, fallback rules, and governance-sensitive restrictions are defined by `docs/architecture/MODEL_REGISTRY_SCHEMA.md`, not by endpoint reachability.

## Validation Commands

Recommended local validation sequence:

```powershell
python -m pytest
python -m aresforge --help
python -m aresforge validate-config
python -m aresforge validate-registries
python -m aresforge inspect-registries
python -m aresforge list-artifacts
python -m aresforge migrate --plan
python -m aresforge list-models
python -m aresforge inspect-model --model-id model-ollama-default
python -m aresforge inspect-model --model-id missing-model-id
python -m aresforge inspect-project --project-id project-aresforge
git diff --check
git diff --cached --check
git status --short
```

If PostgreSQL is running locally, also run:

```powershell
python -m aresforge migrate
python -m aresforge inspect-project-state
python -m aresforge inspect-project --project-id project-aresforge
python -m aresforge list-models
python -m aresforge inspect-model --model-id model-ollama-default
```

The included Compose file maps PostgreSQL to host port `5433` by default so it does not collide with an existing local PostgreSQL on `5432`.

## PR Lifecycle Helper

Issue #99 adds a human-triggered PowerShell helper at `scripts/Invoke-AresForgePrLifecycle.ps1`.

This helper is phase-based on purpose. It does not silently run the entire PR lifecycle. The human operator must explicitly choose the phase to run.

Supported phases:

- `ValidateWorkingBranch`
- `StageCommitPush`
- `CreatePr`
- `VerifyPr`
- `MergePr`
- `PostMergeVerify`
- `SourceTruthScan`

The helper is a visible local wrapper around explicit `git`, `gh`, and local validation commands. It keeps branch state, validation output, PR state, merge readiness, and source-of-truth scan results visible to the human operator.

It is allowed to:

- run local validation commands
- stage explicitly supplied files
- create a commit from an explicit message
- push an explicit branch
- create a PR from an explicit body file
- verify PR state and open PR or issue state
- merge a PR only when the human explicitly runs the `MergePr` phase and the PR is `CLEAN`
- scan active source-of-truth docs for stale branch, issue, PR, and commit wording

It is not allowed to:

- run hidden background behavior
- choose issue scope autonomously
- invoke Codex autonomously
- transition queues
- mutate routing
- select models for governance-sensitive work
- approve, merge, or close issues autonomously
- call `gh issue close`
- modify protected Issue #39
- modify workflows, repo settings, branch protection, rulesets, secrets, releases, tags, or GitHub Projects

Example read-only validation phase:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Invoke-AresForgePrLifecycle.ps1 `
  -Phase ValidateWorkingBranch
```

Example source-of-truth scan:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Invoke-AresForgePrLifecycle.ps1 `
  -Phase SourceTruthScan `
  -IssueNumber 99 `
  -BranchName codex/issue-99-pr-lifecycle-helper
```

Example stage, commit, and push flow:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Invoke-AresForgePrLifecycle.ps1 `
  -Phase StageCommitPush `
  -BranchName codex/issue-99-pr-lifecycle-helper `
  -CommitMessage "Add PR lifecycle helper (#99)" `
  -FilesToStage scripts/Invoke-AresForgePrLifecycle.ps1 docs/operator/LOCAL_OPERATOR_USAGE.md
```

For `powershell -File` usage, prefer a staging-list file instead of multiple direct `-FilesToStage` values. This avoids fragile argument binding when many paths are supplied.

Example recommended `StageCommitPush` flow with a temporary file list:

```powershell
@'
scripts\Invoke-AresForgePrLifecycle.ps1
docs\operator\LOCAL_OPERATOR_USAGE.md
docs\architecture\RUNNABLE_SKELETON.md
docs\context\BUILD_STATE.md
docs\context\AGENT_CONTEXT.md
docs\roadmap\ROADMAP.md
'@ | Set-Content -LiteralPath .\.tmp_stage_files_issue_99.txt

powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Invoke-AresForgePrLifecycle.ps1 `
  -Phase StageCommitPush `
  -RepoPath "C:\Projects\aresforge" `
  -BranchName "codex/issue-99-pr-lifecycle-helper" `
  -CommitMessage "Add human-triggered PR lifecycle helper" `
  -FilesToStagePath "C:\Projects\aresforge\.tmp_stage_files_issue_99.txt"
```

When `-FilesToStagePath` is supplied, the helper resolves the file to an absolute path, reads non-empty non-comment lines, de-duplicates entries while preserving order, and uses that effective list for `git add`. The temporary staging-list file itself is treated as an allowed local helper input and does not need `-AllowUntracked`.

Example PR creation flow:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Invoke-AresForgePrLifecycle.ps1 `
  -Phase CreatePr `
  -BranchName codex/issue-99-pr-lifecycle-helper `
  -PrTitle "Add human-triggered PR lifecycle helper (#99)" `
  -PrBodyPath .\artifacts\pr_body_issue_99.md
```

The helper resolves `PrBodyPath` to an absolute path before PR creation and uses `gh pr create --body-file` so multiline Markdown does not rely on fragile direct `--body` argument passing in Windows PowerShell.

The `ValidateWorkingBranch` phase runs the standard M2 validation sequence:

- `.\.venv\Scripts\python.exe -m pytest`
- `.\.venv\Scripts\python.exe -m aresforge --help`
- `.\.venv\Scripts\python.exe -m aresforge validate-config`
- `.\.venv\Scripts\python.exe -m aresforge validate-registries`
- `.\.venv\Scripts\python.exe -m aresforge migrate --plan`
- optional `.\.venv\Scripts\python.exe -m aresforge migrate` when `-IncludeDatabaseValidation` is supplied
- any explicit `-ExtraValidationCommand` values
- `git diff --check`
- `git diff --cached --check`
- `git status --short --branch`

The `StageCommitPush` phase refuses to run on `main`, confirms the current branch matches `-BranchName`, requires `-CommitMessage` plus at least one effective staging file from `-FilesToStage` or `-FilesToStagePath`, and refuses unexpected untracked files unless `-AllowUntracked` is supplied.

The `MergePr` phase is intentionally narrow. It only runs when the human explicitly selects `-Phase MergePr`, it refuses PRs whose `mergeStateStatus` is not `CLEAN`, and it performs `gh pr merge --squash --delete-branch`. It does not close issues directly.

The `SourceTruthScan` phase is read-only. It scans:

- `docs/context/BUILD_STATE.md`
- `docs/context/AGENT_CONTEXT.md`
- `docs/roadmap/ROADMAP.md`

It prints matches for the current branch, the supplied branch or issue or PR identifiers, and stale wording markers such as `current-branch`, `on the current branch`, `Latest main commit`, and `Latest runtime-affecting merged foundation commit`. It does not edit docs.

Recommended script validation:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "$null = [scriptblock]::Create((Get-Content -Raw 'C:\Projects\aresforge\scripts\Invoke-AresForgePrLifecycle.ps1')); 'parse-ok'"
```

## Boundaries

The local operator is allowed to:

- validate config
- manage local PostgreSQL migrations
- inspect documented local registry and lifecycle sources
- write local prompt/evidence/handoff artifacts
- perform local Ollama test calls
- inspect local project state
- run the human-triggered PR lifecycle helper phases described above

The local operator is not allowed to:

- merge pull requests autonomously
- close issues
- approve changes
- change repository settings
- change branch protection or rulesets
- change secrets
- create releases or tags
- change GitHub Projects
- invoke Codex autonomously

The local operator also is not allowed to autonomously select models for governance-sensitive actions or silently fall through to hosted external model APIs.
