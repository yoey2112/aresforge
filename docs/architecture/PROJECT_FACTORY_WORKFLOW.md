# Project Factory Workflow

## Purpose

Define the canonical end-to-end AresForge project factory workflow so future implementation milestones build in the correct order.

## Product Vision

AresForge is a local-first AI project factory and orchestration hub. The Hub is mission control for starting projects, linking repos, planning work, routing tasks to the right agents, validating outcomes, updating documentation, and closing milestones and projects with explicit safety gates.

## Canonical AresForge Build Pipeline

1. Project intake
2. Repo create/link
3. Project scoping
4. Architecture/design
5. Milestone planning
6. Issue planning
7. GitHub apply boundary
8. Agent queue dispatch
9. Agent run lifecycle
10. Validation
11. Documentation update
12. Milestone/project closeout

## Core Entities

- Project: top-level managed product effort with lifecycle state and ownership context.
- Repo: local and GitHub-linked repository context associated with a project.
- Active Project: currently selected project context in Hub.
- Intake: structured request to start a new project or add feature work.
- Scope Artifact: accepted statement of asks, constraints, and success criteria.
- Architecture Artifact: approved technical design and implementation approach.
- Milestone Plan: planned milestone breakdown derived from scope and architecture.
- Issue Plan: planned issue/task set mapped to milestones.
- Queue Item: local work unit tracked for dispatch/execution lifecycle.
- Agent Profile: capability and boundary profile for an execution path.
- Agent Dispatch: routing decision that assigns queue work to an agent path.
- Agent Run: lifecycle record for execution attempt, outputs, and status.
- Validation Evidence: test/check/review evidence proving acceptance criteria.
- Documentation Update: required source-of-truth and operational docs updates.
- Closeout Record: accepted milestone/project completion summary and evidence map.

## New Project Lifecycle

1. Start project.
2. Create/link repo.
3. Scope ask.
4. Architect solution.
5. Plan milestones/issues.
6. Approve GitHub mutation boundary.
7. Create GitHub issues/milestones.
8. Dispatch agent work.
9. Validate outputs.
10. Update docs.
11. Close project/milestone.

## Add Feature Lifecycle

1. User adds feature to existing active project.
2. Scope feature.
3. Perform impact analysis.
4. Decide whether work is:
   - new milestone
   - new issue
   - update existing issue
   - docs-only update
5. Approve GitHub mutation boundary where needed.
6. Dispatch agent work.
7. Validate outputs.
8. Update docs.
9. Close feature work.

## Multi-Project Orchestration

- Multiple projects can run in parallel.
- Each project owns its own queue state.
- Agents can work across project queues.
- Hub must present project, repo, queue, agent, run, validation, and closeout state in one mission-control view.

## Safety Model

- Read-only local operations: inspection/planning workflows with no mutation.
- Local write operations: local registry, queue, artifacts, and docs updates.
- GitHub mutation-gated operations: explicit boundary before any issue/milestone mutation.
- AI/model execution-gated operations: explicit boundary before any agent/model run.
- User approval boundaries: required for mutation and execution transitions.

## M43-M45 Relationship

- M43 active project support is the active context layer.
- M44 active project intake is the first user-to-queue bridge.
- M45 active project workbench is mission control foundation.
- M43-M45 do not yet complete the full end-to-end project factory loop.

## Next Milestone Sequence

- M47 New Project Wizard
- M48 Repo Create/Link Planner And Approval Gate
- M49 Project Scope And Architecture Contract
- M50 Milestone And Issue Plan Generator
- M51 Explicit GitHub Milestone/Issue Apply Boundary
- M52 Agent Queue Dispatcher
- M53 Agent Run Lifecycle, Evidence, And Validation Gates
- M54 Documentation And Closeout Automation
- M55 Active-Project Feature Loop
