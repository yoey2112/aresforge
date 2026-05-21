# Structured Sprint Issue Definition Contract

## Purpose

Define the local structured contract used by `generate-sprint-issue-script` to produce a hardened PowerShell issue-creation script for human review and manual execution.

## Safety Boundary

- Output-only command behavior.
- Human-triggered and human-executed GitHub mutation only.
- AresForge command generation does not call `gh issue create`.
- No autonomous setup, closeout, merge, comments, labels, milestones, releases, or tags.
- Protected historical Issue #39 remains safety-only and must not be treated as active implementation linkage.

## Definition Format

JSON object.

### Required Root Fields

- `sprint_id`: string.
- `repo`: string (`owner/repo`).
- `parent`: object.
- `children`: non-empty array of objects.

### Optional Root Fields

- `notes`: string.
- `output_path`: string (CLI `--output` can still override).

### Parent Required Fields

- `title`: string.
- `body`: string.

### Child Required Fields

- `title`: string.
- `body`: string.

### Body Requirements (Parent and Child)

- Must include `## Safety Posture`.
- Must include `## Acceptance Criteria`.
- Must include `## Validation`.
- Must include read-only/human-gated mutation boundary language.
- Must not include nested markdown fences (` ``` `) because generated output uses PowerShell here-strings.

### Child Linkage Requirement

Each child body must include explicit parent linkage using placeholder:

`Part of #{{PARENT_ISSUE_NUMBER}}`

The generated script replaces `{{PARENT_ISSUE_NUMBER}}` after parent creation.

## Validation Expectations

Validation fails with actionable messages when it detects:

- missing required fields
- missing parent/child linkage sections
- missing safety posture sections
- missing acceptance criteria
- missing validation section
- nested markdown fences in body text
- risky Issue #39 references not marked protected historical
- ambiguous linked-issue wording that is not explicit implementation linkage
- missing read-only and human-gated mutation boundary language

## Output Contract

Command:

`python -m aresforge generate-sprint-issue-script --definition <definition.json>`

Optional explicit local planning-state persistence:

`python -m aresforge generate-sprint-issue-script --definition <definition.json> --write-planning-state`

Optional output override:

`python -m aresforge generate-sprint-issue-script --definition <definition.json> --output <script.ps1>`

Result:

- Writes local `.ps1` script only.
- Writes local planning state only when `--write-planning-state` is explicitly provided.
- Emits JSON command result with `mutation_posture=output_only_human_execution_required`.
- Performs no GitHub mutation.

## Human Execution Boundary

The generated script is an operator artifact.

Operator responsibilities:

- review generated parent/child bodies
- confirm protected historical wording for Issue #39 remains safety-only
- execute script manually when approved
- verify GitHub results manually

## Example Definition

`{
  "sprint_id": "M8",
  "repo": "yoey2112/aresforge",
  "parent": {
    "title": "M8: Harden sprint planning and closeout evidence workflows",
    "body": "## Safety Posture\n- human-triggered operations only\n- read-only planning by default\n- no autonomous mutation\n\n## Acceptance Criteria\n- Parent issue captures sprint scope\n\n## Validation\n- python -m pytest"
  },
  "children": [
    {
      "title": "M8: Improve closeout planner merged PR evidence detection",
      "body": "Part of #{{PARENT_ISSUE_NUMBER}}\nImplements explicit closeout evidence detection.\n\n## Safety Posture\n- human-triggered issue creation only\n- read-only generation command\n- no autonomous setup or mutation\n\n## Acceptance Criteria\n- Evidence detection hardened\n\n## Validation\n- python -m pytest"
    }
  ]
}`
