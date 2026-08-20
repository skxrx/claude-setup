# Claude Blockchain Dev Framework

Portable Claude Code harness for blockchain/crypto work: specialized agents,
slash commands, cross-model review (GPT), and persistent semantic + forensic
memory (Postgres/pgvector). Clone → install → go.

## Install

```bash
git clone <your-repo-url> ~/claude-setup
cd ~/claude-setup
./install.sh
# then fill in keys:
$EDITOR ~/claude-setup/harness.env
```

Requires: `uv`, Docker (OrbStack/Docker Desktop), `claude` CLI.

## What's Inside

### Harness (the new core)

| Piece | What it does |
|-------|-------------|
| `harness-memory` MCP | Semantic memory + investigation graph in Postgres/pgvector. **Runs fully offline, no API key** — embeddings are local (fastembed/ONNX, multilingual RU+EN). Hybrid search (vector + Russian-stemmed FTS + address matching). Memories auto-supersede near-duplicates (paraphrases included), so facts stay current instead of accumulating stale copies. |
| `harness-second-opinion` MCP | Independent review/debate via any OpenAI-compatible API (default: GPT). Three tools: `second_opinion`, `review`, `counter_position`. |
| `/mem` | save / find / recent / cases / stats over the memory DB |
| `/cross-review` | External GPT review of a diff, then Claude adversarially verifies every finding against the real code — only confirmed findings survive |
| `/debate` | Structured debate: Claude position → GPT counter-attack → honest adjudication → decision persisted to memory |
| `/investigate` | On-chain fund tracing (EVM 60+ chains via Etherscan V2, BTC, TRON, Solana). Entities/flows land in the memory DB; any future session reconstructs the case with `trace` / `case_report` |

### Memory model

One Postgres (port 5433), two layers that reference each other:

- **memories** — notes/decisions/findings with embeddings, plus the dimensions crypto work actually needs: `topic` (blockchain / trading / dev / investigation), `project`, `chain` (aliases normalized — `eth`/`sol`/`btc` collapse to canonical names, and a linked address infers the chain by itself), `source` (docs URL / EIP / PR / tx hash, because crypto facts go stale), `track` + `branch` (parallel work streams on one repo — derived from the git branch: anything containing "opensource" is the opensource track, everything else roadmap), `tags`. Updates supersede near-duplicates (similarity ≥ 0.90, paraphrases included) instead of duplicating — but **only within the same project + track + chain**, so an open-source truth can never silently overwrite a roadmap one, and `atomic-core` never collides with `atomicwallet-desktop`.
- **entities / flows / investigations** — labeled addresses (exchange, mixer, bridge, victim, attacker…) and fund-movement edges. Multi-hop, cross-chain tracing via recursive SQL — `trace(address)` rebuilds where funds went; `case_report(slug)` rebuilds the whole case.

