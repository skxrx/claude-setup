---
description: External GPT second-opinion review with adversarial verification. Use when the user asks for a second opinion, external/independent review, кросс-ревью, or to check code/plan with GPT.
argument-hint: [files|diff scope] [focus]
---
# Cross-Model Review (GPT second opinion)

Review with an external independent model: $ARGUMENTS

## Step 1: Assemble material

- If a file/directory is given → read those files.
- If nothing given → `git diff` (unstaged + staged) or last commit if the tree is clean.
- Strip secrets/keys/tokens from the material before sending. NEVER send contents of .env, credentials, or seed material.

## Step 2: External review

Call `harness-second-opinion: review` with:
- `content`: the assembled diff/code
- `focus`: from $ARGUMENTS if specified (e.g. "security", "gas", "race conditions")
- `context`: 2-3 sentences on what the code is supposed to do and the stack

## Step 3: Adversarial verification (CRITICAL — do not skip)

The external model has NO codebase access — its findings are hypotheses.
For EVERY finding, verify against the actual code:
- Read the relevant code yourself.
- Verdict each finding: CONFIRMED (with file:line evidence) | REFUTED (why the model is wrong) | NEEDS-CONTEXT.
- A finding without a concrete failure scenario in OUR code is REFUTED.

## Step 4: Report

```
## Cross-review: <scope>
External model: <model> | Findings: N | Confirmed: X | Refuted: Y

## CONFIRMED
[severity] file:line — finding — failure scenario

## REFUTED (external model was wrong)
finding — why it does not apply here

## Disagreements worth the user's judgment
[cases where you and the external model disagree and both have a point]
```

## Step 5: Persist

For confirmed non-trivial findings, call `harness-memory: remember`
(topic=dev, mtype=finding, project=<repo>) so future sessions know.
