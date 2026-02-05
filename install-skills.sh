#!/bin/bash
# GMemory Skills Installation Script for npx skills users
# Run: chmod +x install-skills.sh && ./install-skills.sh
#
# For users managing skills via `npx skills` CLI
# Supports: opencode, github-copilot

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;90m'
NC='\033[0m'

# Default agents
AGENTS=("opencode" "github-copilot")
LIST_MODE=false
UNINSTALL_MODE=false
SKILLS_DIR=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --agents)
            IFS=',' read -ra AGENTS <<< "$2"
            shift 2
            ;;
        --skills-dir)
            SKILLS_DIR="$2"
            shift 2
            ;;
        --list)
            LIST_MODE=true
            shift
            ;;
        --uninstall)
            UNINSTALL_MODE=true
            shift
            ;;
        -h|--help)
            echo "GMemory Skills Installer (npx skills)"
            echo ""
            echo "Usage: ./install-skills.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --agents <list>   Comma-separated agents (default: opencode,github-copilot)"
            echo "  --list            List available skills"
            echo "  --skills-dir      Custom skills source directory"
            echo "  --uninstall       Remove skills"
            echo "  -h, --help        Show this help"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

echo -e "${CYAN}========================================"
echo -e "  GMemory Skills Installer (npx skills)"
echo -e "========================================${NC}"
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -n "$SKILLS_DIR" ]; then
    SKILLS_SOURCE="$SKILLS_DIR"
else
    SKILLS_SOURCE="$SCRIPT_DIR/skills"
fi

# Available skills
declare -A SKILL_PATHS
declare -A SKILL_DESCS
SKILL_PATHS["gmemory"]="$SKILLS_SOURCE/gmemory"
SKILL_DESCS["gmemory"]="Memory CRUD operations (search, add, update, delete)"
SKILL_PATHS["gmemory-refine"]="$SKILLS_SOURCE/gmemory-refine"
SKILL_DESCS["gmemory-refine"]="Session refinement and memory evolution"

SKILL_NAMES=("gmemory" "gmemory-refine")

# List mode
if $LIST_MODE; then
    echo -e "${YELLOW}Available GMemory Skills:${NC}"
    echo ""
    for skill in "${SKILL_NAMES[@]}"; do
        echo -e "  ${GREEN}$skill${NC}"
        echo -e "    ${GRAY}${SKILL_DESCS[$skill]}${NC}"
    echo -e "    ${GRAY}Path: ${SKILL_PATHS[$skill]}${NC}"
    echo ""
    done
    exit 0
fi

# Check if npx is available
if ! command -v npx &> /dev/null; then
    echo -e "${RED}[ERROR] npx not found. Please install Node.js first.${NC}"
    exit 1
fi

echo -e "${YELLOW}[INFO] Skills source: $SKILLS_SOURCE${NC}"
echo -e "${YELLOW}[INFO] Target agents: ${AGENTS[*]}${NC}"
echo ""

# Uninstall mode
if $UNINSTALL_MODE; then
    echo -e "${CYAN}Uninstalling GMemory skills...${NC}"
    for agent in "${AGENTS[@]}"; do
        for skill in "${SKILL_NAMES[@]}"; do
            echo -e "  Removing $skill from $agent..."
            if npx skills uninstall "$skill" --agent "$agent" 2>/dev/null; then
                echo -e "  ${GREEN}[OK] Removed $skill from $agent${NC}"
            else
                echo -e "  ${GRAY}[SKIP] $skill not installed for $agent${NC}"
            fi
        done
    done
    echo ""
    echo -e "${GREEN}Uninstall complete.${NC}"
    exit 0
fi

# Install skills
echo -e "${CYAN}Installing GMemory skills...${NC}"
echo ""

for agent in "${AGENTS[@]}"; do
    echo -e "${CYAN}Agent: $agent${NC}"
    
    for skill in "${SKILL_NAMES[@]}"; do
        skill_path="${SKILL_PATHS[$skill]}"
        
        if [ ! -d "$skill_path" ]; then
            echo -e "  ${RED}[ERROR] Skill path not found: $skill_path${NC}"
            continue
        fi
        
        echo -e "  ${YELLOW}Installing $skill...${NC}"
        
        # Try different npx skills command patterns
        if npx skills install "$skill_path" --agent "$agent" 2>/dev/null; then
            echo -e "  ${GREEN}[OK] Installed $skill for $agent${NC}"
        elif npx skills add "$skill" "$skill_path" --agent "$agent" 2>/dev/null; then
            echo -e "  ${GREEN}[OK] Added $skill for $agent${NC}"
        else
            echo -e "  ${YELLOW}[WARN] Could not auto-install. Manual command:${NC}"
            echo -e "         ${GRAY}npx skills install \"$skill_path\" --agent $agent${NC}"
        fi
    done
    echo ""
done

# Show manual instructions as fallback
echo -e "${CYAN}========================================"
echo -e "  Manual Installation (if needed)"
echo -e "========================================${NC}"
echo ""
echo -e "${YELLOW}If auto-install didn't work, run these commands:${NC}"
echo ""

for agent in "${AGENTS[@]}"; do
    echo -e "${CYAN}# For $agent${NC}"
    for skill in "${SKILL_NAMES[@]}"; do
        echo "npx skills install \"${SKILL_PATHS[$skill]}\" --agent $agent"
    done
    echo ""
done

echo -e "${CYAN}========================================"
echo -e "${GREEN}  Installation Complete!"
echo -e "${CYAN}========================================${NC}"
echo ""
echo -e "${YELLOW}Verify with: npx skills list${NC}"
