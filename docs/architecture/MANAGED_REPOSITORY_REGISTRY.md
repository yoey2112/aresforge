# Managed Repository Registry

## Purpose

This document defines the minimal M3 managed repository registry extension.

The goal is to let AresForge represent multiple managed repositories in a reusable read-only model, while keeping the current AresForge repository as the first default managed repository.

## Command Surface

- `python -m aresforge inspect-managed-repos`
- `python -m aresforge managed-repo-readiness-report`
- `python -m aresforge plan-repo-bootstrap`
- `python -m aresforge demo-managed-repo-governance`

This command is human-triggered, read-only, deterministic JSON output, and safe to run repeatedly.

## Registry Scope

The managed repository registry currently supports these fields per repository:

- repository slug
- local path where available
- default branch
- project key
- repo role
- governance profile
- automation status
- bootstrap status
- documentation roots
- artifact roots
- allowed automation capabilities
- disabled status
- archived status

## Default Repository Record

The configured AresForge repository (`ARESFORGE_GITHUB_OWNER` + `ARESFORGE_GITHUB_REPO`) is always included as the first/default managed repository.

This preserves current behavior while enabling additional managed repositories to be represented without changing command semantics.

## Optional Registry File

If present, `config/managed_repositories.json` may define additional repository records:

```json
{
  "managed_repositories": [
    {
      "repository_slug": "example-org/example-repo",
      "local_path": "D:/ManagedRepos/example-repo",
      "default_branch": "main",
      "project_key": "project-example",
      "repo_role": "managed_external",
      "governance_profile": "aresforge-default",
      "documentation_roots": ["docs/"],
      "artifact_roots": ["artifacts/evidence/generated/"],
      "allowed_automation_capabilities": ["read_only_inspection"],
      "disabled": false,
      "archived": false
    }
  ]
}
```

Current M4 fixture example:

- `repository_slug`: `yoey2112/aresforge-demo-managed-repo`
- `project_key`: `project-aresforge-demo`
- `repo_role`: `demo_managed_repository`
- `local_path`: `C:/Projects/aresforge-demo-managed-repo`
- `automation_status`: `fixture_read_only`
- `bootstrap_status`: `fixture_only`
- `allowed_automation_capabilities`: `human_triggered_validation`, `read_only_inspection`

Fixture/demo records are inspection-only and must not imply live setup or mutation.

When this file is missing, malformed, or incomplete, the command degrades gracefully and still returns the default managed repository record plus warnings.

## Status Evaluation

Each repository entry includes:

- `automation_status`
- `bootstrap_status`
- `warnings`

Status values are derived from reusable read-only governance and bootstrap contract inspection surfaces. No setup mutation is performed.

For the default AresForge managed repository, labels and canonical platform milestones are now aligned through human-triggered manual setup. Current readiness posture may still report `attention_needed` while legacy or project-specific milestone mapping remains advisory and documentation-alignment-only.

Current AresForge legacy milestone mapping guidance:

- `M0 - Self-Bootstrap Foundation` maps to `M0 - Foundation`
- `M1 - GitHub Operations Validation` maps to `M1 - Validation`
- `M2 - Documentation Automation` maps to `M2 - Local Automation Foundation`
- `validation: issue-26-milestone-lifecycle` maps to `M1 - Validation`

## Safety Boundaries

This extension does not authorize:

- file mutation
- GitHub mutation
- autonomous queue or routing mutation
- background schedulers, daemons, or polling loops
- autonomous merge, closeout, or approval

Setup command execution is also out of scope for this registry extension. It represents managed repositories and reports posture only.

Issue 39 remains retired historical validation evidence only.

## Extension Direction

This M3 extension is intentionally minimal. It now provides a stable registry shape that is consumed by:

- managed repository readiness reporting
- bootstrap plan generation
- multi-repository governance demos
- end-to-end managed repository governance demo reporting

Future work may expand registry-backed selection and richer per-repository policies while preserving read-only defaults and explicit human-triggered mutation gates.
