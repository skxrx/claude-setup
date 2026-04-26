# Security Audit

Run a comprehensive security audit on: $ARGUMENTS

Launch the `crypto-security-auditor` agent with the following scope:

1. **Identify all files** in scope that touch key material, signing, secrets, or user funds
2. **Static analysis** — grep for dangerous patterns:
   - `Math.random`, `console.log` near sensitive data, `eval`, `any` in crypto paths
   - Unzeroed buffers, string copies of keys, plaintext storage
3. **Data flow trace** — follow key material from creation to destruction
4. **Dependency check** — audit crypto-related dependencies for CVEs and supply chain risks
5. **Threat model** — STRIDE analysis for the feature/module
6. **Output** structured report: CRITICAL / HIGH / MEDIUM / LOW / PASSED

If no specific target is given, audit the most recently changed files.