Embeddings: **local by default** — `intfloat/multilingual-e5-large` via fastembed (ONNX, CPU, ~2.2GB downloaded once by the installer; ~35ms per embedding, ~3s model load per session). Cross-lingual: a Russian query finds an English memory. Switch to `openai`, `voyage` or `ollama` with one env line (`EMBED_PROVIDER`); the lighter local option is `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (dim 384, ~0.2GB).

If the embedding provider is ever unreachable, memory degrades gracefully instead of failing: writes and searches keep working on full-text + address matching, and `reindex_embeddings` backfills vectors once the provider is back.

### Agents (11)

| Agent | Purpose |
|-------|---------|
| `blockchain-developer` | Smart contracts, Solidity, DApps, DeFi protocols |
| `chain-adapter-engineer` | Multi-chain adapters, tx construction, fee estimation |
| `crypto-security-auditor` | Key management, signing, entropy, supply chain audit |
| `frontend-wallet` | React/RN wallet UI, secure inputs, transaction flows |
| `product-strategist` | Monetization, competitive analysis, feature prioritization |
| `architecture-advisor` | System design, refactoring, scalability |
| `typescript-specialist` | Type systems, generics, branded types |
| `integration-specialist` | External APIs, OAuth, webhooks, retry logic |
| `devops-infra` | Docker, K8s, CI/CD, monitoring, secrets |
| `dba-specialist` | PostgreSQL, Redis, migrations, indexing |
| `senior-code-reviewer` | Code review with crypto-specific security checklist |

### Autonomy

The harness is wired so it works without you invoking anything by hand:
- **memory is always live** — `harness-memory` is an MCP server, its tools are available in every session (no `/mem` required);
- **SessionStart hook** (`hooks/session-memory.sh`) reads the git repo and branch of the session, then injects only that repo's memories (track-labeled) plus open cases;
- **`~/.claude/CLAUDE.md` protocol** (appended by the installer) tells Claude to recall before work on chains/trading/investigations and remember decisions with rationale afterwards;
- **trigger-rich command descriptions** mean "куда ушли средства с 0x…" auto-invokes `/investigate` without typing the slash command.

### Commands (17 slash commands)

| Command | What it does |
|---------|-------------|
| `/mem` | Semantic memory operations |
| `/cross-review` | External GPT review + adversarial verification |
| `/debate` | Structured debate vs external model |
| `/investigate` | On-chain fund tracing with case memory |
| `/security-audit` | Full crypto security audit with STRIDE threat model |
| `/chain-add` | Add new blockchain support (full adapter) |
| `/chain-feature` | Add feature to existing chain adapter |
| `/implement` | Multi-agent orchestrated feature implementation |
| `/pipeline` | Custom agent pipeline with `→` and `[parallel]` syntax |
| `/review` | Parallel multi-agent code review |
| `/tdd` `/tdd-test` `/tdd-implement` `/tdd-refactor` | TDD workflow phases |
| `/debug` | Systematic debugging framework |
| `/idea` | Product strategy brainstorming |
| `/threat-model` | STRIDE + attack tree threat modeling |

### MCP Servers

**Harness:** harness-memory, harness-second-opinion (local, uv-run, fully auditable — no third-party agent code)
**Registered via `claude mcp add --scope user`:** context7, cryptodata, phantom, docker

### Hooks (merged into `~/.claude/settings.json`)

- **Security alerts** — warns when crypto-critical files are modified
- **Secret protection** — blocks writes to `.env` and credential files
- **Publish guards** — warns on `npm publish` and `docker push`
- **Desktop notifications** — native OS notifications when tasks complete

## Structure

```
claude-setup/
├── agents/                  # 11 specialized agent definitions
├── commands/                # 17 slash commands
├── mcp/
│   ├── memory/              # harness-memory MCP server (Python, uv)
│   └── second-opinion/      # harness-second-opinion MCP server
├── db/docker-compose.yml    # Postgres 17 + pgvector on 127.0.0.1:5433
├── settings/hooks.json      # hooks source (merged into settings.json)
├── env.sample               # copy to harness.env, fill in keys (git-ignored)
├── install.sh               # idempotent installer
└── README.md
```

## Keys (harness.env)

**Every key is optional.** Memory, investigations on BTC/Solana, and all agents/commands work with an empty `harness.env`.

| Key | Needed for | Without it |
|-----|-----------|-----------|
| `OPENAI_API_KEY` | `/cross-review`, `/debate` | those two commands are unavailable; everything else works |
| `ETHERSCAN_API_KEY` | EVM chains in `/investigate` (one key = 60+ chains) | BTC (mempool.space), Solana (public RPC) still traceable |
| `TRON_PRO_API_KEY` | higher TronGrid limits | TRON works at public rate limits |
| `HELIUS_API_KEY` | richer Solana parsing | public RPC fallback |
| `VOYAGE_API_KEY` | only if `EMBED_PROVIDER=voyage` | local embeddings are the default |

## Moving to another machine

The repo carries everything except two things:
1. `harness.env` — copy it manually (keys are never committed);
2. the memory DB content — `db/backup.sh` on the old machine, `db/restore.sh` on the new one after `./install.sh`.

## Updating

```bash
cd ~/claude-setup && git pull && ./install.sh
```

The installer is idempotent: it merges hooks into `settings.json` (preserving
your other settings, with a timestamped backup), skips already-registered MCP
servers, and leaves `harness.env` untouched.
