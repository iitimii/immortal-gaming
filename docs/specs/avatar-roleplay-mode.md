# Avatar Roleplay Mode (Personal Mode) Design Notes

This document describes the complete design for "god's-eye view by default + the ability to take over a single avatar for roleplay", covering three phases of scope.

The goal is not to build an additional new mode parallel to god mode, but to introduce, on top of the existing framework for observing the world, viewing information, and controlling the passage of time, a lightweight, clear player roleplay capability that can be interrupted at "decision boundaries" rather than "in the middle of action execution".

## 1. Background and Goals

The current game's main experience is:

- The player observes the world from a god's-eye view.
- Avatars make decisions via AI and execute action chains by default.
- The player can intervene in limited ways via the system menu, avatar details, heavenly phenomena, and other interfaces.

This structure already suits "observation" and "light intervention", but it lacks a stronger form of immersion:

- The player can choose any avatar to roleplay.
- While roleplaying, the player still keeps full world information, rather than being downgraded to a traditional "first person in the fog".
- The player can enter intentions at key decision points, rather than being forced to issue commands one by one every month.

The core goals of this design:

1. The default is still the god's-eye view; there are no longer two separate global modes, "personal mode" and "god mode".
2. The player can choose an avatar to enter the roleplay state at any time, but can roleplay at most one avatar at a time.
3. While the player is roleplaying, the avatar may not be forcibly interrupted "while an existing action chain is executing".
4. Only when the avatar needs a new decision step does the world pause automatically and wait indefinitely for player input.
5. The roleplay state is purely runtime state; it does not go into the save file and does not change the existing save/load technical shape.
6. Phase 1 does "text decision takeover" first, Phase 2 does "one-off choices and invitation responses", and Phase 3 does "free-form dialogue".

## 2. Design Principles

### 2.1 The Default Is Still the God's-Eye View

This feature is positioned as "local avatar takeover under the god's-eye view", not a new global play mode.

Therefore:

- Even after entering the roleplay state, the player can still freely view the map, event panel, other avatars' details, sect situations, and other information.
- Information is not narrowed, and no extra UI restrictions based on the avatar's perception range are introduced.
- The player is not locked into an avatar camera or an avatar-exclusive page.

### 2.2 Pause at Decision Boundaries, Not in the Middle of Actions

The player cannot interrupt an action chain that has already started executing.

The only standard boundary at which pausing is allowed is:

- The currently roleplayed avatar has no action executing;
- And there are no pending planned actions to submit;
- And therefore a new round of decision needs to be produced.

This ensures:

- Consistency with the existing action chain model;
- The multi-step execution semantics inside actions are not broken;
- There is no need to implement "half-action rollback" or "changing minds mid-action".

### 2.3 Runtime Roleplay State Does Not Go into the Save

The roleplay state is a UI/Runtime layer state, not world state.

Therefore:

- It is not written into world;
- It is not written into the save file;
- It is cleared automatically after load, restart, reset, and reinit.

### 2.4 Reuse Existing Systems Instead of Building a Parallel One

This feature prioritizes reusing:

- The existing AI decision prompt and action chain loading mechanism;
- The existing `single_choice` system;
- The existing mutual action response action model;
- The existing event panel and detail panels;
- The existing `/api/v1/query/*` and `/api/v1/command/*` stable interface layering.

Inventing an additional "roleplay-only world loop", "roleplay-only event log", or "roleplay-only action engine" is not recommended.

### 2.5 Phase 2 Prioritizes a "General Finite Decision Framework" over Adding Buttons Scenario by Scenario

If Phase 2 proceeds by "adding a separate button UI + interface + pause point for each business point", it looks simple in the short term but will quickly get out of control in the long term:

- Every scenario has to repeatedly wire up pausing, resuming, state queries, button rendering, and error handling;
- The business layer will keep accumulating scattered branches like "if the player is roleplaying, show buttons, otherwise go through the LLM";
- Adding one-off choices, invitation responses, and finite dialogues later will reinvent the wheel.

Therefore the correct goal of Phase 2 is not "add a few more button scenarios", but:

1. Upgrade the existing `single_choice` into a unified "finite decision framework".
2. Treat "player roleplay" as a new decision source, not a new business system.
3. Let the business layer only declare "a finite decision is needed here", without caring whether this decision ultimately comes from the LLM, the player, or a fallback.

## 3. Non-Goals

This design explicitly does not include the following goals:

1. No traditional RPG-style information hiding or fog of war.
2. No roleplaying multiple avatars at the same time.
3. No forced command changes in the middle of action execution.
4. No general-purpose agent interface for "universal natural language control of every world object".
5. The roleplay state is not written into the save, and there is no requirement to restore the roleplay context after loading.
6. Phase 1 does not include full multi-turn free-form dialogue sessions.

## 4. Core Experience Overview

### 4.1 Player Perspective

The player's regular experience stays unchanged:

- The world runs normally;
- The player observes the map and events;
- The player opens an avatar's info panel.

A new "Roleplay Mode" section is added to the avatar info panel:

- Can enter roleplay;
- Can exit roleplay;
- If another avatar is already being roleplayed, a second avatar cannot be taken over at the same time.

After entering roleplay:

