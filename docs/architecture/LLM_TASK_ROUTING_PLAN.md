# LLM Task Routing Plan

## Purpose

This document defines the future task routing plan for local LLM usage in AresForge.

The plan is advisory only. AresForge is not yet wiring live LLM execution into workflows.

The first implementation must remain local-first, read-only where possible, and operator-gated.

## Routing summary

AresForge will initially route local LLM tasks between two Ollama aliases:

| Alias | Role |
| --- | --- |
| `aresforge-coder-local` | Coding and implementation support |
| `aresforge-reasoner-local` | Reasoning, planning, documentation, and validation support |

The models are not expected to run concurrently on the current hardware.

## Core routing principle

AresForge should route by task intent, not by screen location.

For example, a task created from the Queue screen may need the coding model if it is implementation-heavy, but the same Queue screen may need the reasoning model if the task is planning-heavy.

Routing decisions should be explicit, explainable, and visible to the operator.

## Coding model routing

Use `aresforge-coder-local` for tasks where the primary output is implementation-oriented.

### Preferred coding-model tasks

The coding model should handle:

- Code generation
- Bug fixing
- Test creation
- Repo-aware implementation prompts
- Code review
- Patch planning
- Refactoring recommendations
- Static analysis interpretation
- Failure diagnosis from test output
- File-by-file implementation sequencing
- Local change summaries

### Example routing intents

Route to the coding model when the task asks to:

- Implement a feature
- Fix a failing test
- Add unit coverage
- Review a diff
- Generate a patch plan
- Update a CLI command
- Modify an API route
- Add frontend behavior
- Explain a stack trace
- Convert requirements into implementation steps

### Initial coding output types

The coding model may produce:

- Implementation prompts
- Patch plans
- Suggested file changes
- Review notes
- Test plans
- Risk notes
- Validation commands

The coding model must not directly apply file changes until AresForge has a validated operator approval workflow.

## Reasoning model routing

Use `aresforge-reasoner-local` for tasks where the primary output is planning, analysis, or synthesis.

### Preferred reasoning-model tasks

The reasoning model should handle:

- Architecture planning
- Task decomposition
- Milestone planning
- Documentation synthesis
- Risk analysis
- Validation planning
- Prompt optimization
- Handoff generation
- Requirements clarification
- Decision records
- Roadmap sequencing
- Operator workflow design

### Example routing intents

Route to the reasoning model when the task asks to:

- Break down a milestone
- Decide between implementation options
- Summarize project state
- Create documentation
- Review architecture
- Identify risks
- Create validation gates
- Generate Codex prompts
- Prepare a handoff
- Map dependencies between tasks

### Initial reasoning output types

The reasoning model may produce:

- Architecture notes
- Decision records
- Milestone plans
- Task decomposition
- Prompt drafts
- Documentation drafts
- Risk registers
- Validation checklists
- Operator handoffs

The reasoning model must not directly create project tasks, write files, or start agent execution without operator approval.

## Advisory routing phase

The first AresForge LLM routing phase should be advisory.

In this phase, AresForge may:

- Recommend a model for a task.
- Explain why the model was selected.
- Generate the prompt that would be sent to the model.
- Allow the operator to copy or approve the prompt.
- Store the prompt as a local artifact.
- Store the model response as a local artifact after operator-approved execution.

In this phase, AresForge must not:

- Automatically send every task to a model.
- Automatically execute generated commands.
- Automatically apply model-generated code.
- Automatically commit or push changes.
- Automatically call GitHub APIs.
- Automatically create GitHub issues.

## Suggested routing metadata

When AresForge eventually stores routing decisions, each local routing record should include:

| Field | Purpose |
| --- | --- |
| `task_id` | Local task or queue item identifier |
| `recommended_model_alias` | Selected local alias |
| `routing_reason` | Human-readable reason for model selection |
| `routing_confidence` | Low, medium, or high confidence |
| `operator_approved` | Whether the operator approved the routing |
| `prompt_artifact_path` | Local path to the generated prompt artifact |
| `response_artifact_path` | Local path to the response artifact, if execution occurred |
| `execution_mode` | Advisory, approved-local-run, or future automated mode |
| `created_at` | Local timestamp |
| `validated_at` | Local validation timestamp, if applicable |

## Routing examples

### Example: bug fix task

Task:

    Fix failing tests in the local queue lifecycle API.

Recommended model:

    aresforge-coder-local

Reason:

    The task requires test failure analysis, implementation planning, and code-level changes.

Expected output:

    Patch plan, affected files, validation commands, and operator-reviewed implementation prompt.

### Example: milestone planning task

Task:

    Break the next AresForge phase into five local-only milestones.

Recommended model:

    aresforge-reasoner-local

Reason:

    The task requires planning, sequencing, risk assessment, and documentation synthesis.

Expected output:

    Milestone plan, scope boundaries, validation gates, and implementation prompts.

### Example: documentation closeout task

Task:

    Update project context docs after completing a local-only milestone.

Recommended model:

    aresforge-reasoner-local

Reason:

    The task requires summarization, consistency checking, and documentation synthesis.

Expected output:

    Proposed documentation edits and validation checklist.

### Example: code review task

Task:

    Review the current diff for unsafe network execution paths.

Recommended model:

    aresforge-coder-local

Reason:

    The task requires repo-aware code review and risk identification in implementation files.

Expected output:

    Findings, file references, risk level, and recommended patch plan.

## Future automated routing path

Automated routing should only be considered after the advisory routing phase is validated.

A safe progression is:

1. Manual model selection by operator.
2. Advisory model recommendation with visible rationale.
3. Operator-approved prompt generation.
4. Operator-approved local inference call.
5. Local response artifact capture.
6. Operator-approved application of model output.
7. Validated routing rules with test coverage.
8. Limited automation for low-risk documentation-only tasks.
9. Broader automation only after audit trail, rollback, and policy gates exist.

## Required safeguards before automation

Before AresForge performs automated routing or execution, the project must have:

- Local model readiness checks.
- Operator approval gates.
- Prompt artifact storage.
- Response artifact storage.
- Clear execution mode labels.
- Tests proving no network execution occurs.
- Tests proving GitHub APIs are not called.
- Tests proving generated commands are not automatically executed.
- A rollback or discard path for generated outputs.
- Documentation showing how to disable local LLM routing.

## Non-goals

The routing layer should not initially support:

- Concurrent large-model execution.
- Cloud fallback.
- Autonomous repo modification.
- Autonomous GitHub issue creation.
- Autonomous commit or push.
- Autonomous command execution.
- Unreviewed agent-to-agent task chaining.

## Related documents

- `docs/architecture/LOCAL_LLM_STRATEGY.md`
- `docs/operator/OLLAMA_LOCAL_SETUP.md`
- `docs/context/LOCAL_LLM_DECISION_RECORD.md`