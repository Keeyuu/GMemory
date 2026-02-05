# GMemory Installation Script for Windows
# Run: powershell -ExecutionPolicy Bypass -File install.ps1
#
# Supports:
#   - Fresh install
#   - Upgrade (re-run to update)
#   - Reinstall with --Force

param(
    [switch]$SkipSkills,
    [switch]$SkipModules,
    [switch]$Dev,
    [switch]$Force,
    [string]$SkillsDir
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  GMemory Installation Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Options:" -ForegroundColor Yellow
Write-Host "  -SkipModules  Skip Python module installation" -ForegroundColor Yellow
Write-Host "  -SkipSkills   Skip OpenCode skills installation" -ForegroundColor Yellow
Write-Host "  -Dev          Install with dev dependencies" -ForegroundColor Yellow
Write-Host "  -Force        Force reinstall" -ForegroundColor Yellow
Write-Host "  -SkillsDir    Custom skills source directory" -ForegroundColor Yellow
Write-Host ""

# Detect package manager
$UseUv = $false
$UsePip = $false
if (Get-Command uv -ErrorAction SilentlyContinue) {
    $UseUv = $true
    Write-Host "[OK] Found uv package manager" -ForegroundColor Green
}
if (Get-Command pip -ErrorAction SilentlyContinue) {
    $UsePip = $true
    if (-not $UseUv) {
        Write-Host "[OK] Found pip package manager" -ForegroundColor Green
    }
}
if (-not $UseUv -and -not $UsePip) {
    Write-Host "[ERROR] Neither uv nor pip found. Please install Python first." -ForegroundColor Red
    exit 1
}

# Get script directory (where GMemory source is)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Write-Host "[INFO] Installing from: $ScriptDir" -ForegroundColor Yellow

# Check existing installation
$ExistingVersion = $null
try {
    $ExistingVersion = gmemory --version 2>$null
    if ($ExistingVersion) {
        Write-Host "[INFO] Existing installation found: $ExistingVersion" -ForegroundColor Yellow
        Write-Host "[INFO] Will upgrade to latest version..." -ForegroundColor Yellow
    }
} catch {
    Write-Host "[INFO] No existing installation found, performing fresh install" -ForegroundColor Yellow
}

function Install-Modules {
    Write-Host ""
    if ($ExistingVersion) {
        Write-Host "Step 1: Upgrading GMemory..." -ForegroundColor Cyan
    } else {
        Write-Host "Step 1: Installing GMemory..." -ForegroundColor Cyan
    }

    try {
        if ($UseUv) {
            # Use 'uv tool install' for global CLI tool installation
            # This installs to ~/.local/bin which is in PATH, avoiding venv isolation issues
            # Use Python 3.12 to ensure compatibility with onnxruntime (fastembed dependency)
            if ($Force) {
                Write-Host "[INFO] Force reinstall requested" -ForegroundColor Yellow
                uv tool uninstall gmemory 2>$null
            }
            Write-Host "[INFO] Installing with: uv tool install -e $ScriptDir --python 3.12 --force" -ForegroundColor Yellow
            uv tool install -e "$ScriptDir" --python 3.12 --force
        } elseif ($UsePip) {
            if ($Force) {
                Write-Host "[INFO] Force reinstall requested" -ForegroundColor Yellow
                pip uninstall gmemory -y -q 2>$null
            }
            if ($Dev) {
                pip install -e "$ScriptDir[dev]" --upgrade
            } else {
                pip install -e "$ScriptDir" --upgrade
            }
        }
        Write-Host "[OK] GMemory installed/upgraded successfully" -ForegroundColor Green
    } catch {
        Write-Host "[ERROR] Failed to install GMemory: $_" -ForegroundColor Red
        exit 1
    }
}

function Verify-Installation {
    Write-Host ""
    Write-Host "Step 2: Verifying installation..." -ForegroundColor Cyan

    try {
        $NewVersion = gmemory --version 2>&1
        if ($NewVersion) {
            Write-Host "[OK] gmemory command is available" -ForegroundColor Green
            if ($ExistingVersion -and $ExistingVersion -ne $NewVersion) {
                Write-Host "[OK] Upgraded: $ExistingVersion -> $NewVersion" -ForegroundColor Green
            }
        } else {
            $helpOutput = gmemory --help 2>&1 | Select-String "GMemory"
            if ($helpOutput) {
                Write-Host "[OK] gmemory command is available" -ForegroundColor Green
            }
        }
    } catch {
        Write-Host "[WARN] Could not verify gmemory command" -ForegroundColor Yellow
    }
}

function Install-Skills {
    if ($SkipSkills) {
        Write-Host ""
        Write-Host "Step 3: Skipping skills installation (--SkipSkills)" -ForegroundColor Yellow
        return
    }

    Write-Host ""
    Write-Host "Step 3: Installing/Updating Skills for OpenCode..." -ForegroundColor Cyan

    $skillsArgs = @()
    if ($SkillsDir) {
        $skillsArgs += "--skills-dir"
        $skillsArgs += $SkillsDir
    }

    & (Join-Path $ScriptDir "install-skills.ps1") @skillsArgs
}

if (-not $SkipModules) {
    Install-Modules
    Verify-Installation
} else {
    Write-Host ""
    Write-Host "Step 1: Skipping module installation (--SkipModules)" -ForegroundColor Yellow
}

Install-Skills

# Step 4: Initialize/Verify data directory
Write-Host ""
Write-Host "Step 4: Verifying data directory..." -ForegroundColor Cyan

$DataDir = Join-Path $env:USERPROFILE ".gmemory"
if (-not (Test-Path $DataDir)) {
    New-Item -ItemType Directory -Path $DataDir -Force | Out-Null
    Write-Host "[OK] Created data directory: $DataDir" -ForegroundColor Green
} else {
    Write-Host "[OK] Data directory exists: $DataDir" -ForegroundColor Green
    
    # Show existing data info
    $DbFile = Join-Path $DataDir "data.db"
    if (Test-Path $DbFile) {
        $DbSize = (Get-Item $DbFile).Length / 1KB
        Write-Host "[INFO] Existing database: $([math]::Round($DbSize, 1)) KB" -ForegroundColor Yellow
    }
}

# Done
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Installation Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Quick Start:" -ForegroundColor Yellow
Write-Host "  gmemory health          # Check system health"
Write-Host "  gmemory process         # Fetch unprocessed sessions"
Write-Host "  gmemory search 'query'  # Search memories"
Write-Host "  gmemory q 'query'       # Quick search"
Write-Host ""
Write-Host "To upgrade later, simply re-run this script." -ForegroundColor Cyan
Write-Host ""
Write-Host "Documentation: https://github.com/Keeyuu/GMemory" -ForegroundColor Cyan