- A command-line-like input area appears at the bottom;
- The roleplayed avatar's recent event list is shown in that area;
- The event list content matches the result of filtering the right-side global event panel for that avatar.

### 4.2 Pause Behavior During Runtime

After entering roleplay, the world does not pause unconditionally right away.

The standard behavior should be:

1. If the avatar still has an action chain executing, the world advances as usual.
2. When the avatar's action chain finishes and a new decision is needed, the system automatically enters the "waiting for player input" state.
3. After entering that state, the world pauses automatically and waits indefinitely for the player to submit a decision.
4. After the player submits successfully, the system loads the avatar's new action chain and resumes the world.

### 4.3 Information Display

In the roleplay state, two kinds of information should be displayed at the same time:

- Global information: world time, other avatars, the map, the global event panel, sect situations;
- Local information: the currently roleplayed avatar's event stream, the prompt for the decision currently awaited, and the input box or option buttons.

### 4.4 Exit Behavior

The player should be able to exit roleplay voluntarily.

After exiting:

- The avatar returns to AI control;
- When a decision is needed again later, the player is no longer waited on;
- If exiting while in the waiting-for-player-input state, after confirmation the AI decision should resume or the waiting request should be released.

## 5. Three-Phase Scope

## 5.1 Phase 1: Text Decision Takeover

Phase 1 only solves "when the avatar needs a new step of action planning, the player enters a text intention".

### Phase 1 Includes

- Entering/exiting the roleplay state.
- Roleplaying at most one avatar at a time.
- Pausing the world after the avatar's action chain finishes and waiting for player input.
- The player enters the next intention via text.
- The server reuses the existing decision prompt to convert player input into an action chain.
- The right-side global event panel keeps working.
- The avatar's local event stream is shown in the info panel.

### Phase 1 Excludes

- One-off choice buttons;
- Invitation accept/decline buttons;
- Multi-turn free-form dialogue;
- Inserting new decisions in the middle of an action chain;
- A complex "editable plan queue UI".

### Phase 1 Prompt Constraints

Player input is an "intention description", not a direct internal action DSL.

The server should add the following constraints to the prompt:

- Prioritize generating a reasonable action chain based on the player's intention;
- If the player asks to go to a location unknown to the avatar, do not error; instead automatically convert it into "explore / head toward an explorable direction" behavior;
- If the player's intention does not satisfy current conditions, generate the closest executable action chain;
- Keep the safety constraints, world rules, and action legality checks of the current AI decision prompt.

## 5.2 Phase 2: One-Off Choices and Two-Person Event Invitations

Phase 2 handles scenarios that are "essentially not free-text planning but finite-option decisions".

### Phase 2 Includes

- Upgrading the existing `single_choice` system into a unified "finite decision framework".
- Exposing one-off choice scenarios as option buttons rather than a text box.
- Hooking invitation responses in two-person/multi-person interactions into the same decision framework, rather than writing dedicated button logic for each action.
- The frontend only needs to render a unified `choice` request; each business point is not required to have its own UI.

### Phase 2 Sources

Prioritize reusing existing mechanisms:

- `single_choice`
- mutual action `RESPONSE_ACTIONS`

Phase 2 is not a redesign of the choice system; it hands the "finite decision slots" originally handled by the LLM or fixed logic over to the player when "the currently roleplayed avatar is the decision subject".

More precisely, the core of Phase 2 is not "buttons", but:

- Unified modeling of `single_choice` requests;
- Unified resolution of decision sources;
- Unified hosting of pause/resume for player choices;
- Unified frontend rendering of `choice`-type requests.

### Phase 2 Limitations

- Long-text free-form dialogue is still not supported.
- Multiple roleplayed avatars waiting on different choices at the same moment is still not supported.
- The number of buttons should be kept restrained, preferring binary or limited options, without a complex tree-shaped dialogue UI.
- Phase 2 does not aim to hook up all existing scenarios in one go; the general framework should be completed first, and then specific business logic migrated to the unified entry point step by step.

## 5.3 Phase 3: Free-Form Dialogue

Phase 3 handles the complex scenario of "the avatar as a social subject having multi-turn dialogue with other avatars".

### Phase 3 Goals

- The player can roleplay the avatar and speak freely within a dialogue context.
- Multiple consecutive rounds of interaction are possible until the player actively ends it.
- The dialogue result is ultimately compressed into an abstract narrative event, rather than pouring the entire raw chat log into the long-term event stream.
- Dialogue must be triggered by attaching to the existing `Conversation` action; no "free chat entry point detached from world action semantics" is added.
- In the dialogue, only the player's roleplay side is entered by the player; the other side is still answered by the LLM.

### Capabilities Phase 3 Must Add

- An independent "conversation session state";
- Conversation turn caching;
- A summary service after the dialogue ends;
- Writing the summary result into the event system.

### Phase 3 Event Landing Rules

No matter how many rounds of chat occur in between, what ultimately enters the event panel should be:

- A narrative summary;
- Related avatar IDs;
- Necessary emotion/relationship/follow-up action effects.
- An optional story extension event;

Long-term storage of the raw turn-by-turn dialogue text in the event store is not recommended, to avoid:

- Flooding the event panel;
- Storage bloat;
- Excessive cost of repeatedly injecting context later.

