# AresForge System Overview

## Architecture Direction

AresForge is a local-first AI software factory.

The system should coordinate GitHub, local AI models, automation workflows, documentation, project state, and eventually a dashboard.

## Current M0 Architecture

During M0, the system uses:

- GitHub repository as source control
- GitHub Issues as task tracking
- GitHub Milestones as phase tracking
- GitHub pull requests as review boundaries
- GitHub labels as lightweight routing, phase, risk, and evidence metadata
- GitHub Actions as automation runner entry points
- Ares self-hosted runner for local execution
- Ollama for local model review and validation
- Markdown documentation as the project memory layer

## Current Project-State Architecture

Until the dashboard exists, AresForge project state is distributed across:

- docs/context/PROJECT_CONTEXT.md for identity, vision, and source-of-truth rules
- docs/context/AGENT_CONTEXT.md for agent behavior and operating context
- docs/context/BUILD_STATE.md for current milestone, completed work, in-progress work, and next steps
- docs/roadmap/ROADMAP.md for milestone sequencing
- docs/governance/SELF_MANAGEMENT_MODEL.md for the self-management loop and future dashboard state
- docs/agents/DOCUMENTATION_AGENTS.md for documentation update responsibilities
- docs/validation/ for validation evidence

## Future Architecture Components

Planned future components include:

- AresForge dashboard
- Agent orchestration layer
- Project registry
- Task queue
- Agent execution logs
- Local model validation service
- Documentation update pipeline
- PR validation and scoring service
- Cost and usage tracking
- Release management automation

## Future Dashboard Responsibility

The future dashboard should consolidate the currently distributed GitHub and documentation state into a readable project control surface.

The dashboard should not replace GitHub or documentation as durable records until the governance model explicitly allows that transition.
