# Future Feature Ideas

## Purpose

This file is a lightweight parking lot for future AresForge feature ideas.

This file is not the active roadmap. It does not define milestone scope, committed work, project dependencies, implementation order, or approval to change repository behavior.

Ideas listed here are candidates for review when starting a new milestone. They may be accepted, deferred, revised, split, or rejected based on the active roadmap, current validation evidence, governance readiness, documentation freshness, and human owner direction at that time.

## Review Rule

At the beginning of each milestone, review this file to determine whether any ideas should influence milestone direction.

Any idea selected for milestone work must be promoted through the normal AresForge planning path before implementation. Promotion should include source-of-truth documentation updates, validation expectations, governance boundaries, and explicit human-reviewed scope.

## Idea Status Values

- Candidate for future milestone review
- Needs more evidence
- Deferred
- Rejected
- Promoted to active planning

## Idea Entry Template

```markdown
### Idea Title

Status: Candidate for future milestone review

Summary:

Potential value:

Possible uses:

First safe experiment:

Readiness requirements:

Non-goals:

Notes:
```

## Ideas

### Evaluate MCP as an AresForge Agent Tool Interface

Status: Candidate for future milestone review

Summary:

MCP may provide value as a standardized interface between AresForge agents and external tools.

Potential value:

- Standardize how agents request tool access.
- Reduce one-off connector patterns if the model proves useful under AresForge governance.
- Support future tool integration reviews without making any single tool interface foundational too early.

Possible uses:

- GitHub operations.
- Read-only project context access.
- Documentation agent tooling.
- Ollama or local validation interfaces.
- Future project connectors.

First safe experiment:

Read-only project context access should be the first safe experiment if MCP is evaluated.

Readiness requirements:

Write-capable MCP should not be considered until AresForge's governance, validation, and documentation freshness models are stable.

Non-goals:

- MCP is not a committed project dependency at this stage.
- MCP should not be treated as a foundation dependency at this stage.
- This idea does not authorize MCP-backed write operations, workflow changes, automation, autonomous approval, autonomous issue closure, or repository setting changes.

Notes:

Any MCP evaluation should remain validation-first, documentation-driven, and bounded by explicit human-reviewed scope.
