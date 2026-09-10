#requires -Version 5.1
<#
.SYNOPSIS
  Model discovery and bounded nightly benchmarks. Requires Python 3.10+; no pip packages.
.EXAMPLE
  .\bench.ps1 -Discover
.EXAMPLE
  .\bench.ps1 -ValidateCandidate .\state\selection.json
.EXAMPLE
  .\bench.ps1 -RunCandidate .\state\selection.json
.NOTES
  Resource limits and publisher rules live in policy.json. Generated code is never executed.
#>
[CmdletBinding(DefaultParameterSetName='Discover')]
param(
    [Parameter(ParameterSetName='Discover')][switch]$Discover,
    [Parameter(ParameterSetName='Pending',Mandatory=$true)][switch]$Pending,
    [Parameter(ParameterSetName='Validate',Mandatory=$true)][string]$ValidateCandidate,
    [Parameter(ParameterSetName='Run',Mandatory=$true)][string]$RunCandidate,
    [Parameter(ParameterSetName='Status',Mandatory=$true)][string]$StatusRun,
    [Parameter(ParameterSetName='Wait',Mandatory=$true)][string]$WaitRun,
    [Parameter(ParameterSetName='Benchmark',Mandatory=$true)][string]$Benchmark,
    [ValidateRange(1,100)][int]$TopN=25,
    [ValidateRange(1,100)][int]$DetailLookupCap=100
)
$ErrorActionPreference='Stop'
$pythonCandidates = @($env:NIGHTLY_BENCH_PYTHON,
    [Environment]::GetEnvironmentVariable('NIGHTLY_BENCH_PYTHON','User'),
    (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python314\python.exe'),
    (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python313\python.exe'),
    (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'))
$pythonCommand=Get-Command python.exe -ErrorAction SilentlyContinue
if ($pythonCommand -and $pythonCommand.Source -notmatch '\\WindowsApps\\') { $pythonCandidates += $pythonCommand.Source }
$pythonCandidates += (Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe')
$pythonPath=$pythonCandidates | Where-Object { $_ -and (Test-Path -LiteralPath $_ -PathType Leaf) } | Select-Object -First 1
if (-not $pythonPath) { throw 'Python 3.10+ not found. Set NIGHTLY_BENCH_PYTHON to an existing interpreter; this task never installs software.' }
$cliArgs=@((Join-Path $PSScriptRoot 'nightly.py'))
switch ($PSCmdlet.ParameterSetName) {
    'Pending' { $cliArgs += '--pending' }
    'Validate' { $cliArgs += @('--validate-candidate',$ValidateCandidate) }
    'Run' { $cliArgs += @('--launch-candidate',$RunCandidate) }
    'Status' { $cliArgs += @('--status-run',$StatusRun) }
    'Wait' { $cliArgs += @('--wait-run',$WaitRun) }
    'Benchmark' { $cliArgs += @('--benchmark',$Benchmark) }
    default { $cliArgs += @('--discover','--top-n',"$TopN",'--detail-cap',"$DetailLookupCap") }
}
& $pythonPath @cliArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
