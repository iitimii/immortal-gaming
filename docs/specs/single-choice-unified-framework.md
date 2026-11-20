# `single_choice` Unified Finite Decision Framework Refactor Draft

This document describes how to refactor the `single_choice` system in the current repository into a "unified finite decision framework", so that it can serve both the existing LLM automatic selection and the player's button selection in roleplay mode.

This document is a technical breakdown of [avatar-roleplay-mode.md](</e:/projects/cultivation-world-simulator/docs/specs/avatar-roleplay-mode.md>), focusing on:

- Analysis of the current `single_choice` state
- General decision model design
- Decision source abstraction
- continuation / resume mechanism
- Integration with the roleplay runtime
- Incremental migration strategy

## 1. Background

The `single_choice` in the current repository already has a fairly good foundational abstraction:

- `SingleChoiceRequest`
- `SingleChoiceDecision`
- `SingleChoiceScenario`
- `resolve_single_choice(scenario)`

The typical call path is:

1. The business scenario constructs a scenario
2. The scenario generates a request
3. The engine calls the LLM to get a decision
4. The scenario applies the decision and returns an outcome

This structure is already clearly better than the old approach of "hand-writing an LLM prompt + parse + fallback in every business file".

However, after introducing roleplay mode, the existing structure exposes a key limitation:

- It assumes by default that "a decision must produce a result immediately"

A finite choice under player roleplay does not return immediately; instead it:

1. Creates a request
2. Suspends the current flow
3. Pauses the world
4. Waits for the player to click a button
5. Then resumes the original flow

In other words, the problem Phase 2 needs to solve is not "render the options as buttons", but upgrading `single_choice` from "a call style that gets a decision synchronously" to "a unified decision framework that supports suspend and resume".

## 2. Refactor Goals

The core goals of this refactor:

1. Keep the existing `request / decision / scenario` foundational model.
2. Extract the "decision source" out of business logic.
3. Allow the same choice scenario to be completed uniformly by:
   - LLM decision
   - Player roleplay decision
   - fallback decision
4. Introduce a unified continuation mechanism that supports resuming the original flow after waiting for the player.
5. Make concrete business scenarios responsible only for:
   - Defining the scenario
   - Constructing the request
   - Applying the decision
6. Do not make business scenarios responsible for:
   - Whether to show buttons
   - Whether to pause the world
   - Whether to go through the LLM
   - How to resume an interrupted flow

## 3. Non-Goals

This refactor explicitly does not aim to:

1. Tear down and rewrite all of `single_choice`'s data structures.
2. Migrate all existing choice scenarios directly in this round.
3. Mix free-form dialogue into this framework.
4. Build an "arbitrarily complex multi-step tree-branching story editor".
5. Let the frontend directly carry business logic decisions.

## 4. Current State Analysis

## 4.1 Current Model

The current core model lives in:

- `src/systems/single_choice/models.py`
- `src/systems/single_choice/scenario.py`
- `src/systems/single_choice/engine.py`

Existing key objects:

- `SingleChoiceOption`
- `SingleChoiceRequest`
- `SingleChoiceDecision`
- `SingleChoiceOutcome`
- `SingleChoiceScenario`

Current core entry points:

- `decide_single_choice(request)`
- `resolve_single_choice(scenario)`

## 4.2 Current Strengths

The current structure already has several clear strengths:

1. Business scenarios and the engine are separated.
2. `build_request()` and `apply_decision()` naturally form a two-stage structure.
3. The fallback policy has already been standardized.
4. The request content of each business scenario is relatively clear.

## 4.3 Current Limitations

There are three major current limitations:

### Limitation 1: The decision source is fixed to LLM/fallback

`resolve_single_choice()` currently defaults to:

1. build request
2. call LLM
3. fallback
4. apply

It does not treat "player roleplay" as a valid source.

### Limitation 2: The call semantics are "return immediately"

All current call sites assume:

- An outcome is obtained immediately after `await resolve_xxx(...)`

But a player decision does not return immediately; it spans multiple request cycles.

### Limitation 3: No continuation

There is currently no unified mechanism to represent:

- A choice scenario has already created a request
- The current flow has been suspended
- Where to resume after the player chooses

This means that without a refactor, the business layer would be forced to hand-write its own suspend logic.

## 5. Design Principles

## 5.1 The business layer only declares "there is a finite decision here"

The business side is only responsible for:

- Defining what this choice is;
- Providing the options;
- How to apply the result once a key is finally selected.

The business side is not responsible for:

- Who makes this choice;
- When to pause;
- How to resume.

## 5.2 The decision source is a framework-level concept

"Who makes the decision" should be a framework-level concept, not an `if roleplay ... else ...` scattered across the business layer.

## 5.3 continuation is core Phase 2 infrastructure

Without continuation, pause/resume logic can only be hardcoded scenario by scenario.  
Doing that would ultimately break the abstraction boundary of `single_choice`.

## 5.4 Allow incremental migration

This refactor cannot require all old scenarios to migrate together.  
The new framework must allow:

- Old logic to keep running;
- New logic to switch over one by one;
- Both call styles to coexist during the transition period.

