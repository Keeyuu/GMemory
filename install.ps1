# GMemory Installation Script for Windows
# Run: powershell -ExecutionPolicy Bypass -File install.ps1
#
# Supports:
#   - Fresh install
#   - Upgrade (re-run to update)
#   - Reinstall with --Force

param(
    [switch]$SkipModules,
    [switch]$Dev,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  GMemory Installation Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Options:" -ForegroundColor Yellow
Write-Host "  -SkipModules  Skip Python module installation" -ForegroundColor Yellow
Write-Host "  -Dev          Install with dev dependencies" -ForegroundColor Yellow
Write-Host "  -Force        Force reinstall" -ForegroundColor Yellow
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

function Install-Modules {
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
                uv pip install -e "${ScriptDir}[dev]" --reinstall
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

    try {
        Get-Command gmemory-mcp -ErrorAction Stop | Out-Null
        Write-Host "[OK] gmemory-mcp command is available" -ForegroundColor Green
    } catch {
        Write-Host "[WARN] gmemory-mcp command not found in PATH" -ForegroundColor Yellow
    }

    try {
        Get-Command gmemory-web -ErrorAction Stop | Out-Null
        Write-Host "[OK] gmemory-web command is available" -ForegroundColor Green
    } catch {
        Write-Host "[WARN] gmemory-web command not found in PATH" -ForegroundColor Yellow
    }
}

function Configure-OpenCodeMCP {
    Write-Host ""
    Write-Host "Step 4: Configuring OpenCode MCP (optional)..." -ForegroundColor Cyan

    $McpCommandPath = $null
    try {
        $McpCommandPath = (Get-Command gmemory-mcp -ErrorAction Stop).Source
    } catch {
        $FallbackPath = Join-Path $ScriptDir ".venv\Scripts\gmemory-mcp.exe"
        if (Test-Path $FallbackPath) {
            $McpCommandPath = $FallbackPath
        }
    }

    if (-not $McpCommandPath) {
        Write-Host "[WARN] Could not resolve gmemory-mcp executable path" -ForegroundColor Yellow
        Write-Host "       You can configure OpenCode manually after installation" -ForegroundColor Yellow
        return
    }

    $OpenCodeConfigPath = Join-Path $env:USERPROFILE ".config\opencode\opencode.json"
    if (-not (Test-Path $OpenCodeConfigPath)) {
        Write-Host "[INFO] OpenCode config not found: $OpenCodeConfigPath" -ForegroundColor Yellow
        Write-Host "[INFO] Recommended MCP config snippet:" -ForegroundColor Yellow
        Write-Host "       \"gmemory\": { \"command\": [\"$McpCommandPath\"], \"enabled\": true, \"type\": \"local\" }" -ForegroundColor Yellow
        return
    }

    try {
        $config = Get-Content -Path $OpenCodeConfigPath -Raw | ConvertFrom-Json

        if (-not $config.mcp) {
            $config | Add-Member -NotePropertyName mcp -NotePropertyValue ([PSCustomObject]@{})
        }

        if (-not $config.mcp.gmemory) {
            $config.mcp | Add-Member -NotePropertyName gmemory -NotePropertyValue ([PSCustomObject]@{})
        }

        $config.mcp.gmemory.command = @($McpCommandPath)
        $config.mcp.gmemory.enabled = $true
        $config.mcp.gmemory.type = "local"

        $config | ConvertTo-Json -Depth 20 | Set-Content -Path $OpenCodeConfigPath -Encoding UTF8
        Write-Host "[OK] OpenCode MCP configured: $OpenCodeConfigPath" -ForegroundColor Green
        Write-Host "[OK] gmemory command uses absolute path: $McpCommandPath" -ForegroundColor Green
    } catch {
        Write-Host "[WARN] Failed to update OpenCode config automatically: $_" -ForegroundColor Yellow
        Write-Host "[INFO] Please update gmemory MCP command manually to: $McpCommandPath" -ForegroundColor Yellow
    }
}

if (-not $SkipModules) {
    Install-Modules
    Verify-Installation
} else {
    Write-Host ""
    Write-Host "Step 1: Skipping module installation (--SkipModules)" -ForegroundColor Yellow
}

# Step 3: Initialize/Verify data directory
Write-Host ""
Write-Host "Step 3: Verifying data directory..." -ForegroundColor Cyan

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

Configure-OpenCodeMCP

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