## 6. Terminology and State Definitions

To avoid cramming multiple semantics into a single `is_paused` boolean, introducing finer-grained runtime concepts is recommended.

### 6.1 Roleplay Session

Proposed runtime object:

- `RoleplaySession`

Proposed fields:

- `controlled_avatar_id: str | None`
- `status: inactive | observing | awaiting_decision | awaiting_choice | conversing | submitting`
- `pending_request: dict | None`
- `started_at: float | None`
- `last_prompt_context: dict | None`
- `conversation_session: dict | None`

Semantics:

- `inactive`: no avatar is currently being roleplayed.
- `observing`: the avatar is being roleplayed, but the world is not yet blocked waiting for the player.
- `awaiting_decision`: waiting on a Phase 1 text decision.
- `awaiting_choice`: waiting on a Phase 2 option.
- `conversing`: in a Phase 3 free-form dialogue session.
- `submitting`: the frontend has submitted and the server is parsing or loading the result.

### 6.1.1 Phase 3 Conversation Session State

Proposed new runtime field in `RoleplaySession`:

- `conversation_session`

Proposed fields:

- `session_id`
- `request_id`
- `avatar_id`
- `target_avatar_id`
- `initiator_avatar_id`
- `status: awaiting_player | generating_reply | awaiting_continue | completed | cancelled`
- `messages`
- `started_at`
- `last_summary`

Semantic requirements:

- This structure is purely runtime state; it is not written into world and not written into the save;
- `messages` stores the turn-by-turn chat log of this session, used only for this dialogue's context and the post-dialogue summary;
- `last_summary` is only a temporary cache of this round's end state and is not a long-term source of facts.

### 6.2 Pause Reasons

It is recommended to elevate "pause" from a single boolean to "aggregate state + reasons".

Proposed additions:

- `pause_reasons`
- `pause_reason_detail`

Candidate reasons include:

- `manual_pause`
- `init_pending`
- `auto_control_no_client`
- `roleplay_waiting_decision`
- `roleplay_waiting_choice`
- `roleplay_conversation`

Aggregation rules:

- As long as any blocking pause reason exists, `is_paused = true`.
- The UI should show the most important current reason, rather than only showing "Paused".

### 6.3 Roleplay Request

Proposed unified abstraction:

- `RoleplayPromptRequest`

Proposed fields:

- `request_id`
- `type: decision | choice | conversation`
- `avatar_id`
- `target_avatar_id`
- `title`
- `description`
- `context`
- `options`
- `messages`
- `can_end`
- `created_at`

Of these:

- `decision` corresponds to Phase 1 text input;
- `choice` corresponds to Phase 2 button selection;
- `conversation` corresponds to Phase 3 session input.

Phase 3 constraints:

- A `conversation` request must be bound to a `Conversation` action that is already in progress;
- The frontend is not allowed to create a free chat session out of thin air, detached from the action chain;
- `messages` is used only for rendering the current session in the frontend and does not enter formal event storage.

### 6.4 General Finite Decision Request

It is recommended to explicitly introduce unified concepts in Phase 2:

- `ChoiceRequest`
- `ChoiceDecision`
- `ChoiceResolver`

Of these, `ChoiceRequest` can evolve directly from the existing `SingleChoiceRequest`.

Proposed fields:

- `request_id`
- `avatar_id`
- `task_name`
- `template_path`
- `situation`
- `options`
- `fallback_policy`
- `context`
- `decision_mode`

Semantic notes:

- `request_id`: runtime unique identifier;
- `avatar_id`: the current decision subject;
- `task_name/template_path`: compatible with the current LLM decision chain;
- `situation/options/fallback_policy/context`: carried over from the current `single_choice` model;
- `decision_mode`: marks whether the current mode is `llm`, `roleplay_player`, `fallback_only`, etc.

### 6.5 Decision Source

It is recommended to abstract "where the decision comes from" uniformly as:

- `DecisionSource`

Phase 2 includes at least:

- `llm`
- `player_roleplay`
- `fallback`

Key principles:

- The business layer does not directly check "whether the player is currently roleplaying";
- The business layer only creates the request and hands it to the unified resolver;
- The resolver then decides, based on the current runtime/session, who completes this decision.

### 6.6 Continuation / Resume Token

The biggest technical difficulty in Phase 2 is not button rendering, but "how to resume the original business flow after pausing".

Many current `single_choice` scenarios directly `await resolve_xxx()` within an asynchronous settlement flow:

1. Build the request
2. Get the decision immediately
3. Apply immediately
4. Continue with subsequent logic

If that decision is instead provided by the player, a cross-tick / cross-request wait appears in the middle.  
Therefore unified continuation semantics need to be introduced.

Proposed field:

- `continuation_token`

Its responsibility is not to be exposed to the frontend for business decisions, but to:

- Identify which suspended decision continuation this choice corresponds to;
- Resume the flow that was originally waiting on the decision after the player submits;
- Avoid the business layer hand-writing scattered "suspend half a settlement flow" logic.

## 7. Phase 1 Detailed Flow

### 7.1 Starting Roleplay

The player clicks "Start Roleplay" in the avatar info panel:

