---
description: On-chain fund tracing and forensics. Use when the user asks where funds went, to trace stolen/leaked/drained money, investigate an address or tx, куда утекли/ушли средства, проследить адрес, расследование — even if /investigate was not typed explicitly.
argument-hint: <chain> <address> [case:<slug>] [hops:N]
---
# On-Chain Investigation (fund tracing)

Investigate: $ARGUMENTS

Forensic tracing of fund movements (stolen/leaked funds, suspicious flows).
All data is PUBLIC on-chain data. Purpose: recovery, exchange reports, evidence.

## Step 0: Parse & Recall

- Parse `$ARGUMENTS`: chain(s), address(es), optional case slug (`case:<slug>`), optional depth (`hops:N`, default 2).
- Call `harness-memory: recall` with the address(es) — if entities/flows already exist, load them via `trace` and `case_report` and CONTINUE the existing case instead of re-fetching everything.
- Open/reuse a case: `case_open(slug)`. Slug convention: `<what>-<yyyy-mm>` e.g. `drain-victim-2026-08`.

## Step 1: Fetch transaction history (curl, keys from ~/claude-setup/harness.env)

Load keys: `source <(grep -E '^(ETHERSCAN_API_KEY|TRON_PRO_API_KEY|HELIUS_API_KEY)=' ~/claude-setup/harness.env | sed 's/^/export /')`

**EVM (one Etherscan V2 key, 60+ chains).** chainid: 1 eth, 56 bsc, 137 polygon, 42161 arbitrum, 8453 base, 10 optimism, 43114 avax:
```
https://api.etherscan.io/v2/api?chainid={ID}&module=account&action=txlist&address={A}&sort=asc&apikey=$ETHERSCAN_API_KEY      # native
https://api.etherscan.io/v2/api?chainid={ID}&module=account&action=tokentx&address={A}&sort=asc&apikey=$ETHERSCAN_API_KEY     # ERC-20
```

**Bitcoin (no key):**
```
https://mempool.space/api/address/{A}/txs        # newest first, 25/page; ?after_txid= for paging
```
UTXO nuance: separate change outputs (back to sender cluster) from real spends before recording flows.

**TRON:**
```
https://api.trongrid.io/v1/accounts/{A}/transactions?limit=200              # TRX; header TRON-PRO-API-KEY optional
https://api.trongrid.io/v1/accounts/{A}/transactions/trc20?limit=200        # USDT-TRC20 etc.
```

**Solana (RPC https://api.mainnet-beta.solana.com, or Helius if key set):**
```
{"jsonrpc":"2.0","id":1,"method":"getSignaturesForAddress","params":["{A}",{"limit":100}]}
{"jsonrpc":"2.0","id":1,"method":"getTransaction","params":["{SIG}",{"encoding":"jsonParsed","maxSupportedTransactionVersion":0}]}
```
With HELIUS_API_KEY prefer `https://api.helius.xyz/v0/addresses/{A}/transactions?api-key=$HELIUS_API_KEY` (pre-parsed transfers).

Use `python3` for parsing/aggregation, not manual reading. Rate-limit: sleep 0.25s between explorer calls.

## Step 2: Analyze & Record

For each SIGNIFICANT movement (skip dust, skip obvious spam airdrops):
1. `entity_upsert` both sides. Label what you can identify:
   - exchange deposit pattern: fresh address receiving then forwarding to a known hot wallet
   - known labels: check Etherscan address tags via WebFetch of the address page if uncertain
   - mixers/bridges by known contract addresses
   - entity_type: victim | attacker | wallet | exchange | mixer | bridge | contract | service
2. `flow_add` with chain, tx_hash, amount, asset, block_time (ISO), investigation=slug.
   Cross-chain (bridge) hops: pass `to_address` as `chain:address` of the destination chain.

## Step 3: Follow the money

- Take endpoints from `trace(address, chain, direction=out)` after each recording round.
- Recurse into endpoints that are NOT terminal (terminal = exchange deposit, mixer, known service) up to the hop limit.
- STOP and ask the user before exceeding the hop limit or when a hop fans out to >20 addresses (peel chains / dusting).

## Step 4: Report

1. `case_report(slug)` for the full picture, then produce:
   - **Timeline** of flows (time, amount, from → to with labels)
   - **Mermaid flowchart** of the fund graph (victim red, exchanges green, mixers/bridges orange)
   - **Terminal endpoints table**: where funds sit now / where they went off-chain, with the exchange name if identified — these are the actionable leads (KYC subpoena targets)
   - **Gaps**: what could not be traced and why
2. `remember` a summary (topic=investigation, mtype=finding, investigation=slug, addresses=[key addresses]) — this is what makes the case resumable in any future session.

## Ethics & scope

- Public ledger data only. No doxxing of private individuals, no deanonymization beyond exchange/service attribution.
- If the user asks to investigate an address they do not plausibly own/represent as victim, ask about the purpose once, plainly.
