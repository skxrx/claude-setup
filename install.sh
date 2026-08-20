#!/usr/bin/env bash
set -euo pipefail

# Claude Blockchain Dev Framework — Installer
# Agents/commands are copied into ~/.claude/; hooks are MERGED into
# ~/.claude/settings.json (the location Claude Code actually reads);
# MCP servers are registered via `claude mcp add --scope user`.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="$HOME/.claude"

echo "=== Claude Blockchain Dev Framework ==="
echo "Installing from: $SCRIPT_DIR"
echo ""

# --- Agents ---
echo "[1/7] Agents..."
mkdir -p "$CLAUDE_DIR/agents"
cp "$SCRIPT_DIR/agents/"*.md "$CLAUDE_DIR/agents/"
echo "  ✓ $(ls "$SCRIPT_DIR/agents/"*.md | wc -l | tr -d ' ') agents"

# --- Commands ---
echo "[2/7] Commands..."
mkdir -p "$CLAUDE_DIR/commands"
cp "$SCRIPT_DIR/commands/"*.md "$CLAUDE_DIR/commands/"
echo "  ✓ $(ls "$SCRIPT_DIR/commands/"*.md | wc -l | tr -d ' ') commands"

# --- Hooks: script + merge into settings.json (NOT a separate hooks.json) ---
echo "[3/7] Hooks -> settings.json ..."
mkdir -p "$CLAUDE_DIR/hooks"
cp "$SCRIPT_DIR/hooks/"*.sh "$CLAUDE_DIR/hooks/"
chmod +x "$CLAUDE_DIR/hooks/"*.sh
if [ -f "$CLAUDE_DIR/settings.json" ]; then
  cp "$CLAUDE_DIR/settings.json" "$CLAUDE_DIR/settings.json.bak.$(date +%s)"
fi
python3 - "$CLAUDE_DIR/settings.json" "$SCRIPT_DIR/settings/hooks.json" <<'PY'
import json, os, sys
sp, hp = sys.argv[1], sys.argv[2]
settings = {}
if os.path.exists(sp):
    with open(sp) as f:
        settings = json.load(f)
with open(hp) as f:
    hooks = json.load(f)
settings.pop("mcpServers", None)  # dead config from old installer versions
settings["hooks"] = hooks.get("hooks", hooks)
with open(sp, "w") as f:
    json.dump(settings, f, indent=2)
print("  ✓ hooks merged (other settings preserved)")
PY

# --- MCP servers ---
echo "[4/7] MCP servers..."
NPM_REG="npm_config_registry=https://registry.npmjs.org/"
register() {
  local name="$1"; shift
  if claude mcp get "$name" >/dev/null 2>&1; then
    echo "  = $name (already registered, left as-is)"
  else
    claude mcp add --scope user "$name" "$@" >/dev/null
    echo "  + $name"
  fi
}
register harness-memory         -- uv run --directory "$SCRIPT_DIR/mcp/memory" python server.py
register harness-second-opinion -- uv run --directory "$SCRIPT_DIR/mcp/second-opinion" python server.py
register context7     -e "$NPM_REG" -- npx -y @upstash/context7-mcp
register cryptodata   -e "$NPM_REG" -- npx -y cryptodata-mcp
register phantom      -e "$NPM_REG" -- npx -y @phantom/mcp-server
register docker       -e "$NPM_REG" -- npx -y docker-mcp

# --- Memory database ---
echo "[5/7] Memory DB (Postgres + pgvector)..."
if docker info >/dev/null 2>&1; then
  docker compose -f "$SCRIPT_DIR/db/docker-compose.yml" up -d --wait >/dev/null 2>&1 \
    && echo "  ✓ harness-memory-db up on 127.0.0.1:5433" \
    || echo "  ✗ compose failed — run manually: docker compose -f $SCRIPT_DIR/db/docker-compose.yml up -d"
else
  echo "  → Docker daemon not running. Start it, then:"
  echo "    docker compose -f $SCRIPT_DIR/db/docker-compose.yml up -d"
fi

# --- Local embedding model prefetch ---
echo "[6/7] Local embedding model (no API key needed)..."
if grep -qE '^EMBED_PROVIDER=local' "$SCRIPT_DIR/harness.env" 2>/dev/null || [ ! -f "$SCRIPT_DIR/harness.env" ]; then
  uv run --directory "$SCRIPT_DIR/mcp/memory" python -c "
import warnings; warnings.simplefilter('ignore')
import embeddings; embeddings.embed('warmup')
print('  \u2713 ' + embeddings.MODEL + ' ready (dim ' + str(embeddings.DIM) + ')')
" 2>/dev/null || echo "  ! model prefetch failed — it will download on first use"
else
  echo "  = non-local EMBED_PROVIDER configured, skipping"
fi

# --- Config ---
echo "[7/7] Config..."
if [ ! -f "$SCRIPT_DIR/harness.env" ]; then
  cp "$SCRIPT_DIR/env.sample" "$SCRIPT_DIR/harness.env"
  chmod 600 "$SCRIPT_DIR/harness.env"
  echo "  → Created harness.env — FILL IN YOUR KEYS: $SCRIPT_DIR/harness.env"
else
  echo "  ✓ harness.env exists"
fi

# --- Global memory protocol (CLAUDE.md) ---
if ! grep -q "harness-memory-protocol" "$HOME/.claude/CLAUDE.md" 2>/dev/null; then
  cat "$SCRIPT_DIR/settings/CLAUDE-harness.md" >> "$HOME/.claude/CLAUDE.md"
  echo "  ✓ memory protocol appended to ~/.claude/CLAUDE.md"
else
  echo "  ✓ memory protocol already in ~/.claude/CLAUDE.md"
fi

echo ""
echo "=== Installation complete ==="
echo ""
echo "New in the harness:"
echo "  /mem           — semantic memory (save/find/cases/stats)"
echo "  /cross-review  — external GPT review with adversarial verification"
echo "  /debate        — structured debate vs external model"
echo "  /investigate   — on-chain fund tracing with persistent case memory"
echo ""
echo "Keys are OPTIONAL — memory and tracing work without any:"
echo "  OPENAI_API_KEY    — only for /cross-review and /debate"
echo "  ETHERSCAN_API_KEY — only for EVM chains in /investigate (BTC/Solana need none)"
echo "Restart Claude Code to pick up new MCP servers."
