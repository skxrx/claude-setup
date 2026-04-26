# TDD Workflow Mode

You are now in **strict TDD mode**. Follow the Red-Green-Refactor cycle for every piece of functionality.

## Task: $ARGUMENTS

## Workflow

### Phase 1: RED — Write Failing Tests First
1. Analyze the task requirements
2. Break it into the smallest testable units
3. Write test files FIRST — cover:
   - Happy path
   - Edge cases
   - Error cases
   - For crypto code: security cases (key zeroing, timing attacks, invalid inputs)
4. Run the tests — they MUST fail (if they pass, tests are wrong)
5. Show the user the failing test output

### Phase 2: GREEN — Minimal Implementation
1. Write the MINIMUM code to make each test pass
2. No premature optimization, no extra features
3. Run tests after each implementation unit
4. Every test must pass before moving to next

### Phase 3: REFACTOR — Clean Up
1. Improve code quality without changing behavior
2. Extract common patterns, improve naming, reduce duplication
3. Run tests after each refactor step — must stay green
4. Use `senior-code-reviewer` agent for review if changes are significant

### Phase 4: VERIFY
1. Run full test suite
2. Check coverage — aim for >90% on business logic, 100% on crypto-critical paths
3. Report: tests written, tests passing, coverage, any concerns

## Rules
- NEVER write implementation before tests
- NEVER skip the failing test verification
- Each test-implement cycle should be small (one behavior per cycle)
- If you discover a new requirement during implementation, STOP and write a test for it first
- For TypeScript: tests must verify type safety too (expect compile errors for invalid usage)
- For crypto code: always include a test that verifies sensitive data is zeroed after use
