# GMemory Skills Installation Script for npx skills users
# Run: powershell -ExecutionPolicy Bypass -File install-skills.ps1
#
# For users managing skills via `npx skills` CLI
# Supports: opencode, github-copilot

param(
    [string[]]$Agents = @("opencode", "github-copilot"),
    [switch]$List,
    [switch]$Uninstall
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  GMemory Skills Installer (npx skills)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Get script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$SkillsSource = Join-Path $ScriptDir "skills"

# Available skills
$Skills = @(
    @{
        Name = "gmemory"
        Path = Join-Path $SkillsSource "gmemory"
        Description = "Memory CRUD operations (search, add, update, delete)"
    },
    @{
        Name = "gmemory-refine"
        Path = Join-Path $SkillsSource "gmemory-refine"
        Description = "Session refinement and memory evolution"
    }
)

# List mode
if ($List) {
    Write-Host "Available GMemory Skills:" -ForegroundColor Yellow
    Write-Host ""
    foreach ($skill in $Skills) {
        Write-Host "  $($skill.Name)" -ForegroundColor Green
        Write-Host "    $($skill.Description)" -ForegroundColor Gray
        Write-Host "    Path: $($skill.Path)" -ForegroundColor Gray
        Write-Host ""
    }
    exit 0
}

# Check if npx is available
if (-not (Get-Command npx -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] npx not found. Please install Node.js first." -ForegroundColor Red
    exit 1
}

Write-Host "[INFO] Skills source: $SkillsSource" -ForegroundColor Yellow
Write-Host "[INFO] Target agents: $($Agents -join ', ')" -ForegroundColor Yellow
Write-Host ""

# Uninstall mode
if ($Uninstall) {
    Write-Host "Uninstalling GMemory skills..." -ForegroundColor Cyan
    foreach ($agent in $Agents) {
        foreach ($skill in $Skills) {
            Write-Host "  Removing $($skill.Name) from $agent..." -ForegroundColor Yellow
            try {
                npx skills uninstall $skill.Name --agent $agent 2>$null
                Write-Host "  [OK] Removed $($skill.Name) from $agent" -ForegroundColor Green
            } catch {
                Write-Host "  [SKIP] $($skill.Name) not installed for $agent" -ForegroundColor Gray
            }
        }
    }
    Write-Host ""
    Write-Host "Uninstall complete." -ForegroundColor Green
    exit 0
}

# Install skills
Write-Host "Installing GMemory skills..." -ForegroundColor Cyan
Write-Host ""

foreach ($agent in $Agents) {
    Write-Host "Agent: $agent" -ForegroundColor Cyan
    
    foreach ($skill in $Skills) {
        if (-not (Test-Path $skill.Path)) {
            Write-Host "  [ERROR] Skill path not found: $($skill.Path)" -ForegroundColor Red
            continue
        }
        
        Write-Host "  Installing $($skill.Name)..." -ForegroundColor Yellow
        try {
            # Try different npx skills command patterns
            # Pattern 1: npx skills install <path> --agent <agent>
            # Pattern 2: npx skills add <name> <path> --agent <agent>
            # Pattern 3: npx skills link <path> --agent <agent>
            
            $result = npx skills install $skill.Path --agent $agent 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "  [OK] Installed $($skill.Name) for $agent" -ForegroundColor Green
            } else {
                # Try alternative command
                $result = npx skills add $skill.Name $skill.Path --agent $agent 2>&1
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "  [OK] Added $($skill.Name) for $agent" -ForegroundColor Green
                } else {
                    Write-Host "  [WARN] Could not auto-install. Manual command:" -ForegroundColor Yellow
                    Write-Host "         npx skills install `"$($skill.Path)`" --agent $agent" -ForegroundColor Gray
                }
            }
        } catch {
            Write-Host "  [WARN] Auto-install failed. Try manually:" -ForegroundColor Yellow
            Write-Host "         npx skills install `"$($skill.Path)`" --agent $agent" -ForegroundColor Gray
        }
    }
    Write-Host ""
}

# Show manual instructions as fallback
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Manual Installation (if needed)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "If auto-install didn't work, run these commands:" -ForegroundColor Yellow
Write-Host ""

foreach ($agent in $Agents) {
    Write-Host "# For $agent" -ForegroundColor Cyan
    foreach ($skill in $Skills) {
        Write-Host "npx skills install `"$($skill.Path)`" --agent $agent"
    }
    Write-Host ""
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Installation Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Verify with: npx skills list" -ForegroundColor Yellow
