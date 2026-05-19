# AresForge Error Patterns

## Purpose

This document is the canonical place for durable AresForge lessons about repeatable errors, failed commands, shell and tool limitations, encoding problems, and corrective guidance.

The goal is to keep future human-guided agents from rediscovering the same operational failures. A learning entry should turn a repeated or high-signal error from transient chat output into reviewable project knowledge that can guide future prompts, skills, validation docs, governance docs, and dashboard rules.

During M1, this document is documentation only. It does not enable runnable automation, auto-merge, autonomous approval, autonomous issue closure, destructive automation, or autonomous command execution.

## When To Promote An Error

Promote an error from chat, command output, issue evidence, or PR evidence into this document when at least one of the following is true:

- The same failure pattern appears more than once.
- The failure affected GitHub operations, repository state, issue planning, PR evidence, build state, or source-of-truth documentation.
- The failure could cause future agents to create incorrect evidence, corrupt encoding, repeat fragile commands, or trust a command that did not actually fix the problem.
- The workaround is safer than the obvious command a future agent might otherwise choose.
- The issue, PR, or human owner identifies the lesson as reusable project knowledge.

Do not promote every typo, one-off local mistake, or speculative concern. Learning entries should be specific enough that a future agent can change behavior because of them.

## Required Fields

Each learning entry should include:

| Field | Requirement |
|---|---|
| ID | Stable identifier such as `M1-ERROR-001`. |
| Status | Observed, suspected, confirmed, mitigated, or superseded. |
| Area | GitHub CLI, PowerShell, encoding, build state, validation, documentation, or another affected area. |
| Summary | Short description of the failure pattern. |
| Observed fact | What was directly observed in command output, file content, validation evidence, or issue comments. |
| Suspected root cause | The likely cause when not yet proven. Mark as suspected. |
| Confirmed root cause | The proven cause when validation confirms it. Use `Not confirmed` when unknown. |
| Workaround | The safer manual approach to use until a confirmed fix exists. |
| Confirmed fix | The verified permanent fix, or `None during M1` when no permanent fix has been implemented. |
| Verification expectation | How future agents should prove the issue is avoided or resolved. |
| Update targets | Skills, validation docs, prompts, governance docs, or dashboard rules that should learn from the entry. |
| M1 boundary | Confirmation that the entry is advisory/manual during M1 and does not authorize automation. |

## Fact, Cause, Workaround, And Fix

Learning entries must distinguish between:

- Observed fact: Evidence that actually happened, such as a command failure, parser error, mojibake, or byte-level file content.
- Suspected root cause: A plausible explanation that has not been fully proven.
- Confirmed root cause: A cause verified through reproduction, documentation, tool behavior, byte or code-point inspection, or another concrete check.
- Workaround: A safer operating pattern that avoids or reduces the failure.
- Confirmed fix: A verified change that removes the failure mode rather than merely avoiding it.

A workaround is not the same as a confirmed fix. During M1, most entries are expected to be advisory lessons and manual mitigations.

## How Entries Should Propagate

When a learning entry affects repeatable work, update the smallest relevant source-of-truth docs:

- Skills: Update `.agent/skills/` when the lesson changes how agents should perform a repeatable task.
- Validation docs: Update `docs/validation/` when the lesson changes evidence expectations or reliable command patterns.
- Prompt docs: Update `docs/prompts/` when future implementation prompts should require the lesson.
- Governance docs: Update `docs/governance/` when the lesson changes autonomy, review, escalation, or source-of-truth boundaries.
- Context docs: Update `docs/context/` when the lesson changes active work, handoff expectations, or agent operating context.
- Future dashboard rules: Record candidate dashboard checks only as future recommendations unless a later issue explicitly approves implementation.

During M1, learning propagation is manual and human-reviewed. A learning entry may guide future prompts and skills, but it does not authorize automation by itself.

## Initial M1 Learning Entries

### M1-ERROR-001: Unsupported `gh issue create --json`