1. The backend checks whether an avatar is already being roleplayed.
2. If one exists and it is not the current avatar, reject and return an explicit error.
3. If the current avatar is valid, create/update the `RoleplaySession`.
4. If the avatar already has an action chain at this point, `status = observing`.
5. If the avatar is already at the decision boundary of "no current action and no plan", immediately create a `pending_request` and enter the waiting state.

### 7.2 Triggers During World Advancement

In the simulator's "fill in decisions" phase, if an avatar is detected that satisfies:

- It is the currently roleplayed avatar;
- Its current action is empty;
- Its planned actions are empty;

then instead of going through the normal LLM decision, it:

1. Creates a decision request;
2. Records it in the runtime's roleplay session;
3. Sets the corresponding pause reason;
4. Ends further advancement of the current tick or stops in the next loop iteration.

### 7.3 Player Submits a Text Intention

Example player input:

- Go explore nearby for opportunities
- Find someone to talk to and see if we can become friends
- First regulate breathing to recover, then continue the breakthrough

Backend handling:

1. Validate that the current `pending_request` is still valid.
2. Validate that the avatar the submitter targets matches the currently roleplayed avatar.
3. Call the "player decision to action chain" service.
4. The service reuses the AI prompt and action legality checks.
5. On success, load the result into the avatar's planned actions.
6. Clear the `pending_request` and the corresponding pause reason.
7. Switch the session status back to `observing`.

### 7.4 Invalid Player Input

Invalid input should not directly resume the world.

It should prioritize:

1. Returning an error or hint message;
2. Keeping the world paused;
3. Allowing the player to continue entering input.

If the model generates a non-executable action chain, the existing legality filtering logic applies; if ultimately there is no valid action, it should return to the waiting state and give a clearer failure hint.

## 8. Phase 2 Detailed Flow

Proceeding in Phase 2 by "temporarily adding a button entry point for one scenario first" one by one is not recommended.  
It is recommended to first refactor `single_choice` into a unified finite decision framework, then gradually migrate existing business scenarios.

### 8.1 Overall Phase 2 Goals

Phase 2 should first complete the following framework goals:

1. Unify the `build request -> resolve -> apply` flow.
2. Unify the finite decision sources:
   - LLM
   - Player roleplay
   - fallback
3. Unify the `choice` suspended state in the runtime.
4. Unify the frontend choice request display and button submission flow.
5. Unify the continuation / resume mechanism.

### 8.2 `single_choice` Refactor Direction

The current `single_choice` already has two good foundations:

- A clear request model;
- The scenario has a natural two-stage structure of `build_request()` and `apply_decision()`.

It is recommended not to tear down the existing structure, but to upgrade on top of it:

#### Current Model

- `SingleChoiceScenario.build_request()`
- `decide_single_choice(request)`
- `resolve_single_choice(scenario) -> decision -> apply`

#### Target Model

- `ChoiceScenario.build_request()`
- `resolve_choice(request, runtime, scenario)`
- `ChoiceResolver` decides to:
  - Call the LLM directly
  - Hand it to the player and suspend
  - Use the fallback
- After obtaining the `ChoiceDecision`, call `scenario.apply_decision(...)` uniformly

In other words, the business layer keeps the responsibility of "build request + apply decision", but is no longer responsible for "where this decision comes from".

### 8.3 Proposed Unified Entry Point

It is recommended to add a unified entry point, for example:

- `resolve_choice(scenario, runtime)`

Its behavior should be:

1. Call `scenario.build_request()`
2. Determine whether the current request's avatar is the player's roleplay target
3. If it is not the player's roleplay target:
   - Keep using the current LLM/fallback flow
4. If it is the player's roleplay target:
   - Create `RoleplayPromptRequest(type=choice)`
   - Write it into the runtime
   - Enter the waiting state
   - Suspend the current flow via the continuation token
5. After the player submits:
   - Resume that flow
   - Construct a unified `ChoiceDecision`
   - Call `scenario.apply_decision(...)`

### 8.4 One-Off Choices

When the roleplayed avatar encounters a finite choice scenario:

When the roleplayed avatar encounters a `single_choice` scenario:

1. If the avatar is not being roleplayed by the player, keep the existing automatic logic.
2. If the avatar is being roleplayed by the player, the unified `ChoiceResolver` takes over.
3. The Resolver creates `RoleplayPromptRequest(type=choice)`.
4. The world pauses and the frontend shows unified option buttons.
5. After the player clicks a button, the system resumes that choice continuation.
6. After resuming, `scenario.apply_decision(...)` is called uniformly.

### 8.5 Two-Person Invitation Responses

When the roleplayed avatar is the responder of a mutual action:

1. If the action exposes finite `RESPONSE_ACTIONS`;
2. Then those responses should preferably be wrapped into a unified `ChoiceRequest`;
3. Rather than hardcoding "which buttons to show in player mode" directly in the action class;
4. After the player selects, resume still goes through the unified resolver -> continuation -> apply flow.

### 8.6 Recommended Migration Order for Existing Scenarios

Migrating all finite choice scenarios at once is not recommended. The following order is recommended:

1. `item_exchange`
   - "Keep or sell/replace" after obtaining a new item from alchemy, fortunes, spoils, etc.
   - Reason: the existing `single_choice` structure is the most complete and has the highest validation value
