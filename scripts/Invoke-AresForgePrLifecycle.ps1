[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet(
        "ValidateWorkingBranch",
        "StageCommitPush",
        "CreatePr",
        "VerifyPr",
        "MergePr",
        "PostMergeVerify",
        "SourceTruthScan"
    )]
    [string]$Phase,

    [string]$RepoPath = "C:\Projects\aresforge",
    [string]$Repo = "yoey2112/aresforge",
    [int]$IssueNumber,
    [int]$PrNumber,
    [string]$BranchName,
    [string]$CommitMessage,
    [string]$PrTitle,
    [string]$PrBodyPath,
    [string[]]$FilesToStage,
    [string]$FilesToStagePath,
    [string[]]$ExtraValidationCommand,
    [switch]$IncludeDatabaseValidation,
    [switch]$AllowUntracked
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Write-Section {
    param([Parameter(Mandatory = $true)][string]$Title)
    Write-Host ""
    Write-Host "=== $Title ==="
}

function Resolve-AbsolutePath {
    param([Parameter(Mandatory = $true)][string]$Path)

    $resolved = Resolve-Path -LiteralPath $Path
    return $resolved.ProviderPath
}

function Get-RepoRelativePath {
    param([Parameter(Mandatory = $true)][string]$Path)

    $absolutePath = Resolve-AbsolutePath -Path $Path
    $relativePath = Resolve-Path -LiteralPath $absolutePath -Relative
    if ($relativePath.StartsWith(".\")) {
        return $relativePath.Substring(2)
    }

    if ($relativePath.StartsWith("./")) {
        return $relativePath.Substring(2)
    }

    return $relativePath
}

function Invoke-CheckedCommand {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [string[]]$ArgumentList = @()
    )

    $display = @($FilePath) + $ArgumentList
    Write-Host ">> $($display -join ' ')"
    & $FilePath @ArgumentList
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $($display -join ' ')"
    }
}

function Invoke-CheckedPowerShellCommand {
    param([Parameter(Mandatory = $true)][string]$Command)

    Write-Host ">> powershell -NoProfile -ExecutionPolicy Bypass -Command $Command"
    & powershell -NoProfile -ExecutionPolicy Bypass -Command $Command
    if ($LASTEXITCODE -ne 0) {
        throw "PowerShell command failed with exit code ${LASTEXITCODE}: $Command"
    }
}

function Get-CurrentBranchName {
    $branch = (git branch --show-current).Trim()
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to determine the current branch."
    }
    if (-not $branch) {
        throw "Unable to determine the current branch."
    }

    return $branch
}

function Get-LatestCommitSummary {
    $summary = (git log -1 --oneline).Trim()
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to determine the latest commit summary."
    }

    return $summary
}

function Show-WorkingTreeSummary {
    Write-Section "Working Tree Summary"
    Write-Host "Repository path: $(Get-Location)"
    Write-Host "Current branch: $(Get-CurrentBranchName)"
    Write-Host "Latest commit: $(Get-LatestCommitSummary)"
    Invoke-CheckedCommand -FilePath "git" -ArgumentList @("status", "--short", "--branch")
}

function Invoke-DiffSafetyChecks {
    Write-Section "Diff Safety Checks"
    Invoke-CheckedCommand -FilePath "git" -ArgumentList @("diff", "--check")
    Invoke-CheckedCommand -FilePath "git" -ArgumentList @("diff", "--cached", "--check")
}

function Assert-NotOnMainBranch {
    $currentBranch = Get-CurrentBranchName
    if ($currentBranch -eq "main") {
        throw "This phase refuses to run on 'main'. Create or switch to a working branch first."
    }
}

function Assert-BranchMatches {
    param([Parameter(Mandatory = $true)][string]$ExpectedBranch)

    $currentBranch = Get-CurrentBranchName
    if ($currentBranch -ne $ExpectedBranch) {
        throw "Current branch '$currentBranch' does not match expected branch '$ExpectedBranch'."
    }
}

