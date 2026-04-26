# Add Feature to Existing Chain Adapter

Add feature to chain adapter: $ARGUMENTS

## Context
This is NOT a new chain — it's a new capability for an already supported chain.
Read the existing adapter code first to understand current implementation.

## Examples of chain features:
- Token standards (ERC-721, ERC-1155, SPL Token-2022, Jettons)
- RBF (Replace-By-Fee) for Bitcoin
- EIP-4337 Account Abstraction for EVM
- Staking/delegation support
- NFT operations
- Multi-sig / threshold signing
- L2 bridge integration
- New address types (Taproot, stealth addresses)
- Batch transactions (Multicall)
- MEV protection (private mempool submission)
- dApp interaction / WalletConnect

## Workflow

### Step 1: Understand Current State
1. Read the existing chain adapter fully
2. Identify the interface/types that need extending
3. Check if other adapters already implement similar feature (reuse patterns)

### Step 2: Design the Extension
- Extend existing types (don't break them — backward compatible)
- New types for the feature with branded identifiers
- Consider: does this affect fee estimation? Transaction building? Signing?

### Step 3: Implement (TDD preferred)
1. Write tests for the new feature
2. Extend adapter interface if needed
3. Implement the feature
4. Ensure existing tests still pass (no regression)

### Step 4: Validate
- Run `senior-code-reviewer` on changes
- If feature touches signing/keys → run `crypto-security-auditor`
- Test on testnet if applicable

## Key Principle
The adapter interface should grow incrementally. Use optional capabilities:
```typescript
interface ChainAdapter {
  // core — always present
  buildTransaction(...): Promise<Transaction>;
  
  // optional capabilities — check before use
  supportsRBF?: boolean;
  replaceTransaction?(...): Promise<Transaction>;
  
  supportsStaking?: boolean;
  stake?(...): Promise<Transaction>;
}
```
Or better — use a capability discovery pattern with discriminated unions.
