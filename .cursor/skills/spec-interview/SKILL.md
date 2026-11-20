---
name: spec-interview
description: Conduct an in-depth interview to gather requirements and write a detailed specification (spec)
---

## Overview

Use `AskUserQuestion` to run an in-depth interview and thoroughly understand a feature, system, or idea before writing a spec.

## Core Principles

1. **Use your judgment** - Adjust the depth and focus of your questions to the topic. A small UI change needs different questions than a new authentication system.

2. **Ask non-obvious questions** - Skip surface-level questions. Probe for:
   - Hidden assumptions the user has not stated
   - Edge cases they have not considered
   - Trade-offs they are making implicitly
   - Constraints they forgot to mention
   - Failure modes and recovery paths

3. **Follow interesting threads** - When an answer reveals complexity or uncertainty, dig deeper before moving on.

4. **Challenge gently** - Ask "What if X fails?" or "Why not use Y instead?" to stress-test the design.

5. **Know when to stop** - End the interview once you have enough clarity to write a useful spec. Not every topic needs exhaustive coverage.

## Question Areas (use as needed, not as a checklist)

- **Problem and motivation**: Why now? What is the cost of not doing this?
- **Technical design**: Data model, state, API, performance, data migration
- **User experience**: Error states, loading, edge cases, accessibility
- **Integration**: What else does this affect? Security? Observability?
- **Trade-offs**: What are you **not** building? What technical debt are you accepting?
- **Risks**: Which assumptions might be wrong? What would make this project fail?

## Interview Flow

1. Start each round with 2-4 questions via `AskUserQuestion`.
2. Synthesize the answers and follow up on gaps or ambiguities.
3. Summarize periodically to confirm understanding.
4. When it is complete enough, confirm with the user and write the spec.

## Output

Write the spec to `docs/specs/<feature-name>.md` (or ask the user for a preferred path). Write it in English. Include whichever sections are relevant; do not force a rigid template.

## Invocation

```
/spec-interview [topic]
```
