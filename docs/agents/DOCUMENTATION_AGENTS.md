# AresForge Documentation Agents

## Purpose

Documentation agents ensure that every pushed change updates the documentation needed by humans and AI agents.

## Initial Model

AresForge may use one or more documentation agents:

- Context Documentation Agent
- Architecture Documentation Agent
- Roadmap Documentation Agent
- Governance Documentation Agent
- Prompt Documentation Agent
- Release Notes Documentation Agent

## Required Behavior

Documentation agents should:

- Detect changed files
- Identify impacted documentation
- Update relevant docs
- Preserve historical context
- Avoid overwriting intentional human decisions
- Summarize changes clearly
- Flag missing or stale documentation
- Produce evidence for PR validation

## M0 Decision

The first documentation agent should focus on keeping these files current:

- docs/context/PROJECT_CONTEXT.md
- docs/context/AGENT_CONTEXT.md
- docs/context/BUILD_STATE.md
- docs/roadmap/ROADMAP.md
- docs/architecture/SYSTEM_OVERVIEW.md
