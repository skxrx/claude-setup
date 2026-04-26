# Claude Blockchain Dev Framework

Portable Claude Code configuration for blockchain/crypto wallet development. Clone → install → go.

## Install

```bash
git clone <your-repo-url> ~/claude-setup
cd ~/claude-setup
./install.sh
```

## What's Inside

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

### Commands (13 slash commands)

| Command | What it does |
|---------|-------------|
| `/security-audit` | Full crypto security audit with STRIDE threat model |
| `/chain-add` | Add new blockchain support (full adapter) |
| `/chain-feature` | Add feature to existing chain adapter |
| `/implement` | Multi-agent orchestrated feature implementation |
| `/pipeline` | Custom agent pipeline with `→` and `[parallel]` syntax |
| `/review` | Parallel multi-agent code review |
| `/tdd` | Full TDD workflow (Red → Green → Refactor) |
| `/tdd-test` | Write tests only (RED phase) |
| `/tdd-implement` | Implement to pass existing tests (GREEN phase) |
| `/tdd-refactor` | Refactor with green tests (REFACTOR phase) |
| `/debug` | Systematic debugging framework |
| `/idea` | Product strategy brainstorming |
| `/threat-model` | STRIDE + attack tree threat modeling |

### MCP Servers (8)

**Active:** context7, crypto-price, cryptodata, phantom, docker  
**Disabled (need API keys):** alchemy, evm, postgres

### Hooks

- **Security alerts** — warns when crypto-critical files are modified
- **Secret protection** — blocks writes to `.env` and credential files
- **Publish guards** — warns on `npm publish` and `docker push`
- **Desktop notifications** — native OS notifications when tasks complete

## Structure

```
claude-setup/
├── agents/           # 11 specialized agent definitions
│   ├── blockchain-developer.md
│   ├── chain-adapter-engineer.md
│   ├── crypto-security-auditor.md
│   └── ...
├── commands/         # 13 slash commands
│   ├── security-audit.md
│   ├── chain-add.md
│   ├── pipeline.md
│   └── ...
├── settings/
│   ├── settings.json # MCP server configuration
│   └── hooks.json    # Security hooks
├── install.sh        # One-command installer
└── README.md
```

## Updating

Pull latest and re-run install:

```bash
cd ~/claude-setup && git pull && ./install.sh
```

The installer backs up existing `settings.json` and `hooks.json` before overwriting.
