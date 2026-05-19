# AresForge System Overview

## Architecture Direction

AresForge is a local-first AI software factory.

The system should coordinate GitHub, local AI models, automation workflows, documentation, project state, and eventually a dashboard.

## Current M0 Architecture

During M0, the system uses:

- GitHub repository as source control
- GitHub Issues as task tracking
- GitHub Milestones as phase tracking
- GitHub Actions as automation runner entry points
- Ares self-hosted runner for local execution
- Ollama for local model review and validation
- Markdown documentation as the project memory layer

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
