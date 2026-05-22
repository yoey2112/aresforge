# Sprint Issue Creation Planning Contract

## Purpose

Define the read-only M12 planning contract for deterministic, human-gated sprint issue creation output.

## Command Surface

- `python -m aresforge plan-sprint-issues --definition <path>`

## Input Contract

Required root fields:

- `sprint_id` (string)
- `repo` (string)
- `parent` (object with `title`, `body`)
- `children` (non-empty array of objects with `title`, `body`)

Required body expectations:

- `## Safety Posture`
- `## Acceptance Criteria`
- `## Validation`
- child bodies include `Part of #{{PARENT_ISSUE_NUMBER}}`
- no nested markdown fences inside bodies (` ``` ` disallowed)
- safety boundary phrases include `human-triggered`, `read-only`, and `no autonomous`

## Output Contract

`plan-sprint-issues` emits deterministic JSON with:

- `command`
- `ok`
- `inspection_mode` = `read_only_generated_plan`
- `mutation_posture` = `human_gated_output_only`
- `safety_warnings`
- normalized plan summary (`sprint_id`, `repo`, `parent_title`, `child_titles`, `child_count`)
- rendered artifacts:
  - `parent_issue_body`
  - `child_issue_bodies`
  - `powershell_issue_creation_block`
  - `parent_child_index_update`
  - `final_post_creation_verification_block`

## Verification-Aware Requirements

Generated verification output must compare intended plan versus live issue state for:

- expected parent issue title
- actual parent issue title
- expected child count
- actual child count
- missing expected child titles
- unexpected child titles
- parent child-index completeness
- required body-section completeness
- safety-boundary text presence
- overall pass/fail

Failure guidance remains text-only and human-gated:

- do not continue implementation
- review mismatch report
- run generated repair block or manually reconcile issue state

## Safety Posture

- Planner command is read-only and does not execute `gh`.
- Planner command never creates/edits/closes/issues labels/milestones/assignees/projects/PR merges/releases/tags.
- Generated scripts may include `gh` commands but require explicit human execution.
