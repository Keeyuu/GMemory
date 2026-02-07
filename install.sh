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
SKIP_MODULES=false
DEV_MODE=false
FORCE_MODE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
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
        -h|--help)
            echo "GMemory Installation Script"
            echo ""
            echo "Usage: ./install.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --dev           Install with dev dependencies"
            echo "  --force         Force reinstall (uninstall first)"
            echo "  --skip-modules  Skip Python module installation"
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
            uv pip install -e "$SCRIPT_DIR[dev]" --reinstall
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

    if command -v gmemory-mcp &> /dev/null; then
        echo -e "${GREEN}[OK] gmemory-mcp command is available${NC}"
    else
        echo -e "${YELLOW}[WARN] gmemory-mcp command may not be in PATH${NC}"
    fi

    if command -v gmemory-web &> /dev/null; then
        echo -e "${GREEN}[OK] gmemory-web command is available${NC}"
    else
        echo -e "${YELLOW}[WARN] gmemory-web command may not be in PATH${NC}"
    fi
}

configure_opencode_mcp() {
    echo ""
    echo -e "${CYAN}Step 4: Configuring OpenCode MCP (optional)...${NC}"

    MCP_COMMAND_PATH=""
    if command -v gmemory-mcp &> /dev/null; then
        MCP_COMMAND_PATH="$(command -v gmemory-mcp)"
    elif [ -x "$SCRIPT_DIR/.venv/bin/gmemory-mcp" ]; then
        MCP_COMMAND_PATH="$SCRIPT_DIR/.venv/bin/gmemory-mcp"
    fi

    if [ -z "$MCP_COMMAND_PATH" ]; then
        echo -e "${YELLOW}[WARN] Could not resolve gmemory-mcp executable path${NC}"
        echo -e "${YELLOW}       You can configure OpenCode manually after installation${NC}"
        return
    fi

    OPENCODE_CONFIG="$HOME/.config/opencode/opencode.json"
    if [ ! -f "$OPENCODE_CONFIG" ]; then
        echo -e "${YELLOW}[INFO] OpenCode config not found: $OPENCODE_CONFIG${NC}"
        echo -e "${YELLOW}[INFO] Recommended MCP config snippet:${NC}"
        echo "       \"gmemory\": { \"command\": [\"$MCP_COMMAND_PATH\"], \"enabled\": true, \"type\": \"local\" }"
        return
    fi

    PYTHON_BIN=""
    if command -v python3 &> /dev/null; then
        PYTHON_BIN="python3"
    elif command -v python &> /dev/null; then
        PYTHON_BIN="python"
    fi

    if [ -z "$PYTHON_BIN" ]; then
        echo -e "${YELLOW}[WARN] python/python3 not found; cannot auto-update OpenCode config${NC}"
        echo -e "${YELLOW}[INFO] Please set mcp.gmemory.command to: $MCP_COMMAND_PATH${NC}"
        return
    fi

    if "$PYTHON_BIN" -c "import json, pathlib, sys; p=pathlib.Path(sys.argv[1]); c=sys.argv[2]; d=json.loads(p.read_text(encoding='utf-8')); d.setdefault('mcp',{}).setdefault('gmemory',{}).update({'command':[c],'enabled':True,'type':'local'}); p.write_text(json.dumps(d, ensure_ascii=False, indent=2)+'\\n', encoding='utf-8')" "$OPENCODE_CONFIG" "$MCP_COMMAND_PATH"; then
        echo -e "${GREEN}[OK] OpenCode MCP configured: $OPENCODE_CONFIG${NC}"
        echo -e "${GREEN}[OK] gmemory command uses absolute path: $MCP_COMMAND_PATH${NC}"
    else
        echo -e "${YELLOW}[WARN] Failed to update OpenCode config automatically${NC}"
        echo -e "${YELLOW}[INFO] Please set mcp.gmemory.command to: $MCP_COMMAND_PATH${NC}"
    fi
}

sync_opencode_prompts() {
    echo ""
    echo -e "${CYAN}Step 5: Syncing OpenCode prompt templates (optional)...${NC}"

    TEMPLATE_ROOT="$SCRIPT_DIR/opencode"
    if [ ! -d "$TEMPLATE_ROOT" ]; then
        echo -e "${YELLOW}[INFO] Prompt templates not found in project: $TEMPLATE_ROOT${NC}"
        return
    fi

    OPENCODE_DIR="$HOME/.config/opencode"
    if [ ! -d "$OPENCODE_DIR" ]; then
        echo -e "${YELLOW}[INFO] OpenCode directory not found: $OPENCODE_DIR${NC}"
        echo -e "${YELLOW}[INFO] Skip prompt sync; rerun install after OpenCode initializes this directory.${NC}"
        return
    fi

    sync_prompt_file() {
        local source_path="$1"
        local target_dir="$2"

        if [ ! -f "$source_path" ]; then
            echo -e "${YELLOW}[WARN] Missing prompt template: $source_path${NC}"
            return
        fi

        mkdir -p "$target_dir"
        cp "$source_path" "$target_dir/"
        echo -e "${GREEN}[OK] Synced prompt: $target_dir/$(basename "$source_path")${NC}"
        SYNCED_COUNT=$((SYNCED_COUNT + 1))
    }

    SYNCED_COUNT=0
    sync_prompt_file "$TEMPLATE_ROOT/commands/refine-memory.md" "$OPENCODE_DIR/commands"
    sync_prompt_file "$TEMPLATE_ROOT/commands/scan-memories.md" "$OPENCODE_DIR/commands"
    sync_prompt_file "$TEMPLATE_ROOT/agents/knowledge-archivist.md" "$OPENCODE_DIR/agents"

    if [ "$SYNCED_COUNT" -eq 0 ]; then
        echo -e "${YELLOW}[WARN] No prompt templates were synced${NC}"
    else
        echo -e "${GREEN}[OK] Synced $SYNCED_COUNT OpenCode prompt template(s)${NC}"
    fi
}

if ! $SKIP_MODULES; then
    install_modules
    verify_installation
else
    echo ""
    echo -e "${YELLOW}Step 1: Skipping module installation (--skip-modules)${NC}"
fi

# Step 3: Initialize/Verify data directory
echo ""
echo -e "${CYAN}Step 3: Verifying data directory...${NC}"

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

configure_opencode_mcp
sync_opencode_prompts

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