## 6. Target Architecture

It is recommended to abstract the refactored `single_choice` into four layers:

### A. Scenario Layer

Responsibilities:

- Describe a concrete finite decision scenario;
- Produce a request;
- Apply a decision.

Typical interface:

- `build_request()`
- `apply_decision(decision)`

This layer keeps the existing `SingleChoiceScenario` conventions as much as possible.

### B. Resolver Layer

Responsibilities:

- Uniformly decide the decision source for this choice.

Candidate sources:

- `llm`
- `player_roleplay`
- `fallback`

This layer is the new core change.

### C. Continuation Layer

Responsibilities:

- When the resolver decides to hand this choice to the player, it is responsible for:
  - Creating the runtime pending request
  - Registering the continuation
  - Suspending the current flow
  - Resuming the flow after the player submits

### D. Runtime / Roleplay Integration Layer

Responsibilities:

- Manage the currently active roleplay session
- Manage the currently suspended choice continuation
- Expose query / command APIs

## 7. Proposed Data Model

## 7.1 ChoiceRequest

It is proposed to add a unified request model:

```python
@dataclass(slots=True)
class ChoiceRequest:
    request_id: str
    avatar_id: str
    task_name: str
    template_path: Path
    situation: str
    options: list[ChoiceOption]
    fallback_policy: FallbackPolicy
    context: dict[str, Any] = field(default_factory=dict)
    decision_mode: str = "auto"
```

Notes:

- It can evolve smoothly from the current `SingleChoiceRequest`;
- It is recommended to make `avatar_id` and `request_id` explicit, rather than relying only on runtime wrapping;
- `decision_mode` identifies the current mode, for example:
  - `auto`
  - `llm_only`
  - `roleplay_preferred`
  - `fallback_only`

## 7.2 ChoiceDecision

It is proposed to keep the current `SingleChoiceDecision` and extend it with source semantics:

```python
class DecisionSource(Enum):
    LLM = "llm"
    PLAYER_ROLEPLAY = "player_roleplay"
    FALLBACK = "fallback"
```

Proposed fields:

- `selected_key`
- `thinking`
- `source`
- `raw_response`
- `used_fallback`
- `fallback_reason`

## 7.3 ChoiceContinuation

It is proposed to add a continuation model:

```python
@dataclass(slots=True)
class ChoiceContinuation:
    continuation_token: str
    request_id: str
    avatar_id: str
    scenario_type: str
    created_at: float
    resume_handler: Callable[[ChoiceDecision], Awaitable[Any] | Any]
```

Note:

- `resume_handler` does not necessarily have to store an executable closure directly; the final implementation can switch to registry + token;
- But in terms of design semantics, there must be a single entry point that "resumes the original flow once a decision is obtained".

## 7.4 Runtime Pending Choice

It is recommended that the suspended data in the runtime include at least:

- `request_id`
- `avatar_id`
- `type = choice`
- `title`
- `description`
- `options`
- `continuation_token`

Of these:

- The frontend only needs `request_id/type/title/description/options`
- The continuation token need not be exposed directly to the frontend, but the runtime must keep it to resume the flow

## 8. Unified Call Chain

## 8.1 Current Call Chain

```text
business scenario
-> build_request
-> decide_single_choice
-> apply_decision
-> outcome
```

## 8.2 Target Call Chain

```text
business scenario
-> build_request
-> resolve_choice(scenario, runtime)
   -> choice resolver
      -> llm decision
      -> or player roleplay pending request
      -> or fallback
-> apply_decision
-> outcome
```

## 8.3 Expansion in Player Mode

```text
business scenario
-> build_request
-> resolve_choice(scenario, runtime)
   -> detect player-controlled avatar
   -> create pending roleplay choice request
   -> register continuation
   -> pause world
   -> suspend

player submits selected_key
-> submit_roleplay_choice
-> resolve continuation
-> reconstruct ChoiceDecision(source=PLAYER_ROLEPLAY)
-> scenario.apply_decision(decision)
-> continue original flow
```

## 9. Recommended Module Split

It is recommended to add or adjust the following modules:

- `src/systems/single_choice/models.py`
  - Extend the request / decision models
- `src/systems/single_choice/resolver.py`
  - Add `resolve_choice(...)`
- `src/systems/single_choice/continuation.py`
  - Manage continuation registration and resumption
- `src/systems/single_choice/engine.py`
  - Keep the LLM/fallback decision logic
- `src/server/services/roleplay_service.py`
  - Interface with the runtime / API

## 10. Resolver Design

## 10.1 `resolve_choice(...)`

Proposed entry point:

```python
async def resolve_choice(
    scenario: ChoiceScenario[OutcomeT],
    *,
    runtime,
) -> OutcomeT:
    ...
```

Responsibilities:

1. Build the request
2. Choose the decision source
3. Suspend and wait for resumption when necessary
4. Finally call `scenario.apply_decision(...)` uniformly

## 10.2 Source Determination Rules

Proposed rules:

1. If the request avatar is not the avatar currently being roleplayed by the player:
   - Go through the existing LLM/fallback flow