2. `sect_recruitment`
   - Clear semantics, stable buttons
3. Finite responses of mutual actions
   - `Accept / Reject`
   - `Yield / Reject`
   - `Talk / Reject`

### 8.7 Relationship Between Phase 2 and Phase 1

Phase 2 does not replace Phase 1; it adds another request type:

- Text decisions continue to be used for open-ended intentions;
- Option buttons are used for finite responses.

The two share:

- roleplay session;
- pause reason;
- prompt request;
- The frontend prominent prompt container.

At a higher level, both belong to:

- "Unified avatar decision request"

It is just that:

- Phase 1 is open-ended text decision;
- Phase 2 is finite-option decision.

## 9. Phase 3 Detailed Flow

### 9.1 Trigger Principle

Phase 3 dialogue must be triggered by attaching to the existing `Conversation` action.

Adding a standalone entry point where "the player clicks a button to chat freely with any avatar" is not recommended.  
Reasons:

1. `Conversation` is already a formal action semantic in the world;
2. This keeps the semantics of action chains, events, relationship changes, and the story system consistent;
3. It avoids the disconnect of "a chat happened in the UI, but there is no corresponding action in the world".

Therefore the recommended path is:

1. Through a Phase 1 text decision or Phase 2 finite response, the player has the avatar execute a `Talk` / `Conversation` related action;
2. When the action chain advances to `Conversation`:
   - If not currently roleplayed by the player: keep using the existing AI dialogue logic;
   - If currently roleplayed by the player: enter a Phase 3 `conversation`-type request;
3. After the dialogue ends, the `Conversation` action completes and enters settlement.

### 9.2 Conversation Session Start

When the `Conversation` action detects that "the current dialogue subject is the player-roleplayed avatar":

1. Create `RoleplayPromptRequest(type=conversation)`;
2. Build the `conversation_session`;
3. Enter the `conversing` state;
4. Pause the world;
5. Switch the bottom dock to the chat interface.

### 9.3 Multi-Turn Chat

During multi-turn dialogue, a one-sided takeover mode of "the player inputs one side, the target avatar is answered by the LLM" is used.

This means:

- The player only controls the speech of the currently roleplayed avatar;
- The other avatar is not played by the player, and two-sided manual input is not supported;
- Each time the player sends a line, the system generates one reply line from the target avatar;
- Turns are appended to the runtime `messages`;
- Raw messages are not written directly into the formal event system.

### 9.4 Phase 3 Prompt Design

Phase 3 needs a separate conversation prompt; reusing the Phase 1 open-ended action planning prompt is not recommended.

It is recommended that the prompt context be split into at least four sections:

1. Information about both avatars
   - Name, realm, alignment, relationship, current state, recent goals
2. Summary of historical interactions
   - Recent shared events
   - Relationship changes
   - Important past exchanges
3. Context of this conversation
   - Who initiated it
   - Why it started
   - Location
   - Current time
4. Preceding text of this round
   - The most recent several rounds of message history

It is recommended that the LLM output a fixed structure:

- `reply_content`
- `speaker_thinking`
- `conversation_state`
- `summary_hint`
- `relation_hint`

Additional constraints:

- The LLM cannot end the session on its own;
- The right to end the session belongs only to the player explicitly clicking "End Conversation";
- If the LLM thinks the topic is exhausted, it can express "suitable to wrap up" via `conversation_state` or `summary_hint`, but must not terminate directly.

### 9.5 Ending the Conversation

The player has the final say on ending.

Allowed ways to end:

- The player actively clicks "End Conversation";
- Forced interruption caused by the target avatar becoming invalid, dying, leaving, etc.

Not allowed:

- The LLM autonomously deciding to end the conversation.

After ending:

1. Call the summary service;
2. Generate a summary event;
3. Optionally generate a relationship change hint;
4. Optionally generate a story extension event;
5. Clear the temporary conversation cache;
6. Return to `observing` or continue the subsequent action chain.

### 9.6 Summary Design

It is recommended that the Phase 3 summary service output three layers of results:

1. `conversation_brief_summary`
   - For the event panel
   - One to two sentences of narrative text
2. `conversation_relation_hint`
   - For relationship change calculation
   - Can be a structured hint
3. `conversation_story_hint`
   - For subsequent story event extension
   - Optional

Of these:

- The formal event stream writes at least `conversation_brief_summary`;
- The raw chat log does not enter long-term event storage;
- The summary itself is also not required to go into the save; the final long-term facts are the events and relationship change results after they are stored.

## 10. Backend Architecture Recommendations

## 10.1 New Service Modules

It is recommended to add independent services rather than continuing to pile logic back into `src/server/main.py`:

- `src/server/services/roleplay_service.py`
- `src/server/services/roleplay_queries.py`
- `src/server/services/choice_resolver.py`
- `src/server/services/choice_continuation.py`

Proposed responsibilities:

- Manage the `RoleplaySession` lifecycle;
- Create, read, and clear `RoleplayPromptRequest`;
- Execute player submissions;
- Handle invalid avatars, exits, and conflict detection;
- Provide runtime query DTOs.