| Field | Value |
|---|---|
| Status | Confirmed |
| Area | GitHub CLI |
| Summary | The installed GitHub CLI does not support `gh issue create --json`. |
| Observed fact | Issue #18 evidence recorded that `gh issue create --json` is unsupported in the current AresForge environment. |
| Suspected root cause | The installed GitHub CLI version or command surface lacks JSON output support for `gh issue create`. |
| Confirmed root cause | The command is unsupported in the installed CLI behavior observed during M1. |
| Workaround | Use `gh issue create`, capture the returned issue URL, extract the issue number from the URL, then verify with `gh issue view --json`. |
| Confirmed fix | None during M1. |
| Verification expectation | Do not assume issue creation returns JSON. Verify created issue state with `gh issue view --json` after creation or update. |
| Update targets | `.agent/skills/github-operations/SKILL.md`, `.agent/skills/issue-planning/SKILL.md`, `docs/validation/GITHUB_CAPABILITY_VALIDATION.md`, future dashboard GitHub-operation rules. |
| M1 boundary | Advisory/manual only; does not enable autonomous issue creation. |

### M1-ERROR-002: Fragile `gh api --jq` Quoting In Windows PowerShell

| Field | Value |
|---|---|
| Status | Confirmed |
| Area | GitHub CLI, PowerShell |
| Summary | `gh api --jq` expressions with shell quoting can fail in Windows PowerShell. |
| Observed fact | Issue #18 evidence recorded fragile quoted `gh api --jq` milestone discovery. This implementation session also observed a PowerShell parser failure for an unquoted Git revision expression containing `@{u}`. |
| Suspected root cause | PowerShell parsing and quoting rules can interpret characters before the intended command receives them. |
| Confirmed root cause | PowerShell parser behavior can prevent the command from running as intended when expressions are not safely quoted or escaped. |
| Workaround | Prefer raw `gh api` output parsed with PowerShell JSON handling. Quote shell-sensitive tokens carefully and verify the resulting object. |
| Confirmed fix | None during M1. |
| Verification expectation | Verify milestone, issue, or PR state after parsing instead of trusting a quoted shell expression. |
| Update targets | `.agent/skills/github-operations/SKILL.md`, `docs/validation/GITHUB_CAPABILITY_VALIDATION.md`, future dashboard command-safety rules. |
| M1 boundary | Advisory/manual only; does not authorize command automation. |

### M1-ERROR-003: Temporary JSON Payload Encoding Risk

| Field | Value |
|---|---|
| Status | Observed |
| Area | GitHub API, PowerShell, encoding |
| Summary | Temporary JSON payload posting can fail when file encoding is not handled carefully. |
| Observed fact | Issue #18 evidence recorded direct JSON payload posting through temporary files as fragile because payload posting can fail when encoding is not controlled and verified. |
| Suspected root cause | PowerShell and .NET file-writing defaults may produce encodings or byte order behavior that a later API call does not expect. |
| Confirmed root cause | Not confirmed for every failure mode. The encoding risk is confirmed enough to avoid the pattern during M1. |
| Workaround | Use supported `gh issue create` flags for initial creation and `gh api` form fields or carefully verified API calls for updates. Avoid temp-file payloads unless encoding is intentional and inspected. |
| Confirmed fix | None during M1. |
| Verification expectation | When a payload file is unavoidable, inspect the exact content and encoding-sensitive bytes before posting, then verify the resulting GitHub state. |
| Update targets | `.agent/skills/github-operations/SKILL.md`, `.agent/skills/issue-planning/SKILL.md`, `docs/validation/GITHUB_CAPABILITY_VALIDATION.md`. |
| M1 boundary | Advisory/manual only; does not add scripts or payload automation. |

### M1-ERROR-004: Markdown Mojibake From Mixed Encoding Methods

