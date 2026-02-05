#!/bin/bash
# GMemory Installation Script for Linux/macOS
# Run: chmod +x install.sh && ./install.sh
#
# Supports:
#   - Fresh install
#   - Upgrade (re-run to update)
#   - Reinstall with --force

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Options
SKIP_SKILLS=false
SKIP_MODULES=false
DEV_MODE=false
FORCE_MODE=false
SKILLS_DIR=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-skills)
            SKIP_SKILLS=true
            shift
            ;;
        --skip-modules)
            SKIP_MODULES=true
            shift
            ;;
        --dev)
            DEV_MODE=true
            shift
            ;;
        --force)
            FORCE_MODE=true
            shift
            ;;
        --skills-dir)
            SKILLS_DIR="$2"
            shift 2
            ;;
        -h|--help)
            echo "GMemory Installation Script"
            echo ""
            echo "Usage: ./install.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --dev           Install with dev dependencies"
            echo "  --force         Force reinstall (uninstall first)"
            echo "  --skip-modules  Skip Python module installation"
            echo "  --skip-skills   Skip OpenCode skills installation"
            echo "  --skills-dir    Custom skills directory"
            echo "  -h, --help     Show this help"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo -e "${CYAN}========================================"
echo -e "  GMemory Installation Script"
echo -e "========================================${NC}"
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo -e "${YELLOW}[INFO] Installing from: $SCRIPT_DIR${NC}"

# Detect package manager
USE_UV=false
PIP_CMD=""
if command -v uv &> /dev/null; then
    USE_UV=true
    echo -e "${GREEN}[OK] Found uv package manager${NC}"
elif command -v pip3 &> /dev/null; then
    PIP_CMD="pip3"
    echo -e "${GREEN}[OK] Found pip3 package manager${NC}"
elif command -v pip &> /dev/null; then
    PIP_CMD="pip"
    echo -e "${GREEN}[OK] Found pip package manager${NC}"
else
    echo -e "${RED}[ERROR] Neither uv nor pip found. Please install Python first.${NC}"
    exit 1
fi

# Check existing installation
EXISTING_VERSION=""
if command -v gmemory &> /dev/null; then
    EXISTING_VERSION=$(gmemory --version 2>/dev/null || echo "")
    if [ -n "$EXISTING_VERSION" ]; then
        echo -e "${YELLOW}[INFO] Existing installation found: $EXISTING_VERSION${NC}"
        echo -e "${YELLOW}[INFO] Will upgrade to latest version...${NC}"
    else
        echo -e "${YELLOW}[INFO] Existing installation found${NC}"
        echo -e "${YELLOW}[INFO] Will upgrade to latest version...${NC}"
    fi
else
    echo -e "${YELLOW}[INFO] No existing installation found, performing fresh install${NC}"
fi

install_modules() {
    echo ""
    if [ -n "$EXISTING_VERSION" ] || command -v gmemory &> /dev/null; then
        echo -e "${CYAN}Step 1: Upgrading GMemory...${NC}"
    else
        echo -e "${CYAN}Step 1: Installing GMemory...${NC}"
    fi

    if $FORCE_MODE; then
        echo -e "${YELLOW}[INFO] Force reinstall requested${NC}"
        if $USE_UV; then
            uv pip uninstall gmemory -q 2>/dev/null || true
        else
            $PIP_CMD uninstall gmemory -y -q 2>/dev/null || true
        fi
    fi

    if $USE_UV; then
        if $DEV_MODE; then
            uv pip install -e "$SCRIPT_DIR" --reinstall
        else
            uv pip install -e "$SCRIPT_DIR" --reinstall
        fi
    else
        if $DEV_MODE; then
            $PIP_CMD install -e "$SCRIPT_DIR[dev]" --upgrade
        else
            $PIP_CMD install -e "$SCRIPT_DIR" --upgrade
        fi
    fi
    echo -e "${GREEN}[OK] GMemory installed/upgraded successfully${NC}"
}

verify_installation() {
    echo ""
    echo -e "${CYAN}Step 2: Verifying installation...${NC}"

    if command -v gmemory &> /dev/null; then
        NEW_VERSION=$(gmemory --version 2>/dev/null || echo "")
        echo -e "${GREEN}[OK] gmemory command is available${NC}"
        if [ -n "$EXISTING_VERSION" ] && [ -n "$NEW_VERSION" ] && [ "$EXISTING_VERSION" != "$NEW_VERSION" ]; then
            echo -e "${GREEN}[OK] Upgraded: $EXISTING_VERSION -> $NEW_VERSION${NC}"
        fi
    else
        echo -e "${YELLOW}[WARN] gmemory command may not be in PATH${NC}"
        echo -e "${YELLOW}       Try: export PATH=\"\$PATH:\$HOME/.local/bin\"${NC}"
    fi
}

install_skills() {
    if $SKIP_SKILLS; then
        echo ""
        echo -e "${YELLOW}Step 3: Skipping skills installation (--skip-skills)${NC}"
        return
    fi

    echo ""
    echo -e "${CYAN}Step 3: Installing/Updating Skills for OpenCode...${NC}"

    skills_args=()
    if [ -n "$SKILLS_DIR" ]; then
        skills_args+=("--skills-dir" "$SKILLS_DIR")
    fi

    "$SCRIPT_DIR/install-skills.sh" "${skills_args[@]}"
}

if ! $SKIP_MODULES; then
    install_modules
    verify_installation
else
    echo ""
    echo -e "${YELLOW}Step 1: Skipping module installation (--skip-modules)${NC}"
fi

install_skills

 # Step 4: Initialize/Verify data directory
echo ""
echo -e "${CYAN}Step 4: Verifying data directory...${NC}"

DATA_DIR="$HOME/.gmemory"
if [ ! -d "$DATA_DIR" ]; then
    mkdir -p "$DATA_DIR"
    echo -e "${GREEN}[OK] Created data directory: $DATA_DIR${NC}"
else
    echo -e "${GREEN}[OK] Data directory exists: $DATA_DIR${NC}"
    
    # Show existing data info
    DB_FILE="$DATA_DIR/data.db"
    if [ -f "$DB_FILE" ]; then
        DB_SIZE=$(du -k "$DB_FILE" | cut -f1)
        echo -e "${YELLOW}[INFO] Existing database: ${DB_SIZE} KB${NC}"
    fi
fi

# Done
echo ""
echo -e "${CYAN}========================================"
echo -e "${GREEN}  Installation Complete!"
echo -e "${CYAN}========================================${NC}"
echo ""
echo -e "${YELLOW}Quick Start:${NC}"
echo "  gmemory health          # Check system health"
echo "  gmemory process         # Fetch unprocessed sessions"
echo "  gmemory search 'query'  # Search memories"
echo "  gmemory q 'query'       # Quick search"
echo ""
echo -e "${CYAN}To upgrade later, simply re-run this script.${NC}"
echo ""
echo -e "${CYAN}Documentation: https://github.com/Keeyuu/GMemory${NC}"
