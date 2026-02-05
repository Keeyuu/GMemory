# GMemory Installation Script for Windows
# Run: powershell -ExecutionPolicy Bypass -File install.ps1
#
# Supports:
#   - Fresh install
#   - Upgrade (re-run to update)
#   - Reinstall with --Force

param(
    [switch]$SkipSkills,
    [switch]$Dev,
    [switch]$Force,
    [string]$SkillsDir
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  GMemory Installation Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Detect package manager
$UseUv = $false
if (Get-Command uv -ErrorAction SilentlyContinue) {
    $UseUv = $true
    Write-Host "[OK] Found uv package manager" -ForegroundColor Green
} elseif (Get-Command pip -ErrorAction SilentlyContinue) {
    Write-Host "[OK] Found pip package manager" -ForegroundColor Green
} else {
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

# Step 1: Install/Upgrade GMemory
Write-Host ""
if ($ExistingVersion) {
    Write-Host "Step 1: Upgrading GMemory..." -ForegroundColor Cyan
} else {
    Write-Host "Step 1: Installing GMemory..." -ForegroundColor Cyan
}

try {
    if ($UseUv) {
        if ($Force) {
            Write-Host "[INFO] Force reinstall requested" -ForegroundColor Yellow
            uv pip uninstall gmemory -q 2>$null
        }
        if ($Dev) {
            uv pip install -e "$ScriptDir" --reinstall
        } else {
            uv pip install -e "$ScriptDir" --reinstall
        }
    } else {
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

# Step 2: Verify installation
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

# Step 3: Install/Update Skills
if (-not $SkipSkills) {
    Write-Host ""
    Write-Host "Step 3: Installing/Updating Skills for OpenCode..." -ForegroundColor Cyan
    
    # Determine skills directory
    if (-not $SkillsDir) {
        $SkillsDir = Join-Path $env:USERPROFILE ".config\opencode\skills"
    }
    
    # Create skills directory if not exists
    if (-not (Test-Path $SkillsDir)) {
        New-Item -ItemType Directory -Path $SkillsDir -Force | Out-Null
        Write-Host "[OK] Created skills directory: $SkillsDir" -ForegroundColor Green
    }
    
    # Copy skills (overwrite existing)
    $SourceSkills = Join-Path $ScriptDir "skills"
    if (Test-Path $SourceSkills) {
        $SkillFolders = Get-ChildItem -Path $SourceSkills -Directory
        foreach ($skill in $SkillFolders) {
            $DestPath = Join-Path $SkillsDir $skill.Name
            $Action = "Installed"
            if (Test-Path $DestPath) {
                Remove-Item -Path $DestPath -Recurse -Force
                $Action = "Updated"
            }
            Copy-Item -Path $skill.FullName -Destination $DestPath -Recurse
            Write-Host "[OK] $Action skill: $($skill.Name)" -ForegroundColor Green
        }
    } else {
        Write-Host "[WARN] Skills directory not found in source" -ForegroundColor Yellow
    }
} else {
    Write-Host ""
    Write-Host "Step 3: Skipping skills installation (--SkipSkills)" -ForegroundColor Yellow
}

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
