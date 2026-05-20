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
- `migrate`
- `inspect-project-state`
- `list-projects`
- `list-queues`
- `create-work-item`
- `list-work-items`
- `generate-prompt-package`
- `record-evidence-package`
- `test-ollama`
- `prepare-codex-handoff`

These commands are human-triggered only.

## Vertical Slice Achieved

The current vertical slice is:

1. configure local environment
2. start PostgreSQL locally
3. apply repo-stored migrations
4. bootstrap minimal reference data
5. create a work item and assign a queue
6. generate a prompt package
7. record evidence metadata
8. prepare a Codex handoff artifact
9. optionally test a local Ollama model call

That is enough to prove the local execution path without over-designing agents, routing intelligence, or background automation.

## Ollama Boundary

The Ollama adapter is intentionally small:

- one HTTP generate call
- one dry-run/test command
- graceful failure when Ollama is not running

It is a connectivity and interface check, not a full orchestration runtime.

## Codex Boundary

Codex integration is intentionally output-file generation only.

The CLI can prepare a reviewable handoff artifact, but it does not invoke Codex autonomously and it does not grant GitHub or repository mutation authority.

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

The runnable skeleton is local-first and human-triggered by design.
