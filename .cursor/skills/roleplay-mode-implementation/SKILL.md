---
name: roleplay-mode-implementation
description: Use when planning, implementing, or refactoring the avatar roleplay mode (single-avatar takeover under the default god view). Covers Phase 1 text decisions, the Phase 2 unified finite-choice framework, Phase 3 free conversation attached to the Conversation action, and the corresponding runtime/API/frontend/test consolidation.
---

## When to Use

Use this skill when a task involves any of the following:

- Implementing or refactoring the roleplay mode
- Adjusting `RoleplaySession`, `pending_request`, `conversation_session`
- Adding capabilities to or fixing regressions in Phase 1 text decisions
- Wiring player takeover into Phase 2 `single_choice` / mutual action choice
- Changing the Phase 3 `Conversation` dialogue chain, summary, or dock chat UI

## Confirm First

1. Does this change belong to Phase 1, Phase 2, or Phase 3?
2. Is this change filling in the main path, or doing wrap-up / UI / tests?
3. Will it affect runtime pause semantics, save semantics, or continuation semantics?
4. Are you unintentionally turning "single-avatar takeover under the god view" back into a standalone personal mode?

## Required Mental Model

### 1. The default is always the god view

- Do not make personal roleplay a global mode parallel to god mode.
- While roleplaying, the player can still observe the whole world; do not narrow information.

### 2. Pause only at decision boundaries

- Never interrupt an action chain that is midway through execution.
- Only wait for the player when "the current action is empty + planned actions are empty, and a new decision is needed".

### 3. Roleplay state is not saved

- `RoleplaySession`
- `pending_request`
- `conversation_session`
- choice continuation

All of the above belong to the runtime and must be cleared after `load / reinit / reset / start`.

### 4. Phase 2 goes through the unified finite-decision framework first

- Do not scatter `if roleplay ... else ...` across business code
- Prefer business layers that only keep:
  - `build_request()`
  - `apply_decision(...)`
- Leave the decision source to the unified resolver / continuation

### 5. Phase 3 conversations must hang off `Conversation`

- Do not add free-chat entry points detached from action semantics
- The player controls only one side of the dialogue; the other side is still answered by the LLM
- Raw chat logs do not enter the long-term event stream; only the summary is persisted

## Recommended Workflow

### 1. Read the anchor docs first

Look at these first:

- `docs/specs/avatar-roleplay-mode.md`
- `docs/specs/single-choice-unified-framework.md`
- `.cursor/rules/roleplay-mode.mdc`

If the change involves the external API, also read:

- `docs/specs/external-control-api.md`
- `.cursor/rules/external-control-api.mdc`

### 2. Then look at the current touchpoints

Common backend entry points:

- `src/server/runtime/session.py`
- `src/server/services/roleplay_service.py`
- `src/server/api/public_v1/command.py`
- `src/server/api/public_v1/query.py`
- `src/systems/single_choice/**/*.py`
- `src/classes/mutual_action/conversation.py`

Common frontend entry points:

- `web/src/stores/roleplay.ts`
- `web/src/components/game/RoleplayDock.vue`
- `web/src/components/game/roleplay/*.vue`
- `web/src/api/modules/avatar.ts`
- `web/src/types/api.ts`

### 3. Determine the layer of the change

- Changing runtime semantics: change runtime/service first, not the UI
- Changing the API: settle query/command boundaries and DTOs first
- Changing Phase 2 choices: first check whether it can plug into the unified choice resolver
- Changing Phase 3 conversations: first check that it still hangs off `Conversation`

## Implementation Checklist

### Phase 1

1. Is it still a `decision`-type request?
2. Does it keep "invalid input does not resume the world"?
3. Is the pending request only created after the action chain ends?

### Phase 2

1. Does it reuse the unified `choice` request?
2. Does it resume the flow through the unified continuation?
3. Does it avoid hardcoding roleplay branches in business scenarios?

### Phase 3

1. Is it triggered by the `Conversation` action?
2. Does it keep "one line from the player, one line from the LLM"?
3. Can only the player end it?
4. Is only the summary persisted to the long-term event stream?

## Frontend Constraints

- `RoleplayDock` should keep a unified skeleton:
  - Header
  - Active Request
  - Activity Stream
- `decision / choice / conversation` only switch the request body; do not reinvent the whole-page layout
- The event stream should reuse the unified high-density event list component

## Docs and Tests

When changing the roleplay main path, sync these first:

- `docs/specs/avatar-roleplay-mode.md`
- `docs/specs/single-choice-unified-framework.md`
- `.cursor/rules/roleplay-mode.mdc`
- `AGENTS.md`

Recommended minimum to run:

```bash
pytest tests/test_public_api_v1.py tests/test_single_choice.py tests/test_action_social.py tests/test_mutual_actions.py -q
cd web && npm run type-check
cd web && npm run test
```