Of these, the proposed new Phase 2 responsibilities are:

- `choice_resolver.py`
  - Decide whether a given finite decision is completed by the LLM, the player, or a fallback
- `choice_continuation.py`
  - Manage suspension and resumption when taken over by the player

## 10.2 Runtime Layer Extensions

It is recommended to extend the current runtime session with:

- roleplay session state;
- pause reasons;
- Unified pause aggregation logic.

Do not scatter this state across:

- One-sided assumptions in a frontend local store;
- The world object;
- Module-level global variables.

## 10.3 Decision Injection Point

The best injection point for Phase 1 should be where "an avatar needs a decision filled in", not inside the action execution layer.

Recommended locations:

- The simulator decision phase;
- Or the service/adapter called from above it.

The goal is to achieve:

- For the roleplayed avatar: switch to creating a `pending_request`;
- For non-roleplayed avatars: keep the existing `llm_ai.decide(...)`.

### 10.4 Phase 2 Finite Decision Injection Point

Phase 2 injection points should not be scattered across each business scenario, each with its own `if roleplay then ...`.

It is recommended to unify them in:

- The unified entry-point resolver of `single_choice`

In other words:

- Business logic is only responsible for `build_request` and `apply_decision`
- The resolver is responsible for deciding whether to switch to a player choice request
- The continuation is responsible for resuming the original flow

## 10.5 Phase 3 Summary Service

For Phase 3 it is recommended to additionally add:

- `src/server/services/roleplay_conversation_summary.py`
- `src/server/services/roleplay_conversation_service.py`

Responsibilities:

- `roleplay_conversation_service.py`
  - Create / read / advance the `conversation_session`
  - Handle the player sending a line
  - Call the LLM to generate the target avatar's reply
  - Trigger the summary on end
- `roleplay_conversation_summary.py`
  - Receive temporary conversation turns
  - Output narrative event text
  - Control summary length and style
  - Provide relationship / story hints
  - Not directly coupled to the UI layer

## 11. API Design Recommendations

This feature should follow the existing public v1 query/command layering.

## 11.1 Query

Proposed additions:

### `GET /api/v1/query/roleplay/session`

Returns the current roleplay session:

- The currently roleplayed avatar;
- The current status;
- The current pending request;
- The current pause reason;
- Whether submission is allowed;
- Recent avatar event filter parameters.

### Extending `GET /api/v1/query/runtime/status`

Proposed additions:

- `pause_reason`
- `pause_reason_detail`
- `roleplay_status`
- `roleplay_avatar_id`

This way the frontend top status bar and prominent prompt layer can directly reuse runtime status, instead of stitching together results from multiple interfaces.

## 11.2 Command

Proposed additions:

### `POST /api/v1/command/roleplay/start`

Request:

- `avatar_id`

Behavior:

- Start roleplaying the specified avatar;
- If another avatar is already being roleplayed, return a conflict error.

### `POST /api/v1/command/roleplay/stop`

Request:

- Can be empty, or include `avatar_id` for a consistency check.

Behavior:

- End the current roleplay;
- Clear the pending request;
- Clear the roleplay pause reason.

### `POST /api/v1/command/roleplay/submit-decision`

Request:

- `request_id`
- `avatar_id`
- `command_text`

Behavior:

- Convert the player's text into an action chain and load it.

### `POST /api/v1/command/roleplay/submit-choice`

Used in Phase 2:

- `request_id`
- `avatar_id`
- `selected_key`

Notes:

- This interface should not carry business semantics directly;
- It is only responsible for handing "which key the player selected" back to the unified continuation;
- The continuation resumes the original flow and calls the corresponding scenario's `apply_decision(...)`.

### `POST /api/v1/command/roleplay/conversation/send`

Used in Phase 3:

- `request_id`
- `avatar_id`
- `message`

Behavior:

- Append the player's line for this turn to the `conversation_session`
- Call the conversation prompt to generate the target avatar's reply
- Return the latest message list or the latest incremental messages
- Keep the world paused

### `POST /api/v1/command/roleplay/conversation/end`

Used in Phase 3:

- Actively end the conversation and trigger the summary.

Behavior:

- Only allowed to be triggered explicitly by the player;
- Trigger the summary;
- Complete the `Conversation` action;
- Clear the runtime conversation cache.

## 11.3 Error Code Recommendations

It is recommended to explicitly define several stable errors:

- `ROLEPLAY_ALREADY_ACTIVE`
- `ROLEPLAY_AVATAR_NOT_FOUND`
- `ROLEPLAY_TARGET_MISMATCH`
- `ROLEPLAY_REQUEST_NOT_FOUND`
- `ROLEPLAY_REQUEST_EXPIRED`
- `ROLEPLAY_SUBMIT_NOT_ALLOWED`
- `ROLEPLAY_CONVERSATION_NOT_ACTIVE`

## 12. Frontend Design Recommendations

## 12.1 Info Panel Mount Point

The mount point is recommended to be inside the avatar info panel, but as an independent child component, rather than stuffing all the logic into the current detail component.

Proposed addition:

- `web/src/components/game/panels/info/components/RoleplayPanel.vue`

Main responsibilities:

- Show whether roleplay can currently be entered;
- Show the enter/exit buttons.

