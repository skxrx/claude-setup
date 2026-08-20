---
description: Structured debate vs external GPT model. Use when the user wants to challenge/validate an idea or decision, спор, валидация идеи, взвесить архитектурное решение with an independent opponent.
argument-hint: <question or thesis>
---
# Structured Debate (Claude vs external model)

Debate topic: $ARGUMENTS

Use this for architecture choices, protocol design questions, trading strategy
theses — anywhere a genuinely independent challenger beats self-review.

## Round 0: Recall

Call `harness-memory: recall` with the topic — prior decisions on this subject
constrain or inform the debate. Say so if they exist.

## Round 1: Position

Formulate YOUR position first, in writing: claim, key arguments, main risks
you already see. Be concrete — vague positions produce vague debates.

## Round 2: Attack

Call `harness-second-opinion: counter_position` with:
- `question`: the debate topic
- `position`: your full position from Round 1
- `context`: relevant constraints (stack, scale, team, chain specifics)

## Round 3: Adjudicate honestly

For each counter-argument:
- CONCEDE if it is right — update your position.
- REBUT with evidence if it is wrong.
- FLAG as "genuinely uncertain" if neither — these go to the user.

If the counter-arguments changed your position materially, run ONE more
`counter_position` round against the updated position. Max 2 rounds total.

## Round 4: Synthesis

```
## Debate: <topic>
Initial position: <one line>
Final position: <one line — may be the same, say if it changed and why>

## What the external model got right
## What it got wrong
## Open questions for the user
```

## Round 5: Persist

Call `harness-memory: remember` (mtype=decision) with the final position AND
the strongest counter-argument that was conceded or survived — that context is
what makes the memory useful later.
