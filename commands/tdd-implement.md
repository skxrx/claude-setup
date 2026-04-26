# TDD: Implement to Pass Tests

Make the existing failing tests pass for: $ARGUMENTS

## Rules
1. Read ALL existing tests first to understand expected behavior
2. Write the MINIMUM implementation to make tests pass
3. Run tests after each logical unit of implementation
4. Do NOT modify existing tests (unless there's a genuine bug in the test)
5. Do NOT add functionality that isn't tested
6. If you find a gap in test coverage during implementation — note it but don't write new tests now

## Process
1. Run existing tests, identify all failures
2. Group failures by module/function
3. Implement one function at a time, run tests between each
4. When all tests pass — stop and report

## Output
- Implementation code
- Test run results (all green)
- Notes on any test gaps discovered
- Suggestion: run `/tdd-refactor` next