| Field | Value |
|---|---|
| Status | Observed |
| Area | Markdown, PowerShell, encoding |
| Summary | Markdown mojibake can occur when files are read or written through mixed PowerShell and .NET encoding methods. |
| Observed fact | M1 work observed mojibake in markdown content, including corrupted display of milestone title separators in prior validation evidence. |
| Suspected root cause | Mixed encoding assumptions between shell display, file reads, file writes, and .NET helpers can reinterpret UTF-8 punctuation as different code points. |
| Confirmed root cause | Not confirmed for every file or command path. The mojibake itself is directly observed. |
| Workaround | Keep operational state updates ASCII-safe when special characters are not required. Prefer plain hyphen separators in BUILD_STATE and other high-churn operational text. |
| Confirmed fix | None during M1. |
| Verification expectation | Inspect actual file content after edits. For encoding-sensitive fixes, use byte or code-point evidence rather than display output alone. |
| Update targets | `.agent/skills/build-state-update/SKILL.md`, `docs/context/BUILD_STATE.md`, future dashboard encoding checks. |
| M1 boundary | Advisory/manual only; does not add automated encoding repair. |

### M1-ERROR-005: Special Characters In PowerShell Repair Commands

| Field | Value |
|---|---|
| Status | Observed |
| Area | PowerShell, encoding |
| Summary | Pasting special characters directly into PowerShell repair commands can cause parser or encoding failures. |
| Observed fact | M1 corrective work identified that direct use of special dash characters in PowerShell repair commands can fail or produce unreliable results. |
| Suspected root cause | Shell parsing, clipboard encoding, terminal display, and file encoding can disagree about non-ASCII punctuation. |
| Confirmed root cause | Not confirmed for every special character. The operational risk is confirmed enough to avoid direct paste repair commands during M1. |
| Workaround | Use ASCII-safe replacements in operational files when acceptable. When special characters are required, construct repairs with verified code points rather than visually pasted characters. |
| Confirmed fix | None during M1. |
| Verification expectation | Verify the exact resulting characters in the file, especially when replacing dashes, quotes, or other punctuation. |
| Update targets | `.agent/skills/build-state-update/SKILL.md`, `docs/context/BUILD_STATE.md`, future prompt guidance. |
| M1 boundary | Advisory/manual only; does not enable automated repair commands. |

### M1-ERROR-006: Successful Command Does Not Prove Successful Fix

| Field | Value |
|---|---|
| Status | Confirmed |
| Area | Validation, encoding, documentation |
| Summary | A command can appear to run successfully while verification still shows the issue. |
| Observed fact | M1 encoding repair attempts showed that command completion alone was not enough; validation still had to inspect actual file content and, when needed, byte or code-point evidence. |
| Suspected root cause | Commands may write unexpected bytes, operate on different text than intended, or succeed without changing the problematic content. |
| Confirmed root cause | Command success and content correctness are separate facts. Verification must inspect the affected content. |
| Workaround | For encoding-sensitive updates, inspect actual file content after the command. Use byte or code-point checks when display output is ambiguous. |
| Confirmed fix | None during M1. |
| Verification expectation | Report both the command result and the content verification result. Treat content verification as authoritative for encoding-sensitive work. |
| Update targets | `.agent/skills/build-state-update/SKILL.md`, `docs/governance/SELF_MANAGEMENT_MODEL.md`, `docs/prompts/CODEX_PROMPT_STANDARD.md`, future dashboard validation rules. |
| M1 boundary | Advisory/manual only; does not create automated validators. |

### M1-ERROR-007: ASCII-Safe Operational State Mitigation

