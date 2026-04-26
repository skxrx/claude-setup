# TDD: Refactor Phase

Refactor the implementation for: $ARGUMENTS

Tests are green. Now improve the code without changing behavior.

## Checklist
1. Run tests — confirm green baseline
2. Look for:
   - Code duplication → extract shared functions
   - Poor naming → rename for clarity
   - Long functions → split into focused units
   - Missing types → add branded types, narrow unions
   - Performance → optimize hot paths (but profile first)
   - Security → verify crypto best practices
3. After EACH refactor step: run tests, confirm still green
4. If a test breaks — your refactor changed behavior. Revert and try differently.

## Output
- What was refactored and why
- All tests still passing
- Coverage report if available
