# Threat Model

Build a threat model for: $ARGUMENTS

## Framework: STRIDE + Attack Trees

### 1. Define the scope
- What component/feature/flow is being modeled?
- What assets are at risk? (keys, funds, user data, session tokens)
- What are the trust boundaries?

### 2. STRIDE Analysis
For each component in the scope:
- **S**poofing — Can an attacker impersonate a user/service?
- **T**ampering — Can data be modified in transit/at rest?
- **R**epudiation — Can actions be denied without evidence?
- **I**nformation Disclosure — Can secrets leak?
- **D**enial of Service — Can the service be disrupted?
- **E**levation of Privilege — Can an attacker gain unauthorized access?

### 3. Attack Trees
For the top 3 highest-risk threats, build attack trees:
```
Goal: [attacker objective]
├── Path 1: [attack vector]
│   ├── Prerequisite: [what attacker needs]
│   └── Mitigation: [defense]
├── Path 2: [attack vector]
│   └── ...
```

### 4. Risk Assessment
Rate each threat: Likelihood (1-5) x Impact (1-5) = Risk Score

### 5. Mitigations
For each HIGH/CRITICAL risk, propose concrete mitigations with code examples.

## Output
Structured threat model document suitable for security review.
