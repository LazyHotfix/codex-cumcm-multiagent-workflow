# Local CUMCM smoke tests

[CmdletBinding()]
param(
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = "Stop"
$failures = [System.Collections.Generic.List[string]]::new()
$warnings = [System.Collections.Generic.List[string]]::new()

function Assert-True([bool]$Condition, [string]$Message) {
    if (-not $Condition) {
        $failures.Add($Message)
    }
}

$expected = @(
    "00-cumcm-orchestrator",
    "01-cumcm-doctor",
    "02-cumcm-brainstorm",
    "03-cumcm-project-start",
    "04-cumcm-modeling",
    "05-cumcm-coding-visual",
    "06-cumcm-result-mvp",
    "07-cumcm-drawio",
    "08-cumcm-template",
    "09-cumcm-writing",
    "10-cumcm-latex",
    "11-cumcm-verify",
    "12-cumcm-docx",
    "13-cumcm-paper-review"
)
$contractFields = @(
    "phase_id", "display_name", "owner_agent", "entry_conditions", "inputs",
    "outputs", "exit_conditions", "failure_return", "writable_paths",
    "read_only_paths", "invalidates", "user_gate"
)

$skillsRoot = Join-Path $ProjectRoot "skills"
foreach ($name in $expected) {
    $dir = Join-Path $skillsRoot $name
    Assert-True (Test-Path -LiteralPath $dir -PathType Container) "missing skill directory: $name"
    foreach ($child in @("agents", "references", "scripts")) {
        Assert-True (Test-Path -LiteralPath (Join-Path $dir $child) -PathType Container) "$name missing $child directory"
    }

    $skillFile = Join-Path $dir "SKILL.md"
    Assert-True (Test-Path -LiteralPath $skillFile -PathType Leaf) "$name missing SKILL.md"
    if (Test-Path -LiteralPath $skillFile) {
        $text = Get-Content -LiteralPath $skillFile -Raw -Encoding utf8
        Assert-True ($text -match "(?m)^name:\s*$name\s*$") "$name frontmatter name mismatch"
        foreach ($field in $contractFields) {
            Assert-True ($text.Contains($field)) "$name missing contract field: $field"
        }
    }

    $agentFile = Join-Path $dir "agents\openai.yaml"
    Assert-True (Test-Path -LiteralPath $agentFile -PathType Leaf) "$name missing agents/openai.yaml"
    if (Test-Path -LiteralPath $agentFile) {
        $agentText = Get-Content -LiteralPath $agentFile -Raw -Encoding utf8
        Assert-True (-not $agentText.Contains([char]0xfffd)) "$name agent config contains replacement characters"
        foreach ($field in @("display_name:", "short_description:", "default_prompt:")) {
            Assert-True ($agentText.Contains($field)) "$name agent config missing $field"
        }
    }
}

$registryPath = Join-Path $ProjectRoot "shared\PHASE_REGISTRY.json"
$stateExamplePath = Join-Path $ProjectRoot "orchestrator\STATE_EXAMPLE.json"
Assert-True (Test-Path -LiteralPath $registryPath -PathType Leaf) "missing phase registry"
Assert-True (Test-Path -LiteralPath $stateExamplePath -PathType Leaf) "missing state example"
if ((Test-Path -LiteralPath $registryPath) -and (Test-Path -LiteralPath $stateExamplePath)) {
    $registry = Get-Content -LiteralPath $registryPath -Raw -Encoding utf8 | ConvertFrom-Json
    $state = Get-Content -LiteralPath $stateExamplePath -Raw -Encoding utf8 | ConvertFrom-Json
    Assert-True ($registry.workflow_id -eq "cumcm-local-multi-agent") "registry workflow_id mismatch"
    Assert-True ($registry.phases.Count -eq 15) "registry should contain 15 phases including G1/G2"
    Assert-True ($state.workflow_id -eq $registry.workflow_id) "state example workflow_id mismatch"
    Assert-True ($state.g1.input_hash -ne $null -and $state.g2.input_hash -ne $null) "gate input_hash missing from state example"
    $badWindow = $registry.parallel_windows | Where-Object {
        ($_ -contains "07-cumcm-drawio") -and ($_ -contains "10-cumcm-latex")
    }
    Assert-True (-not $badWindow) "drawio and latex must not be declared parallel"
}

foreach ($path in @(
    "scripts\init_workflow_state.py",
    "scripts\validate_workflow_state.py",
    "scripts\validate_skill_layout.py",
    "scripts\manage_write_lock.py",
    "scripts\update_gate.py",
    "scripts\propagate_invalidation.py",
    "shared\WORKFLOW_STATE.schema.json",
    "shared\PHASE_REGISTRY.json"
)) {
    Assert-True (Test-Path -LiteralPath (Join-Path $ProjectRoot $path) -PathType Leaf) "missing control-plane file: $path"
}

$pythonCandidates = @(
    (Get-Command python -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue),
    (Get-Command python3 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue),
    (Get-Command py -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue)
) | Where-Object { $_ -and (Test-Path -LiteralPath $_) }
$selectedPython = $null
foreach ($candidate in $pythonCandidates) {
    & $candidate --version *> $null
    if ($LASTEXITCODE -eq 0) {
        $selectedPython = $candidate
        break
    }
}
if (-not $selectedPython) {
    $warnings.Add("no functional Python interpreter found; Python control scripts were not executed")
} else {
    & $selectedPython (Join-Path $ProjectRoot "scripts\validate_skill_layout.py") --root $ProjectRoot
    if ($LASTEXITCODE -ne 0) {
        $failures.Add("validate_skill_layout.py failed")
    }
    $quickValidate = $env:QUICK_VALIDATE
    if ($quickValidate -and (Test-Path -LiteralPath $quickValidate)) {
        $env:PYTHONUTF8 = "1"
        $quickPython = $null
        foreach ($candidate in $pythonCandidates) {
            & $candidate -c "import yaml" *> $null
            if ($LASTEXITCODE -eq 0) {
                $quickPython = $candidate
                break
            }
        }
        if ($quickPython) {
            $quickFailed = 0
            Get-ChildItem -LiteralPath $skillsRoot -Directory | ForEach-Object {
                & $quickPython $quickValidate $_.FullName *> $null
                if ($LASTEXITCODE -ne 0) { $quickFailed++ }
            }
            if ($quickFailed -gt 0) {
                $failures.Add("official quick_validate.py failed for $quickFailed skill(s)")
            }
        } else {
            $warnings.Add("no Python interpreter with PyYAML found; official quick_validate.py was not executed")
        }
    }
}

if ($failures.Count -gt 0) {
    Write-Output "[FAIL] $($failures.Count) smoke-test failure(s)"
    $failures | ForEach-Object { Write-Output "- $_" }
    $warnings | ForEach-Object { Write-Output "[WARN] $_" }
    exit 1
}

Write-Output "[PASS] local CUMCM smoke tests passed"
Write-Output "skills_checked=$($expected.Count)"
$warnings | ForEach-Object { Write-Output "[WARN] $_" }
exit 0
