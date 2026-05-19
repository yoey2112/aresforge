# Ollama Evidence Review Skill

## Name

Ollama evidence review

## Purpose

Guide review of local Ollama-generated validation evidence so agents can summarize its usefulness, limitations, and human-review implications.

## When to use

Use this skill when a task includes local model review output, asks for Ollama validation evidence, or needs a structured assessment of AI-generated review results.

## When not to use

Do not use this skill to treat AI output as an approved decision, merge gate, autonomous approval, issue closure, or replacement for human review.

## Inputs

- Local Ollama prompt, model name, and output when available.
- Validation commands and artifacts reviewed by the local model.
- Relevant issue, PR, or task requirements.
- PR validation and governance docs.
- Known limitations from prior Ollama validation evidence.

## Outputs

- Summary of what the Ollama evidence supports.
- Limitations, uncertainty, and reviewer cautions.
- Advisory validation recommendation for human review.
- Follow-up evidence requests when the model output is incomplete or unclear.

## Scope boundaries

This skill covers interpretation of local AI review evidence. It does not authorize workflow creation, model-service integration, automated validation gates, or treating local model output as final authority.

## Execution boundaries

This skill is advisory and manually executed. It does not create Ollama scripts, services, workflows, packages, or adapters.

## Human approval boundaries

Human approval is required before local AI review becomes a required merge gate, blocks PRs automatically, approves PRs, closes issues, or changes repository workflow behavior.

## Documentation impact

Review docs/governance/PR_VALIDATION_MODEL.md when local AI evidence affects PR validation expectations. Review docs/context/BUILD_STATE.md when evidence changes active work state or known limitations.

## Validation expectations

Confirm the evidence being reviewed is tied to the correct issue or PR, includes enough context to evaluate, and is reported as advisory rather than approved.

## Evidence requirements

Report model name when known, input evidence reviewed, decision or recommendation produced by the model, limitations, human-review needs, and any skipped or unavailable validation.

## Related docs

- docs/governance/PR_VALIDATION_MODEL.md
- docs/governance/SELF_MANAGEMENT_MODEL.md
- docs/context/BUILD_STATE.md
- docs/validation/OLLAMA_GITHUB_OPERATION_REVIEW.md
- docs/agents/AGENT_SKILLS_MODEL.md

## Lifecycle status

Draft
