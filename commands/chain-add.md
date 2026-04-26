# Add Chain Support

Add support for new blockchain: $ARGUMENTS

Launch `chain-adapter-engineer` to implement the full adapter:

## Checklist

### 1. Research
- Chain model (UTXO vs account vs other)
- Address format and derivation path (BIP-44 coin type)
- Transaction format and serialization
- Fee model (gas, bandwidth, compute units, etc.)
- Native token + token standards (ERC-20, SPL, Jetton, TRC-20)
- RPC API documentation
- Testnet availability

### 2. Implement (TDD approach)
- [ ] Address derivation and validation
- [ ] Balance queries (native + tokens)
- [ ] Fee estimation (slow/medium/fast tiers)
- [ ] Transaction building
- [ ] Transaction signing (integrate with existing signer)
- [ ] Transaction broadcasting
- [ ] Transaction status monitoring
- [ ] Token operations (transfer, balance)

### 3. Test
- Unit tests: serialization, address validation, fee calculation
- Integration tests: testnet operations
- Property-based tests: address roundtrip, amount precision

### 4. Security Review
- Run `crypto-security-auditor` on the new adapter
- Verify derivation path correctness
- Verify signing security (deterministic nonce, no key leaks)

### 5. Documentation
- Chain-specific notes in adapter code
- RPC endpoints and fallbacks
- Known quirks and limitations