function Assert-NoUnexpectedUntrackedFiles {
    param([string[]]$AllowedUntrackedPaths = @())

    if ($AllowUntracked.IsPresent) {
        Write-Host "AllowUntracked was supplied. Skipping untracked-file refusal check."
        return
    }

    $untracked = git ls-files --others --exclude-standard
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to determine untracked files."
    }

    $ignoredUntrackedPaths = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    if (-not [string]::IsNullOrWhiteSpace($FilesToStagePath)) {
        $repoRelativeStageListPath = Get-RepoRelativePath -Path $FilesToStagePath
        [void]$ignoredUntrackedPaths.Add($repoRelativeStageListPath.Replace("\", "/"))
        [void]$ignoredUntrackedPaths.Add($repoRelativeStageListPath.Replace("/", "\"))
    }

    foreach ($path in @($AllowedUntrackedPaths)) {
        if ([string]::IsNullOrWhiteSpace($path)) {
            continue
        }

        [void]$ignoredUntrackedPaths.Add($path.Trim().Replace("\", "/"))
        [void]$ignoredUntrackedPaths.Add($path.Trim().Replace("/", "\"))
    }

    $untrackedList = @(
        $untracked |
            Where-Object { $_ -and $_.Trim() } |
            Where-Object { -not $ignoredUntrackedPaths.Contains($_.Trim()) }
    )
    if ($untrackedList.Count -gt 0) {
        throw "Unexpected untracked files detected:`n$($untrackedList -join "`n")`nRe-run with -AllowUntracked if this is intentional."
    }
}

function Assert-ProtectedIssueBoundary {
    if ($IssueNumber -eq 39 -and $Phase -in @("CreatePr", "MergePr")) {
        throw "Issue #39 is protected audit evidence. This helper will not create or merge PR lifecycle actions scoped to it."
    }
}

function Assert-RequiredValues {
    param(
        [Parameter(Mandatory = $true)][string[]]$Names
    )

    foreach ($name in $Names) {
        $value = Get-Variable -Name $name -ValueOnly -ErrorAction Stop
        if ($null -eq $value) {
            throw "Parameter '$name' is required for phase '$Phase'."
        }

        if ($value -is [string] -and [string]::IsNullOrWhiteSpace($value)) {
            throw "Parameter '$name' is required for phase '$Phase'."
        }

        if ($value -is [System.Array] -and $value.Count -eq 0) {
            throw "Parameter '$name' is required for phase '$Phase'."
        }
    }
}

function Get-PrView {
    param([Parameter(Mandatory = $true)][int]$Number)

    $json = gh pr view $Number --repo $Repo --json number,title,state,isDraft,mergeStateStatus,baseRefName,headRefName,url
    if ($LASTEXITCODE -ne 0) {
        throw "gh pr view failed for PR #$Number."
    }

    return $json | ConvertFrom-Json
}

function Get-EffectiveFilesToStage {
    $effectiveFiles = [System.Collections.Generic.List[string]]::new()
    $seenFiles = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)

    foreach ($file in @($FilesToStage)) {
        if ([string]::IsNullOrWhiteSpace($file)) {
            continue
        }

        $trimmedFile = $file.Trim()
        if ($seenFiles.Add($trimmedFile)) {
            $effectiveFiles.Add($trimmedFile)
        }
    }

    if (-not [string]::IsNullOrWhiteSpace($FilesToStagePath)) {
        $resolvedStageListPath = Resolve-AbsolutePath -Path $FilesToStagePath
        foreach ($line in Get-Content -LiteralPath $resolvedStageListPath) {
            if ([string]::IsNullOrWhiteSpace($line)) {
                continue
            }

            $trimmedLine = $line.Trim()
            if ($trimmedLine.StartsWith("#")) {
                continue
            }

            if ($seenFiles.Add($trimmedLine)) {
                $effectiveFiles.Add($trimmedLine)
            }
        }
    }

    return @($effectiveFiles)
}

function Show-PrSummary {
    param([Parameter(Mandatory = $true)]$Pr)

    Write-Section "PR Summary"
    $Pr | Select-Object number, title, state, isDraft, mergeStateStatus, baseRefName, headRefName, url | Format-List
}

function Show-OpenGitHubState {
    Write-Section "Open Pull Requests"
    $prListJson = gh pr list --repo $Repo --state open --json number,title,headRefName,url
    if ($LASTEXITCODE -ne 0) {
        throw "gh pr list failed."
    }

    $prList = $prListJson | ConvertFrom-Json
    if ($prList.Count -eq 0) {
        Write-Host "No open PRs."
    }
    else {
        $prList | Select-Object number, title, headRefName, url | Format-Table -AutoSize
    }

    Write-Section "Open Issues"
    $issueListJson = gh issue list --repo $Repo --state open --json number,title,url
    if ($LASTEXITCODE -ne 0) {
        throw "gh issue list failed."
    }

    $issueList = $issueListJson | ConvertFrom-Json
    if ($issueList.Count -eq 0) {
        Write-Host "No open issues."
    }
    else {
        $issueList | Select-Object number, title, url | Format-Table -AutoSize
    }
}

function Invoke-ValidateWorkingBranchPhase {
    Show-WorkingTreeSummary

    Write-Section "Validation Commands"
    Invoke-CheckedCommand -FilePath ".\.venv\Scripts\python.exe" -ArgumentList @("-m", "pytest")
    Invoke-CheckedCommand -FilePath ".\.venv\Scripts\python.exe" -ArgumentList @("-m", "aresforge", "--help")
    Invoke-CheckedCommand -FilePath ".\.venv\Scripts\python.exe" -ArgumentList @("-m", "aresforge", "validate-config")
    Invoke-CheckedCommand -FilePath ".\.venv\Scripts\python.exe" -ArgumentList @("-m", "aresforge", "validate-registries")
    Invoke-CheckedCommand -FilePath ".\.venv\Scripts\python.exe" -ArgumentList @("-m", "aresforge", "migrate", "--plan")

    if ($IncludeDatabaseValidation.IsPresent) {
        Invoke-CheckedCommand -FilePath ".\.venv\Scripts\python.exe" -ArgumentList @("-m", "aresforge", "migrate")
    }

    foreach ($command in @($ExtraValidationCommand)) {
        if (-not [string]::IsNullOrWhiteSpace($command)) {
            Invoke-CheckedPowerShellCommand -Command $command
        }
    }

    Invoke-DiffSafetyChecks

    Write-Section "Final Status"
    Invoke-CheckedCommand -FilePath "git" -ArgumentList @("status", "--short", "--branch")
}

function Invoke-StageCommitPushPhase {
    Assert-RequiredValues -Names @("BranchName", "CommitMessage")
    Assert-NotOnMainBranch
    Assert-BranchMatches -ExpectedBranch $BranchName

    $effectiveFilesToStage = @(Get-EffectiveFilesToStage)
    if ($effectiveFilesToStage.Count -eq 0) {
        throw "StageCommitPush requires at least one staging file from -FilesToStage or -FilesToStagePath."
    }

    Assert-NoUnexpectedUntrackedFiles -AllowedUntrackedPaths $effectiveFilesToStage

    Show-WorkingTreeSummary

    Write-Section "Stage Files"
    $gitAddArguments = @("add") + $effectiveFilesToStage
    Invoke-CheckedCommand -FilePath "git" -ArgumentList $gitAddArguments

    Invoke-DiffSafetyChecks

    Write-Section "Staged Diff Stat"
    Invoke-CheckedCommand -FilePath "git" -ArgumentList @("diff", "--cached", "--stat")

    Write-Section "Commit"
    Invoke-CheckedCommand -FilePath "git" -ArgumentList @("commit", "-m", $CommitMessage)

    Write-Section "Push"
    Invoke-CheckedCommand -FilePath "git" -ArgumentList @("push", "-u", "origin", $BranchName)

    Write-Section "Final Status"
    Show-WorkingTreeSummary
}

function Invoke-CreatePrPhase {
    Assert-RequiredValues -Names @("BranchName", "PrTitle", "PrBodyPath")
    Assert-BranchMatches -ExpectedBranch $BranchName

    $resolvedPrBodyPath = Resolve-AbsolutePath -Path $PrBodyPath

    Write-Section "Create PR"
    Write-Host "PR body path: $resolvedPrBodyPath"
    $prCreateOutput = gh pr create --repo $Repo --base main --head $BranchName --title $PrTitle --body-file $resolvedPrBodyPath
    if ($LASTEXITCODE -ne 0) {
        throw "gh pr create failed."
    }

    Write-Host $prCreateOutput
}

function Invoke-VerifyPrPhase {
    Assert-RequiredValues -Names @("PrNumber")

    Show-WorkingTreeSummary

    $pr = Get-PrView -Number $PrNumber
    Show-PrSummary -Pr $pr

    Write-Section "PR Changed Files"
    Invoke-CheckedCommand -FilePath "gh" -ArgumentList @("pr", "diff", $PrNumber.ToString(), "--repo", $Repo, "--name-only")

    Show-OpenGitHubState
}

function Invoke-MergePrPhase {
    Assert-RequiredValues -Names @("PrNumber")

    $pr = Get-PrView -Number $PrNumber
    Show-PrSummary -Pr $pr

    if ($pr.mergeStateStatus -ne "CLEAN") {
        throw "PR #$PrNumber is not mergeable. mergeStateStatus is '$($pr.mergeStateStatus)', expected 'CLEAN'."
    }

    if ($pr.state -ne "OPEN") {
        throw "PR #$PrNumber is not open. Current state is '$($pr.state)'."
    }

    Write-Section "Merge PR"
    Invoke-CheckedCommand -FilePath "gh" -ArgumentList @("pr", "merge", $PrNumber.ToString(), "--repo", $Repo, "--squash", "--delete-branch")
}

function Invoke-PostMergeVerifyPhase {
    Write-Section "Switch To Main"
    Invoke-CheckedCommand -FilePath "git" -ArgumentList @("checkout", "main")
    Invoke-CheckedCommand -FilePath "git" -ArgumentList @("pull", "--ff-only", "origin", "main")

    Show-WorkingTreeSummary

    if ($PrNumber) {
        $pr = Get-PrView -Number $PrNumber
        Show-PrSummary -Pr $pr
    }

    Show-OpenGitHubState
}

function Invoke-SourceTruthScanPhase {
    $scanFiles = @(
        "docs/context/BUILD_STATE.md",
        "docs/context/AGENT_CONTEXT.md",
        "docs/roadmap/ROADMAP.md"
    )

    $scanPatterns = [System.Collections.Generic.List[string]]::new()
    $scanPatterns.Add((Get-CurrentBranchName))
    $scanPatterns.Add("current-branch")
    $scanPatterns.Add("on the current branch")
    $scanPatterns.Add("Latest main commit")
    $scanPatterns.Add("Latest runtime-affecting merged foundation commit")

    if ($BranchName) {
        $scanPatterns.Add($BranchName)
    }

    if ($IssueNumber) {
        $scanPatterns.Add("Issue #$IssueNumber")
    }

    if ($PrNumber) {
        $scanPatterns.Add("PR #$PrNumber")
    }

    Write-Section "Source Truth Scan"
    Write-Host "Scanning files:"
    foreach ($file in $scanFiles) {
        Write-Host "- $file"
    }

    Write-Host "Patterns:"
    foreach ($pattern in $scanPatterns) {
        Write-Host "- $pattern"
    }

    $findings = @()
    foreach ($file in $scanFiles) {
        foreach ($pattern in $scanPatterns | Select-Object -Unique) {
            $matches = Select-String -Path $file -SimpleMatch -Pattern $pattern
            foreach ($match in $matches) {
                $findings += [PSCustomObject]@{
                    File = $match.Path
                    Line = $match.LineNumber
                    Pattern = $pattern
                    Text = $match.Line.Trim()
                }
            }
        }
    }

    if ($findings.Count -eq 0) {
        Write-Host "No matching source-of-truth references found."
        return
    }

    $findings | Sort-Object File, Line, Pattern | Format-Table -AutoSize
}

$resolvedRepoPath = Resolve-AbsolutePath -Path $RepoPath
Set-Location -Path $resolvedRepoPath

Assert-ProtectedIssueBoundary

switch ($Phase) {
    "ValidateWorkingBranch" { Invoke-ValidateWorkingBranchPhase }
    "StageCommitPush" { Invoke-StageCommitPushPhase }
    "CreatePr" { Invoke-CreatePrPhase }
    "VerifyPr" { Invoke-VerifyPrPhase }
    "MergePr" { Invoke-MergePrPhase }
    "PostMergeVerify" { Invoke-PostMergeVerifyPhase }
    "SourceTruthScan" { Invoke-SourceTruthScanPhase }
    default { throw "Unsupported phase '$Phase'." }
}
