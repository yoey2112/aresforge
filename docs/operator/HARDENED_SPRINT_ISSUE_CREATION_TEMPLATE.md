# Hardened Sprint Issue Creation Template

## Purpose

This template defines the canonical human-run pattern for creating sprint parent/child issue sets without partial creation drift or blank parent-child references.

This is an operator standard, not autonomous automation.

For structured local definition generation, use:

- `python -m aresforge generate-sprint-issue-script --definition <definition.json>`

Contract details are defined in:

- `docs/architecture/STRUCTURED_SPRINT_ISSUE_DEFINITION_CONTRACT.md`

## Safety Boundary

- Human-triggered only.
- Read-only checks first; mutate GitHub only after preflight passes.
- No automatic labeling.
- No automatic milestone assignment.
- No automatic issue closeout.
- No automatic PR merge.
- Issue #39 remains retired historical validation evidence only and must not be used as active scope.

## Required Contract

1. Define all child issues in one in-memory issue definition array.
2. Generate one body file per declared child definition.
3. Preflight-validate every declared body path exists and is non-empty.
4. Create child issues and validate returned URLs before parsing numbers.
5. Fail immediately on blank/null URL or parse failure.
6. Do not update the parent issue until all expected child issue numbers are known.
7. Run final verification before cleanup.
8. Delete temporary artifacts only after final verification passes.

## PowerShell Template (Operator-Run Pattern)

```powershell
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Repo = "yoey2112/aresforge"
$ParentIssueNumber = 172
$SprintId = "M7"
$TempRoot = Join-Path $PWD ".tmp/sprint-issue-create-$SprintId"
$BodiesRoot = Join-Path $TempRoot "bodies"

function Throw-IfBlank {
    param(
        [string]$Value,
        [string]$Message
    )
    if ([string]::IsNullOrWhiteSpace($Value)) {
        throw $Message
    }
}

function Assert-BodyFile {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Missing issue body file: $Path"
    }
    $item = Get-Item -LiteralPath $Path
    if ($item.Length -le 0) {
        throw "Empty issue body file: $Path"
    }
}

function Parse-IssueNumberFromUrl {
    param([string]$IssueUrl)
    Throw-IfBlank -Value $IssueUrl -Message "Issue creation returned blank URL."
    if ($IssueUrl -notmatch "/issues/(\d+)$") {
        throw "Failed to parse issue number from URL: $IssueUrl"
    }
    return [int]$Matches[1]
}

New-Item -ItemType Directory -Path $BodiesRoot -Force | Out-Null

$IssueDefinitions = @(
    [pscustomobject]@{
        Key = "dashboard-shell"
        Title = "M7: Dashboard shell and route scaffolding"
        BodyPath = Join-Path $BodiesRoot "m7-dashboard-shell.md"
        Body = @"
## Summary
- Implement the dashboard shell and route scaffolding.

## Scope
- Add shell layout.
- Add top-level dashboard route.

## Validation
- python -m pytest
- python -m aresforge inspect-repo-governance
"@
    },
    [pscustomobject]@{
        Key = "dashboard-data-contract"
        Title = "M7: Dashboard data contract and read-only surface"
        BodyPath = Join-Path $BodiesRoot "m7-dashboard-data-contract.md"
        Body = @"
## Summary
- Define dashboard data contract and read-only data surface.

## Scope
- Define response model.
- Add read-only retrieval path.

## Validation
- python -m pytest
- python -m aresforge inspect-repo-governance
"@
    }
)

if ($IssueDefinitions.Count -lt 1) {
    throw "Issue definition array cannot be empty."
}

# Body generation gate: every declared body path must be written.
foreach ($def in $IssueDefinitions) {
    Throw-IfBlank -Value $def.Title -Message "Issue title missing for key '$($def.Key)'."
    Throw-IfBlank -Value $def.BodyPath -Message "Issue body path missing for key '$($def.Key)'."
    Throw-IfBlank -Value $def.Body -Message "Issue body content missing for key '$($def.Key)'."
    Set-Content -LiteralPath $def.BodyPath -Value $def.Body -NoNewline -Encoding utf8
}

# Preflight gate: every declared body file must exist and be non-empty.
foreach ($def in $IssueDefinitions) {
    Assert-BodyFile -Path $def.BodyPath
}

$CreatedChildren = @()
foreach ($def in $IssueDefinitions) {
    $url = gh issue create --repo $Repo --title $def.Title --body-file $def.BodyPath
    $number = Parse-IssueNumberFromUrl -IssueUrl $url
    $CreatedChildren += [pscustomobject]@{
        Key = $def.Key
        Title = $def.Title
        Url = $url
        Number = $number
    }
}

# Parent update gate: block until every expected child number is known.
if ($CreatedChildren.Count -ne $IssueDefinitions.Count) {
    throw "Child issue count mismatch. Expected $($IssueDefinitions.Count), got $($CreatedChildren.Count). Parent issue update is blocked."
}
if (($CreatedChildren | Where-Object { $_.Number -le 0 }).Count -gt 0) {
    throw "One or more child issue numbers are invalid. Parent issue update is blocked."
}

$checklist = ($CreatedChildren | ForEach-Object { "- [ ] #$($_.Number) $($_.Title)" }) -join [Environment]::NewLine
$parentBodyPath = Join-Path $BodiesRoot "parent-$ParentIssueNumber-update.md"
$parentBody = @"
## $SprintId Workstreams
$checklist
"@
Set-Content -LiteralPath $parentBodyPath -Value $parentBody -NoNewline -Encoding utf8
Assert-BodyFile -Path $parentBodyPath

gh issue edit $ParentIssueNumber --repo $Repo --body-file $parentBodyPath | Out-Null

# Final verification gate before cleanup.
foreach ($child in $CreatedChildren) {
    $view = gh issue view $child.Number --repo $Repo --json number,title,url,state
    Throw-IfBlank -Value $view -Message "Verification payload missing for child issue #$($child.Number)."
}
$parentView = gh issue view $ParentIssueNumber --repo $Repo --json number,title,url,state
Throw-IfBlank -Value $parentView -Message "Verification payload missing for parent issue #$ParentIssueNumber."

Remove-Item -LiteralPath $TempRoot -Recurse -Force
Write-Host "Sprint issue creation completed with hardened gates."
```

## Operator Checklist

1. Confirm protected scope exclusions, including Issue #39.
2. Build the full issue definition array first.
3. Write all body files.
4. Run body-file preflight validation.
5. Create each child and validate URL-to-number parsing.
6. Confirm all expected child numbers are present.
7. Update parent issue only after child-number completeness gate passes.
8. Run final issue-view verification for parent and all children.
9. Clean up temporary artifacts only after verification success.

## Failure Handling

- If any body file is missing or empty, stop immediately and fix generation before any further mutation.
- If issue URL parsing fails or returns blank, stop immediately; do not continue child creation or parent update.
- If child counts mismatch expected definitions, stop immediately and block parent update.
- If final verification fails, preserve local artifacts for operator inspection and rerun only after correction.
