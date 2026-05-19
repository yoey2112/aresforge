# AresForge Codex Prompt Standard

## Purpose

This standard defines how work should be handed to Codex or another coding agent.

## Required Prompt Sections

Each implementation prompt should include:

1. Task
2. Context
3. Files to read first
4. Goal
5. Constraints
6. Required changes
7. Validation steps
8. Documentation updates
9. Commit and PR expectations
10. Evidence to report back

## Required Constraints

Every prompt should tell the agent to:

- Read relevant docs before coding
- Avoid unrelated changes
- Keep changes small and reviewable
- Update documentation when behavior changes
- Run validation commands
- Report files changed
- Report tests run
- Create or update PR evidence

## Baseline Prompt Template

Task:
[Describe the issue or implementation goal.]

Context:
[Summarize project state and why this work matters.]

Read first:
- [List exact files]

Goal:
[Define the successful end state.]

Constraints:
- Do not make unrelated changes.
- Do not skip documentation updates.
- Do not enable destructive automation without explicit approval.

Required changes:
- [List expected changes]

Validation:
- [List exact commands or checks]

Documentation:
- [List docs that must be updated]

Deliverable:
- Branch name
- Commit summary
- PR summary
- Validation evidence
- Follow-up risks or blockers
