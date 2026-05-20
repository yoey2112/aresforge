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
python -m aresforge list-queues
```

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

## Validation Commands

Recommended local validation sequence:

```powershell
python -m pytest
python -m aresforge --help
python -m aresforge validate-config
python -m aresforge migrate --plan
git diff --check
git diff --cached --check
git status --short
```

If PostgreSQL is running locally, also run:

```powershell
python -m aresforge migrate
python -m aresforge inspect-project-state
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
