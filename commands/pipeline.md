# Custom Agent Pipeline

Run a multi-agent pipeline: $ARGUMENTS

## You are a pipeline executor. Parse the user's intent and orchestrate agents.

### Input format examples:

```
/pipeline architecture-advisor → chain-adapter-engineer → senior-code-reviewer : Design and build Tron adapter
/pipeline [crypto-security-auditor, typescript-specialist] → senior-code-reviewer : Audit signing module
/pipeline blockchain-developer → crypto-security-auditor : Write and audit ERC-20 approval flow
```

### Syntax:
- `→` or `->` = sequential (output of left feeds into right)
- `[a, b, c]` = parallel (all run simultaneously)
- `:` separates pipeline from task description
- If no explicit pipeline given, infer the best agent chain from the task

### Execution:

1. Parse the pipeline definition
2. For each stage:
   - If single agent: launch it with full context (task + previous stage outputs)
   - If parallel group `[a, b]`: launch ALL in one message (actually parallel)
   - Collect outputs before proceeding to next stage
3. Each agent gets:
   - The original task description
   - Outputs/artifacts from all previous stages
   - Specific instructions for their part
4. Final output: consolidated result from all stages

### Rules:
- Always pass relevant context between stages — agents can't see each other
- Don't launch > 4 agents in parallel (context overhead)
- If the task is simple enough for 1 agent, just use 1
