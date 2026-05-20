# Local Operator Usage

## Purpose

This guide explains how to run the first local AresForge operator introduced by Issue #81.

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

List projects and queues:

```powershell
python -m aresforge list-projects
python -m aresforge list-agents
python -m aresforge list-models
python -m aresforge list-queues
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
python -m aresforge migrate --plan
git diff --check
git diff --cached --check
git status --short
```

If PostgreSQL is running locally, also run:

```powershell
python -m aresforge migrate
python -m aresforge inspect-project-state
python -m aresforge list-models
```

The included Compose file maps PostgreSQL to host port `5433` by default so it does not collide with an existing local PostgreSQL on `5432`.

## Boundaries

The local operator is allowed to:

- validate config
- manage local PostgreSQL migrations
- write local prompt/evidence/handoff artifacts
- perform local Ollama test calls
- inspect local project state

The local operator is not allowed to:

- merge pull requests
- close issues
- approve changes
- change repository settings
- change branch protection or rulesets
- change secrets
- create releases or tags
- change GitHub Projects
- invoke Codex autonomously

The local operator also is not allowed to autonomously select models for governance-sensitive actions or silently fall through to hosted external model APIs.
