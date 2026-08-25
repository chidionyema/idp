#!/usr/bin/env pwsh
# Sovereign Bus shim (Windows), mirrors bin/sb: ensures sovereign/.venv
# exists (uv preferred, plain venv as fallback), then execs the CLI.
# See sovereign/CONTRACT.md and features/sovereign-bus/cp20_cross_platform.feature.
# LAW 46: IDP is computed from this script's own location, never a literal.
$ErrorActionPreference = "Stop"

$IDP = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Venv = Join-Path $IDP "sovereign/.venv"
$Req = Join-Path $IDP "sovereign/requirements.txt"
$VenvPython = Join-Path $Venv "Scripts/python.exe"

function Find-Python {
    foreach ($cand in @("python3.13", "python3.12", "python3.11", "python3.10", "python", "python3")) {
        $cmd = Get-Command $cand -ErrorAction SilentlyContinue
        if ($cmd) {
            $versionOk = & $cmd.Source -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" 2>$null
            if ($LASTEXITCODE -eq 0) {
                return $cmd.Source
            }
        }
    }
    return $null
}

if (-not (Test-Path $VenvPython)) {
    $uv = Get-Command uv -ErrorAction SilentlyContinue
    if ($uv) {
        & uv venv --python 3.10 $Venv | Out-Null
        & uv pip install --python $VenvPython -r $Req | Out-Null
    } else {
        $py = Find-Python
        if (-not $py) {
            Write-Error "sb: no python >=3.10 on PATH and no uv available"
            exit 2
        }
        & $py -m venv $Venv
        & $VenvPython -m pip install -q --upgrade pip
        & $VenvPython -m pip install -q -r $Req
    }
}

$env:PYTHONPATH = if ($env:PYTHONPATH) { "$IDP$([System.IO.Path]::PathSeparator)$env:PYTHONPATH" } else { $IDP }
& $VenvPython -m sovereign.cli @args
exit $LASTEXITCODE