2. If the request avatar is the avatar currently being roleplayed by the player, and the current roleplay session allows choices:
   - Create a player choice request
   - Register the continuation
   - Suspend
3. If the roleplay session is unavailable or continuation registration fails:
   - Fall back to an explicit error or fallback, as controlled by the policy

## 10.3 Auto Accept Scenarios

Scenarios like `item_exchange.should_auto_accept()` that can be accepted automatically should not be forced into a continuation.

Proposed rules:

- If the business scenario can clearly determine the result automatically, construct a `ChoiceDecision` directly and apply it;
- Do not create a roleplay request.

## 11. Continuation Design

## 11.1 Why continuation is required

Because a lot of business logic continues executing after calling a choice, for example:

- Generating result events
- Appending story events
- Updating avatar state

If the player's choice does not return immediately, the original call chain needs a "resume point".

## 11.2 Storing Python closures directly in the persistence layer is not recommended

A continuation is a purely runtime object and does not go into the save file.

Recommendations:

- Maintain it only in memory;
- Manage it with token + registry;
- Clear it uniformly on load/reset/reinit.

## 11.3 Two Implementation Paths

### Path A: In-Memory Continuation Registry

Form:

- `continuation_token -> resume handler`

Pros:

- Most intuitive
- Best suited for fast delivery at the current stage

Cons:

- Lifecycle depends entirely on process memory
- Must be strictly cleaned up on reset/load

### Path B: Scenario Resume Descriptor

Form:

- The continuation stores only "scenario type + minimal necessary state"
- On resume, rebuild the scenario and then apply

Pros:

- More controllable
- Less direct dependency on closures

Cons:

- Requires designing a resume payload for each scenario

### Recommendation

Use Path B as the target direction, while allowing the implementation to transition temporarily through A.  
The reasons are:

- The repository is in the middle of structural consolidation;
- In the long run, descriptors are better for maintenance and testing than closures.

## 12. Integration with the Roleplay Runtime

## 12.1 Minimal Capabilities Needed in the Runtime

The runtime should support at least:

- Storing the current `RoleplayPromptRequest(type=choice)`
- Storing the currently active continuation token
- Querying the currently roleplayed avatar
- Retrieving the pending request after the player submits a choice

## 12.2 Responsibilities of the Submit Interface

`submit_roleplay_choice` should not carry business logic directly.

It should only be responsible for:

1. Validating request_id
2. Validating avatar_id
3. Retrieving the continuation
4. Generating `ChoiceDecision(source=PLAYER_ROLEPLAY)`
5. Calling the continuation to resume the original flow

In other words:

- The API layer is not responsible for "whether to actually sell the old weapon after ACCEPT is chosen"
- Those semantics still belong to scenario.apply_decision()

## 13. Impact on Existing Scenarios

## 13.1 `item_exchange`

This is the scenario best suited for the first migration batch.

Reasons:

- It already has a clear `ItemExchangeScenario`
- It already has `should_auto_accept()`
- Clear business boundaries
- Stable button options

Target migration approach:

- Have `resolve_item_exchange()` switch internally to `resolve_choice(...)`
- Keep `ItemExchangeScenario` basically unchanged

## 13.2 `sect_recruitment`

Also a fairly suitable scenario for the second migration batch.

Reasons:

- Simple option semantics
- No complex multi-layer follow-up logic

## 13.3 Mutual Action Responses

When migrating, these should preferably be wrapped into a unified scenario, rather than stuffing roleplay branches directly into each mutual action subclass.

Proposed direction:

- Convert `RESPONSE_ACTIONS` into `ChoiceRequest.options`
- Hand them uniformly to the resolver

## 14. Migration Strategy

A three-step migration is recommended:

### Step 1: Integrate the framework without changing old business logic

- Add `resolve_choice(...)`
- Add the continuation registry / descriptor
- Temporarily keep the old `resolve_single_choice(...)`

### Step 2: Migrate one validation scenario

- Migrate `item_exchange` first
- Get player choice -> continuation -> apply -> outcome working end to end

### Step 3: Gradually replace old entry points

- `sect_recruitment`
- Mutual action responses
- Other finite decision scenarios

## 15. Testing Recommendations

It is recommended to add the following tests:

1. `resolve_choice()` behaves the same as the old behavior in non-roleplay mode.
2. In roleplay mode, a pending choice request is created instead of calling the LLM immediately.
3. After the continuation resumes, the original scenario's `apply_decision(...)` is called.
4. After `item_exchange` is migrated, the auto-accept logic still works.
5. The continuation registry is cleared after load/reset/reinit.
6. Submitting an old request_id returns a stable error.
7. Simultaneous pending choices are not allowed to overwrite each other.

## 16. Conclusion

If Phase 2 wants to avoid the fragmented implementation of "hand-writing a set of player button logic at every business point", `single_choice` must be elevated into a unified finite decision framework.

The key to this refactor is neither the buttons nor the frontend, but:

- A unified abstraction of the decision source
- The continuation / resume mechanism
- The business layer being responsible only for scenario definition and decision application

Following this route, future one-off choices, invitation responses, and finite dialogues will all share a unified foundation, instead of devolving into an increasingly unmaintainable branching hell.
