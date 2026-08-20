---
description: Persistent semantic memory (harness-memory MCP). Use whenever the user asks to remember/recall/запомни/вспомни something, references past decisions, investigations or prior sessions — or to manage memory (find, cases, stats, forget).
argument-hint: save <text> | find <query> | recent | map | cases | case <slug> | stats
---
# Semantic Memory (harness-memory)

Operate on the persistent semantic memory: $ARGUMENTS

## Subcommand routing

Parse `$ARGUMENTS`:
- starts with `save ` → call `harness-memory: remember` with the rest as content. Infer and fill `topic` (blockchain | trading | dev | investigation | general), `mtype` (note | decision | fact | finding | preference), `project` (git repo name) and `branch` (`git branch --show-current` — the work track is derived from it), `chain` (any chain the fact is about — aliases normalized) and `source` (docs URL / EIP / PR / tx hash if known). Extract crypto addresses and pass them via `addresses` as `chain:address` — a single distinct chain there is inferred automatically.
- starts with `find ` or is a bare query → call `recall`; pass `chain=`/`project=`/`track=`/`topic=` whenever the question is scoped ("про Solana", "в atomic-core", "по опенсорсу"). Present results ranked; mention superseded status only if `include_superseded` was requested.
- `map` → call `stats` and render the knowledge map (memories by topic / chain / project).
- `recent [topic]` → call `recent`.
- `forget <id>` → confirm with the user, then call `forget`.
- `cases` → call `case_list`.
- `case <slug>` → call `case_report`, render a readable case summary (timeline of flows + entities table + notes).
- `stats` → call `stats`.

## Rules

- Memory updates happen via `remember` — near-duplicates are superseded automatically, so ALWAYS prefer re-remembering an updated fact over editing prose elsewhere.
- When saving decisions, include the WHY in the content, not just the what.
- Never store secrets, seeds, or private keys in memory. Addresses and tx hashes are fine (public data).

## Proactive use (applies to every session, not just /mem)

At the END of any significant task, silently call `remember` for:
- decisions with rationale (mtype=decision)
- non-obvious findings about a codebase or chain behavior (mtype=finding)
- user preferences expressed as corrections (mtype=preference)

Before starting work on a topic that may have history (a chain integration, an investigation, a trading strategy), call `recall` first.