The main interaction surface for Phase 3 is no longer inside the avatar info panel, but continues to use the bottom dock of the main interface.

## 12.2 Store

Proposed addition:

- `web/src/stores/roleplay.ts`

Responsibilities:

- Fetch/cache the current roleplay session;
- Handle start/stop/submit;
- Manage in-progress submission, error hints, and local UI loading;
- Stay in sync with runtime status.

## 12.3 Event Stream Display

Do not build a separate roleplay event backend.

Reuse the existing event interface, filtering by `avatar_id` to load the avatar's event stream.

Implementation recommendations:

- Keep the right-side global event panel;
- Reuse the same event rendering logic inside RoleplayPanel;
- Ideally extract a shared `EventTimelineList` component to avoid maintaining two sets of event item UI.

## 12.4 Prominent Prompt

When the world is paused because of a roleplay request, a clear prompt is needed.

It is recommended to include at least:

- Which avatar is currently waiting on the player;
- The current wait type: text decision / option choice / conversation input;
- "The world is paused, waiting for your action";
- A clear submission entry point.

Phases 1 and 2 can use the dock's top status bar for the prominent prompt; during Phase 3 conversations the chat header takes on this role.

### 12.5 Phase 3 Conversation UI

For Phase 3, opening a new modal or standalone page is not recommended; keep reusing the current bottom `RoleplayDock`.

It is recommended to add a third mode to the dock:

- `decision`
- `choice`
- `conversation`

The `conversation` mode is recommended to use a chat layout:

1. Top row
   - Current avatar
   - Conversation partner
   - Current status
   - "End Conversation" button
2. Middle main area
   - Message stream
   - Left/right distinction between the two speakers
3. Bottom input area
   - Input box
   - Send button

Interface constraints:

- Information density first, no large blank areas;
- Keep the top toolbar compact;
- While a conversation is in progress, the chat and an event summary area can be shown at the same time, but the chat is the main content area;
- After the session ends, the dock returns to the normal event stream view.

## 13. Loading, Saving, and Lifecycle

## 13.1 Saving

The roleplay state is not written into the save.

Reasons:

- It is not long-term world state;
- Restoring it is costly;
- It easily introduces consistency problems like "the request context is invalid after loading".

## 13.2 Loading

After every load game:

1. Clear the roleplay session;
2. Clear all roleplay pause reasons;
3. Clear the pending request;
4. The frontend resets the roleplay store after receiving the new runtime state.

## 13.3 Other Lifecycle Points

The same cleanup should also be performed after the following operations:

- start game
- reinit game
- reset game

## 14. Edge Cases and Fallbacks

At least the following edge cases need to be covered:

### 14.1 The Roleplayed Avatar Dies

If the roleplayed avatar dies:

- Automatically exit roleplay;
- Clear the pending request;
- Broadcast a toast or hint.

### 14.2 The Roleplayed Avatar Is Deleted or Does Not Exist

If the avatar becomes invalid:

- The roleplay session automatically becomes invalid;
- Old requests may no longer be submitted.

### 14.3 The Player Submits Too Slowly

This design allows waiting indefinitely, with no timeout-based automatic AI takeover.

But the request object should still carry a version or request_id, to guard against:

- The player's page lagging behind;
- Repeated submission of old requests;
- An old frontend still submitting after a load.

### 14.4 Exiting While Waiting for Input

Recommended behavior:

- Show a confirmation;
- After confirmation, end roleplay and hand control back to the AI;
- Do not keep the old request.

### 14.5 Switching to View Other Avatars During Roleplay

Allowed.

This is a core design requirement of "local takeover under the god's-eye view"; the player should not be restricted to viewing only the current avatar.

### 14.6 Suspended Choices Become Invalid After Save/Reset/Load

Since neither the roleplay state nor continuations go into the save:

- All suspended `choice` continuations must become invalid after load/reinit/reset;
- The frontend should receive a stable error when submitting an old `request_id`;
- Attempting to restore an old continuation after loading is not allowed.

### 14.7 Only One Suspended Roleplay Continuation Is Allowed at a Time

Phase 2 still maintains the constraint of "roleplaying at most one avatar", therefore:

- Only one active roleplay continuation is allowed at any moment;
- Multiple choices waiting at the same time is not supported;
- If a flow is already waiting on a choice, a new roleplay request is not allowed to overwrite the old request.

## 15. Impact on Existing Systems

## 15.1 Action System

Small impact.

Reasons:

- The existing action chain already supports "fill in a new decision after the chain finishes executing";
- Roleplay mode only replaces the decision source at the entry point for filling in decisions.

## 15.2 single_choice

Phase 2 requires a structural refactor, but not a tear-down rewrite.

Proposed refactor goals:

1. Keep the existing `request / decision / scenario` approach;
2. Add a unified resolver;
3. Add continuation;
4. Make the business layer stop caring directly about "whether the decision comes from the LLM or the player".

This is the most critical infrastructure change in Phase 2.

## 15.3 mutual action

Phase 2 needs to expose some `RESPONSE_ACTIONS` as player options, but the underlying response application logic should still reuse the original implementation.

## 15.4 Event System

Phases 1 and 2 have a small impact, only adding local display.

