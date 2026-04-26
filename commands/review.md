# Comprehensive Code Review

Review: $ARGUMENTS

## Parallel Multi-Agent Review

### Step 1: Identify scope
- If file/directory given → use that
- If feature/PR description given → find all relevant files
- If nothing given → use `git diff` to find recent changes

### Step 2: Classify files
Read all files in scope and classify:
- `crypto`: touches keys, signing, seeds, entropy, secrets
- `chain`: touches adapters, fee estimation, tx building, RPC
- `types`: complex generics, branded types, conditional types
- `db`: touches queries, migrations, schema
- `general`: everything else

### Step 3: Launch reviewers IN PARALLEL (one message, multiple Agent calls)

Always launch:
- `senior-code-reviewer` — full code review on ALL changed files

Additionally, based on classification:
- Has `crypto` files → also launch `crypto-security-auditor`
- Has `chain` files → also launch `chain-adapter-engineer` (for protocol correctness)
- Has `types` files with complex generics → also launch `typescript-specialist`
- Has `db` files → also launch `dba-specialist` (for query/schema review)

**Launch ALL applicable agents simultaneously.**

### Step 4: Consolidate

Merge all agent reports into one:

```
## Review Summary
[1-2 sentence overall verdict]

## CRITICAL (must fix)
[from all agents, deduplicated]

## HIGH (should fix)  
[from all agents, deduplicated]

## MEDIUM (consider)
[from all agents, deduplicated]

## Passed
[what's good across all reviews]
```

Remove duplicate findings. If agents disagree, note the disagreement with both perspectives.
