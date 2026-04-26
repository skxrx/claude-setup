#!/usr/bin/env bash
set -euo pipefail

# Claude Blockchain Dev Framework — Installer
# Copies agents, commands, settings, and hooks into ~/.claude/

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="$HOME/.claude"

echo "=== Claude Blockchain Dev Framework ==="
echo "Installing to: $CLAUDE_DIR"
echo ""

# --- Agents ---
echo "[1/5] Installing agents..."
mkdir -p "$CLAUDE_DIR/agents"
cp "$SCRIPT_DIR/agents/"*.md "$CLAUDE_DIR/agents/"
echo "  ✓ $(ls "$SCRIPT_DIR/agents/"*.md | wc -l | tr -d ' ') agents installed"

# --- Commands (slash commands) ---
echo "[2/5] Installing commands..."
mkdir -p "$CLAUDE_DIR/commands"
cp "$SCRIPT_DIR/commands/"*.md "$CLAUDE_DIR/commands/"
echo "  ✓ $(ls "$SCRIPT_DIR/commands/"*.md | wc -l | tr -d ' ') commands installed"

# --- Settings (MCP servers) ---
echo "[3/5] Installing settings..."
if [ -f "$CLAUDE_DIR/settings.json" ]; then
  cp "$CLAUDE_DIR/settings.json" "$CLAUDE_DIR/settings.json.bak.$(date +%s)"
  echo "  → Existing settings.json backed up"
fi
cp "$SCRIPT_DIR/settings/settings.json" "$CLAUDE_DIR/settings.json"
echo "  ✓ MCP servers configured"

# --- Hooks ---
echo "[4/5] Installing hooks..."
if [ -f "$CLAUDE_DIR/hooks.json" ]; then
  cp "$CLAUDE_DIR/hooks.json" "$CLAUDE_DIR/hooks.json.bak.$(date +%s)"
  echo "  → Existing hooks.json backed up"
fi
cp "$SCRIPT_DIR/settings/hooks.json" "$CLAUDE_DIR/hooks.json"
echo "  ✓ Security hooks installed"

# --- Memory directory ---
echo "[5/5] Setting up memory..."
mkdir -p "$CLAUDE_DIR/projects"
echo "  ✓ Memory directories ready"

echo ""
echo "=== Installation complete ==="
echo ""
echo "What's installed:"
echo "  Agents:   $(ls "$CLAUDE_DIR/agents/"*.md 2>/dev/null | wc -l | tr -d ' ')"
echo "  Commands: $(ls "$CLAUDE_DIR/commands/"*.md 2>/dev/null | wc -l | tr -d ' ')"
echo "  MCP:      context7, crypto-price, cryptodata, phantom, docker"
echo "  MCP (disabled): alchemy, evm, postgres"
echo "  Hooks:    security-critical file alerts, secret file protection, desktop notifications"
echo ""
echo "Quick start:"
echo "  /security-audit src/signing/  — Audit signing module"
echo "  /chain-add Solana             — Add new chain support"
echo "  /implement EIP-4337 support   — Orchestrate multi-agent implementation"
echo "  /pipeline [arch, types] → impl → [review, security] : Build fee module"
echo "  /review                       — Review recent changes"
echo "  /tdd fee estimation           — TDD workflow for feature"
echo "  /idea DEX aggregator          — Product strategy brainstorm"
echo ""
echo "To enable disabled MCP servers, edit ~/.claude/settings.json"
echo "  - alchemy: set ALCHEMY_API_KEY"
echo "  - evm: set ETHERSCAN_API_KEY and PROVIDER_URL"
echo "  - postgres: update connection string"
