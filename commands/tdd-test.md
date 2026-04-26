# TDD: Write Tests Only

Write comprehensive tests for: $ARGUMENTS

Do NOT write any implementation. Only tests.

## Process
1. Read the existing code/interfaces to understand what needs to be tested
2. If no implementation exists yet — design the interface/API from the tests (test-first design)
3. Write tests covering:
   - **Happy path** — normal expected behavior
   - **Edge cases** — boundary values, empty inputs, max values
   - **Error cases** — invalid inputs, network failures, timeouts
   - **Security cases** (for crypto code) — key material handling, timing attacks, invalid signatures
   - **Concurrency cases** — if relevant (nonce management, parallel tx building)

## Test Quality Criteria
- Each test tests ONE thing
- Test names describe the behavior, not the implementation
- No test depends on another test's state
- No mocks for crypto operations — test real crypto
- Use fixtures/factories for complex test data
- BigInt for all amounts in tests too (no `0.1 + 0.2` surprises)

## Output
- Test files with clear organization
- Run them to confirm they fail (RED state)
- List what implementation is needed to make them pass