Phase 3 will introduce:

- Conversation summary generation;
- Writing the summary into the event system;
- Raw dialogue not going onto the formal event stream.

## 16. Testing Recommendations

## 16.1 Backend

The following test directions are recommended:

1. After entering roleplay, a second avatar cannot be roleplayed at the same time.
2. The roleplayed avatar does not pause immediately while it has an action chain.
3. A pending request is created when the roleplayed avatar's action chain ends.
4. While a pending request exists, the world is paused and does not continue advancing.
5. Submitting valid text loads the plan and resumes running.
6. Submitting an invalid request_id returns a stable error.
7. The roleplay session is cleared after load/reinit/reset.
8. Roleplay is exited automatically after the avatar dies.
9. Phase 2 choice submission reuses the original choice application logic.
10. After a Phase 3 conversation ends, only the summary event is written.

Phase 2 should also add the following dedicated tests:

11. `single_choice` still keeps the original LLM/fallback behavior in non-roleplay mode.
12. In roleplay mode, `single_choice` creates a unified `choice` request instead of immediately returning an LLM decision.
13. After the player submits `selected_key`, the continuation is resumed and the corresponding scenario's `apply_decision(...)` is called.
14. Continuations automatically become invalid after load/reset/reinit.

## 16.2 Frontend

The following test directions are recommended:

1. AvatarDetail correctly shows the enter/exit roleplay buttons.
2. While another avatar is being roleplayed, the current panel shows a cannot-take-over state.
3. A prominent prompt is shown when the roleplay session is in a waiting state.
4. After a successful text submission, the input box is cleared and the waiting state is collapsed.
5. The roleplay local event stream is loaded correctly by avatar_id.
6. The roleplay store resets automatically after load game.
7. A Phase 3 conversation request correctly renders the chat UI.
8. An LLM reply appears after the player sends one round of messages.
9. Clicking End Conversation closes the conversation state and restores the normal event stream.

## 17. Phased Delivery Recommendations

The following implementation order is recommended:

### Step 1

First do the runtime extensions:

- roleplay session
- pause reasons
- runtime status/query extensions

### Step 2

Do the Phase 1 minimal closed loop:

- start/stop/submit-decision API
- Decision injection point
- Frontend RoleplayPanel
- Prominent prompt

### Step 3

Do the first stage of Phase 2:

- Refactor the unified `single_choice` entry point
- Introduce `ChoiceResolver`
- Introduce continuation / resume token
- Unified frontend `choice` request UI

### Step 4

Do the second stage of Phase 2:

- Migrate `item_exchange` first
- Then migrate `sect_recruitment`
- Finally migrate mutual action responses

### Step 5

Do Phase 3:

- Hook up player dialogue with the `Conversation` action as the only trigger entry point
- conversation session
- conversation prompt
- conversation summary service
- Conversation UI
- Relationship / story hint settlement

## 18. Conclusion

The most reasonable way to deliver "personal mode" is not to build a new global mode parallel to god mode, but to:

- Always default to the god's-eye view;
- Allow the player to take over one avatar under the god's-eye view;
- Pause the world to wait for the player only at decision boundaries;
- Do text decisions in Phase 1;
- In Phase 2, first build the general finite decision framework, then carry options and invitation responses on top of it;
- In Phase 3, continue attaching to the `Conversation` action to implement player free-form dialogue, with the summary entering the events.

This route is the friendliest to the existing architecture and best fits the runtime / public v1 API / event system / action chain system already established in the current repository.

## 19. Final Phase 3 Decisions

After requirements confirmation in this round, Phase 3 is executed according to the following decisions:

1. Dialogue must be triggered by attaching to the existing `Conversation` action; no standalone free chat entry point is added.
2. Dialogue uses the one-sided takeover mode of "the player says one line, the target avatar replies with one line via the LLM".
3. The player has the final say on ending; the LLM cannot end the conversation on its own.
4. Raw chat logs do not go into the save; the conversation session state belongs entirely to the runtime.
5. The summary can output a three-layer result of "summary event + relationship hint + optional story extension".
6. While a conversation is in progress, the bottom dock may show the chat and event area at the same time, but the chat should be primary.

## 20. Phase 3 Implementation Plan

The following delivery order is recommended:

### 20.1 Backend Runtime and Protocol Layer

- Extend `RoleplaySession` to support `conversation_session`
- Extend `RoleplayPromptRequest(type=conversation)`
- Extend runtime status / query DTOs
- Add conversation send / end commands

### 20.2 Action Layer Integration

- Use the `Conversation` action as the only entry point
- Non-roleplayed avatars continue using the existing automatic dialogue logic
- The roleplayed avatar enters the `conversation_session`

### 20.3 LLM Layer

- Add a conversation prompt
- Add a conversation summary prompt
- First implement a stable "player line -> LLM line -> player decides whether to continue"

### 20.4 Frontend Layer

- Add a `conversation` mode to `RoleplayDock`
- Implement the message stream, sending, and ending the conversation
- Switch back to the normal event stream after the conversation ends

### 20.5 Testing Layer

- Backend session creation, advancement, ending, and invalidation
- Summary entering events
- Session cleared after reset/load/stop
- Frontend dock chat mode rendering and interaction
