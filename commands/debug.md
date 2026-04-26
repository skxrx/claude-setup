# Debug Issue

Debug: $ARGUMENTS

## Systematic Debugging Framework

### Step 1: Reproduce
- Understand the expected vs actual behavior
- Identify minimal reproduction steps
- Check if it's environment-specific

### Step 2: Isolate
- Narrow down to the specific module/function
- Check recent changes (git log, git diff)
- Add targeted logging/breakpoints (NEVER log sensitive data)

### Step 3: Root Cause
- Read the code path end-to-end
- Check for common crypto wallet bugs:
  - BigInt vs number precision loss
  - Nonce gaps or race conditions
  - RPC response format changes
  - Chain-specific quirks (gas estimation, UTXO selection)
  - Encoding mismatches (hex with/without 0x prefix)
  - Address format/checksum issues

### Step 4: Fix
- Write a test that reproduces the bug FIRST (TDD-style)
- Implement the minimal fix
- Run existing tests to verify no regression
- If security-related, flag for `crypto-security-auditor` review

### Step 5: Report
- Root cause
- Fix applied
- Test added
- Prevention: could this class of bug be prevented structurally?