| Field | Value |
|---|---|
| Status | Mitigated |
| Area | Build state, documentation, encoding |
| Summary | ASCII-safe milestone separators are the safest immediate mitigation for operational state files during M1. |
| Observed fact | M1 build-state and validation evidence included mojibake around long dash milestone separators. The safer immediate mitigation was to use ASCII-safe separators in operational state text. |
| Suspected root cause | Special punctuation in frequently edited operational docs increases encoding and display risk across tools. |
| Confirmed root cause | The special separator risk is confirmed by observed mojibake; the full encoding path is not fully confirmed. |
| Workaround | Use ASCII-safe separators such as `M1 - GitHub Operations Validation` in BUILD_STATE and other operational state text unless the exact official title is required. |
| Confirmed fix | None during M1. |
| Verification expectation | Review BUILD_STATE and operational state text after edits to confirm ASCII-safe separators remain in high-churn sections. |
| Update targets | `.agent/skills/build-state-update/SKILL.md`, `docs/context/BUILD_STATE.md`, future dashboard display-normalization rules. |
| M1 boundary | Advisory/manual only; does not change official GitHub milestone titles or enable automation. |

### M1-ERROR-008: Multiline `gh pr create --body` Argument Splitting In PowerShell

| Field | Value |
|---|---|
| Status | Observed |
| Area | GitHub CLI, PowerShell, PR evidence |
| Summary | Passing a multiline PR body variable directly to `gh pr create --body` can be split into unintended native command arguments when the body contains quoted command examples. |
| Observed fact | During issue #22, `gh pr create --draft --title ... --body $body ...` failed with `unknown arguments` and fragments of quoted label commands from the intended PR body. |
| Suspected root cause | Windows PowerShell native command argument passing can split or reinterpret complex multiline strings containing nested quotes when passed directly as a command argument. |
| Confirmed root cause | Not confirmed for every PowerShell or GitHub CLI version. The observed command did not preserve the intended body as a single argument. |
| Workaround | Prefer piping the PR body to `gh pr create --body-file -`, or use a carefully verified body file when multiline evidence includes quotes, backticks, or command examples. |
| Confirmed fix | None during M1. |
| Verification expectation | After PR creation, verify the PR body rendered with the intended evidence sections and command examples. |
| Update targets | `.agent/skills/github-operations/SKILL.md`, future PR creation prompt guidance, future dashboard GitHub-operation rules. |
| M1 boundary | Advisory/manual only; does not authorize autonomous PR creation or merge. |

### M1-ERROR-009: Hyphenated Marker `gh api --jq` Comment Checks In PowerShell

| Field | Value |
|---|---|
| Status | Observed |
| Area | GitHub CLI, PowerShell, issue comments, jq |
| Summary | `gh api --jq` marker checks can fail when marker strings contain hyphens and are not safely quoted or escaped for jq parsing. |
| Observed fact | During PR #29 human review, `gh api "repos/yoey2112/aresforge/issues/comments/4484336358" --jq '{id: .id, user: .user.login, html_url: .html_url, created_at: .created_at, updated_at: .updated_at, marker_present: (.body | contains("ARESFORGE-ISSUE-28-COMMENT-LIFECYCLE-VALIDATION"))}'` failed with `function not defined: VALIDATION/0`. |
| Suspected root cause | The jq expression or shell quoting path did not preserve the hyphenated marker string as intended before jq parsed it. |
| Confirmed root cause | Not confirmed for every PowerShell, GitHub CLI, or jq quoting path. The observed review command failed and the safer raw JSON parsing pattern succeeded. |
| Workaround | Use raw `gh api` output parsed with PowerShell `ConvertFrom-Json`, then use PowerShell string methods such as `.Contains($marker)` for marker checks. |
| Confirmed fix | None during M1. |
| Verification expectation | Verify comment ID, author, URL, timestamps, and marker presence after parsing the returned JSON. |
| Update targets | `.agent/skills/github-operations/SKILL.md`, `docs/validation/GITHUB_CAPABILITY_VALIDATION.md`, `docs/context/BUILD_STATE.md`, future dashboard GitHub-operation rules. |
| M1 boundary | Advisory/manual only; does not authorize comment automation. |

## M1 Boundary

This document is a manual learning layer for M1. It may be cited by prompts, skills, validation evidence, governance docs, and future dashboard design notes, but it does not execute checks, repair files, update issues, approve PRs, merge work, close issues, or authorize future automation.
