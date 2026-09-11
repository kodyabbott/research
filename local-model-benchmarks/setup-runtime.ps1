#requires -Version 5.1
<# Human-invoked setup only. The scheduled task must never run this installer. #>
[CmdletBinding()]
param([Parameter(Mandatory=$true)][switch]$Install)
$ErrorActionPreference='Stop'
if (-not $Install) { throw 'Use -Install only after the user authorizes runtime installation.' }
$runtimeVersion='3.14.7'
$installerUrl='https://www.python.org/ftp/python/3.14.7/python-3.14.7-amd64.exe'
$expectedHash='9d9eb2709ef81bf5cd30db3c2096bdbc4ea10087c22e62f27d356b36f6ae9649'
$setupFolder=Join-Path $env:TEMP 'benchmark-peer-review-20260910'
$installerFile=Join-Path $setupFolder 'python-3.14.7-amd64.exe'
$runtimeFolder=Join-Path $env:LOCALAPPDATA 'Programs\Python\Python314'
$runtimeExe=Join-Path $runtimeFolder 'python.exe'
New-Item -ItemType Directory -Path $setupFolder -Force | Out-Null
if (-not (Test-Path -LiteralPath $installerFile -PathType Leaf)) {
    Invoke-WebRequest -UseBasicParsing -Uri $installerUrl -OutFile $installerFile
}
if ((Get-FileHash -LiteralPath $installerFile -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expectedHash) {
    throw 'Installer SHA-256 does not match the official Python release.'
}
$signature=Get-AuthenticodeSignature -LiteralPath $installerFile
if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'O=Python Software Foundation,') {
    throw 'Installer is not validly signed by the Python Software Foundation.'
}
if (Test-Path -LiteralPath $runtimeExe) {
    $existingVersion=& $runtimeExe -c 'import platform; print(platform.python_version())'
    if ($existingVersion -ne $runtimeVersion) { throw 'A different Python already occupies the target directory; choose an explicit upgrade separately.' }
} else {
    $setupArgs=@('/quiet','InstallAllUsers=0',('TargetDir="'+$runtimeFolder+'"'),
        'Include_launcher=0','Include_pip=0','Include_test=0','AssociateFiles=0','PrependPath=0','Shortcuts=0',
        '/log',('"'+(Join-Path $setupFolder 'python-install.log')+'"'))
    $setupProcess=Start-Process -FilePath $installerFile -ArgumentList $setupArgs -WindowStyle Hidden -Wait -PassThru
    if ($setupProcess.ExitCode -notin 0,3010) { throw "Python installer exited with $($setupProcess.ExitCode)" }
}
& $runtimeExe -c "import ssl, json, subprocess, platform; assert platform.python_version() == '3.14.7'; print(platform.python_version())"
if ($LASTEXITCODE -ne 0) { throw 'Installed Python validation failed.' }
# unittest writes its successful summary to stderr. Avoid PowerShell 5.1 turning
# that into NativeCommandError when the caller captures this setup script's output.
$testStdout=Join-Path $setupFolder 'runtime-tests.stdout.log'
$testStderr=Join-Path $setupFolder 'runtime-tests.stderr.log'
$testProcess=Start-Process -FilePath $runtimeExe -ArgumentList @('-m','unittest','-q','test_nightly.py') `
    -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -Wait -PassThru `
    -RedirectStandardOutput $testStdout -RedirectStandardError $testStderr
Get-Content -LiteralPath $testStdout,$testStderr
if ($testProcess.ExitCode -ne 0) { throw 'Regression tests failed under the new runtime; the interpreter setting was not changed.' }
[Environment]::SetEnvironmentVariable('NIGHTLY_BENCH_PYTHON',$runtimeExe,'User')
Write-Output "NIGHTLY_BENCH_PYTHON=$runtimeExe"
