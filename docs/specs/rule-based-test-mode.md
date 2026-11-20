# Rule-Based Simulation Test Mode Design

## 1. Background

Much of the game's initialization and simulation behavior uses the LLM to produce decisions, text, or structured results. Normal runs should keep using the configured LLM; however, feature development, integration verification, demos, and regression testing need a mode that can fully start a world and keep it running, yet never access the LLM service.

This design defines the "rule-based simulation test mode" (hereafter "test mode"). It is not a mock from a unit-test framework, nor an error fallback after the LLM configuration fails. It is a **single-run semantic** that the player chooses when starting a game: every LLM dependency point in the current run must be replaced by deterministic built-in rules, or end with an explicit "unsupported" result, and must never access a real LLM network endpoint.

## 2. Goals

1. Allow the user to enable test mode in the "Start Game" panel; it is off by default.
2. In test mode, do not read the API Key to issue requests, do not run provider connectivity checks, and do not call any real LLM HTTP endpoint.
3. World initialization and the regular simulation loop can complete, so the overall paths for avatars, actions, events, sects, saves, and WebSocket can be used for integration verification.
4. For every LLM task, provide a structurally valid, deterministic, business-consumable rule result, or explicitly declare the capability unavailable in test mode.
5. Test mode is part of `RunConfig`; it must be saved with the world snapshot and the save file, and restored after loading.
6. The call chain, LLM configuration, and error behavior of normal mode must not change semantically because of this feature.
7. When a new LLM task is added, test mode must not silently let it slip through and access the real service.

## 3. Non-Goals

1. Do not attempt to reproduce the LLM's creative quality, narrative diversity, or strategic ability with a rule system.
2. Do not make test mode a global, cross-run switch; the semantics of different worlds in the same process must not contaminate each other.
3. Do not automatically treat an LLM request failure as test mode, and do not change the existing exception and fallback logic in formal mode.
4. Do not fabricate custom content or free-form dialogue text that "looks like real generated content" for test mode.
5. Do not require every optional gameplay capability to be available in test mode; proactive generation features may explicitly refuse.
6. Do not introduce a second simulator, a second save format, or a second avatar decision system.

## 4. Terms and Invariants

### 4.1 `test_mode`

`test_mode: bool` is a single-run field in `RunConfig`. `false` means normal mode, `true` means rule-based simulation test mode. The default value must be `false`.

### 4.2 LLM task

An LLM task is the stable task name used when calling `call_llm_with_task_name(task_name, ...)`, for example `action_decision`, `relation_delta`, `story_teller`.

### 4.3 Rule fallback

A rule fallback is the deterministic result returned in test mode for a specific task, conforming to that task's business parsing contract. It is not a temporary empty object produced by exception catching.

### 4.4 Invariants

Test mode must satisfy:

1. No network function that reaches the provider may be called.
2. No unknown or unregistered LLM task may automatically be routed to the normal call path.
3. The return shape of a fallback must be parseable by its caller; a global `{}` must not be used as a generic result.
4. The test mode state must come from the current world's `run_config_snapshot` or the `RunConfig` of the game being started; a module-level mutable global switch must not be used.
5. After loading a test mode save, the game is still in test mode; after loading a normal save, it is still in normal mode.
6. Normal mode keeps the existing API Key, retry, parsing, error notification, and call logging paths.

## 5. User Experience

### 5.1 Game Start Panel

File: `web/src/components/game/panels/system/GameStartPanel.vue`

Add a checkbox near the end of the regular game start parameters, before the start button. Use Naive UI's `n-checkbox`, bound to `settingStore.newGameDraft.test_mode`.

English copy:

- Label: `Test Mode`
- Note: `For testing features and the overall game flow only. No real LLM is called; AI results use built-in rules.`

Requirements:

1. Unchecked by default.
2. Disabled together with the other game start parameters when the form is `readonly`.
3. The note must be visible; it must not be placed only in a tooltip.
4. Do not hide this switch in the start button, map cards, or global system settings.
5. `en-US` is the sole and source locale; maintain the copy only in the `en-US` split source files, and do not directly edit the merged `LC_MESSAGES` artifacts.

### 5.2 Game Start and Load Hints

The first iteration does not require a persistent, prominent indicator in the main game UI, to avoid misleading users into thinking the test feature is a formal gameplay mode. However, the query API must expose the current `test_mode`, so that the frontend, external agents, and test tools can diagnose the current run.

It is recommended to later show a non-error status in the runtime status or debug info: `LLM mode: rule-based simulation test`. This hint should not reuse the "LLM connection failed" error UI.

### 5.3 Proactive Generation Capabilities

The following features that proactively ask the LLM to generate content must return an explicit, localizable controlled error in test mode, instead of pretending generation succeeded:

1. Custom content generation.
2. Custom goldfinger draft generation.
3. Free-form dialogue and dialogue summaries in roleplay.
4. Any future generation command that is explicitly initiated by the user and has no defined rule output.

Suggested error code: `TEST_MODE_LLM_UNAVAILABLE`.

## 6. Data Model, API, and Saves

### 6.1 Configuration Model

File: `src/config/settings_schema.py`

Add the field to the following models:

```python
test_mode: bool = False
```

- `NewGameDefaults`
- `NewGameDefaultsPatch`, with type `Optional[bool]`
- `RunConfig`, which gets the field by inheriting `NewGameDefaults`

Ownership of `test_mode`:

1. It is a current-run runtime semantic, so `RunConfig` is the single runtime source of truth.
2. It can serve as the default for the next game, so it also belongs to `new_game_defaults`.
3. It is not `LLMSettings`, `LLMProfile`, static `CONFIG`, or a deployment environment variable.
4. After the game starts, the current run must not be modified through the settings page; it can only change by starting a new game or loading a save.

### 6.2 Frontend DTO and Store

Files:

- `web/src/types/api.ts`
- `web/src/stores/setting.ts`

Add `test_mode: boolean` to `RunConfigDTO`. The initial value of `newGameDraft` must explicitly include `test_mode: false`, and `applySettings()` restores the field from `settings.new_game_defaults`.

`updateNewGameDraft()` and `startGameWithDraft()` already use `RunConfigDTO` as their carrier; once the field is added to the DTO it should naturally flow through:

```text
GET /api/settings
  -> settingStore.newGameDraft
  -> POST /api/settings (new_game_defaults)
  -> POST /api/v1/command/game/start
```

### 6.3 Stable API Contract

The `RunConfig` structure of the following existing endpoints must include `test_mode`:

| Endpoint | Semantics |
|---|---|
| `GET /api/settings` | Returns the new game defaults |
| `PATCH /api/settings` | Saves the defaults for the next game |
| `POST /api/v1/command/game/start` | Specifies test mode for the current run |
| `GET /api/v1/query/system/current-run` | Queries test mode of the current run |

The API should not add a separate "toggle test mode" command. Toggling during a run would break save semantics, async task boundaries, and reproducibility.

### 6.4 Save and Load

The current `world.run_config_snapshot` is already produced by the initialization flow and saved through the `run_config` section. The implementation does not add a parallel save section:

```text
RunConfig(test_mode=True)
  -> runtime run_config
  -> world.run_config_snapshot
  -> save_data["run_config"]
  -> load context.run_config_snapshot
  -> loaded world.run_config_snapshot
```

Loading must not write back to the user's `settings.json`. The user's defaults for the next new game may differ from the `test_mode` of the loaded save.

## 7. Runtime Test Mode Propagation

### 7.1 Design Choice

The LLM client must not depend directly on some global `game_instance`, nor use a module-level mutable `TEST_MODE` variable. The reasons are:

1. LLM call sites are spread across initialization, the simulation loop, service commands, and roleplay.
2. Both the simulator and API mutations are asynchronous flows.
3. A module-level boolean would leak state across restarts, loads, concurrent tests, or future multi-session support.

Use `contextvars.ContextVar` to carry the test mode of the current execution chain.

Suggested new file: `src/utils/llm/runtime_mode.py`.

```python
def is_test_mode_enabled() -> bool: ...

@contextmanager
def llm_test_mode_scope(enabled: bool): ...
```

The internal `ContextVar` defaults to `False`. The scope must reset its token on exit, ensuring that exceptions, cancellations, and nested calls do not contaminate subsequent requests.

### 7.2 Where to Establish the Scope

Every world entry point that executes LLM-dependent logic must establish a scope from the current run's snapshot:

1. `perform_game_initialization()`: establishes the scope for the entire initialization from the `RunConfig.test_mode` about to be created.
2. `GameLoopRunner.run_once()`: inside the mutation that calls `sim.step()`, establishes the scope using `world.run_config_snapshot["test_mode"]`.
3. Mutation commands related to the loaded world: establish the scope at the service/runtime mutation entry or at each explicit entry point.
4. Roleplay, world lore, and other async tasks that read the world: establish the scope from the target world snapshot.

`asyncio.create_task()` copies the context at creation time; therefore background tasks created during initialization should also be created inside the correct scope. Do not assume context propagates automatically across threads; if some LLM-related logic indirectly enters the call chain via `asyncio.to_thread()`, its mode propagation must be explicitly verified.

### 7.3 World Helper

A read-only helper can be provided to avoid scattered dict reads:

```python
def is_world_test_mode(world: Any) -> bool:
    return bool((getattr(world, "run_config_snapshot", None) or {}).get("test_mode", False))
```

This helper only reads the value from the world snapshot; it owns no state and does not modify configuration.

## 8. LLM Gateway and Fallback Registry

### 8.1 Single Interception Point

File: `src/utils/llm/client.py`

`call_llm_with_task_name()` is the single entry point for structured tasks. In test mode it must short-circuit before the following operations:

1. Reading the template.
2. Building the prompt.
3. Reading the LLM profile/API Key.
4. Acquiring the semaphore.
5. Calling the provider.
6. Writing the real LLM call log.

Logic:

```text
call_llm_with_task_name(task_name, template_path, infos)
  -> is_test_mode_enabled()?
       yes -> RuleLLMFallbackRegistry.resolve(task_name, infos)
       no  -> existing get_task_mode -> template -> call_llm_with_template chain
```

Do not intercept only before the low-level `_call_with_requests()`, because then test mode would still load prompts, trigger parse retries, and be unable to produce a valid structure based on `task_name`.

The raw `call_llm()` and `call_llm_json()` interfaces raise `TestModeUnsupportedLLMTask` by default in test mode; only calls with an explicit task name may go through the rule registry. If business code is found bypassing the task-name entry, it should be changed to use the task-name entry as part of this implementation, or be given an explicit controlled rule interface.

### 8.2 Module Structure

Suggested new file: `src/utils/llm/test_mode_fallbacks.py`.

```python
class TestModeLLMError(Exception): ...
class TestModeUnsupportedLLMTask(TestModeLLMError): ...

def resolve_test_mode_task(task_name: str, infos: Mapping[str, Any]) -> dict[str, Any]: ...
def registered_test_mode_tasks() -> frozenset[str]: ...
```

Requirements:

1. The registry is keyed by the stable `task_name`.
2. Fallback functions must be pure: no network requests, no reading user secrets, no modifying the world.
3. Return values contain only the fields the caller's contract needs.
4. Results must be deterministic. Unless a task's business contract requires seeded randomness, uncontrolled random numbers are forbidden.
5. An unregistered task directly raises `TestModeUnsupportedLLMTask(task_name)` and must never call the real LLM.
6. Implementing a catch-all where "every unknown task returns `{}`" is forbidden.

### 8.3 Registered Task List and Rules

This implementation must cover every `call_llm_with_task_name` task currently in the repository. Each fallback must be written against the fields actually consumed and have a corresponding unit test.

| Task | Typical callers | Test mode rule result |
|---|---|---|
| `action_decision` | `classes/ai.py`, roleplay text decisions | Returns a parseable empty action plan, or a plan generated by an existing valid fallback; must not return nonexistent action IDs |
| `backstory` | Avatar initial backstory | `{"backstory": ""}`; the caller skips writing the backstory |
| `long_term_objective` | Initial avatar objective | `{"long_term_objective": ""}`; the caller skips writing the objective |
| `nickname` | Nickname | `{"nickname": "", "thinking": "", "reason": ""}`; no nickname is granted |
| `story_teller` | Story events / gathering stories | `{"story": ""}`; the factual event is kept and story expansion is skipped |
| `relation_resolver` | Relationship change judgment | `{"changed": false}` |
| `relation_delta` | Bidirectional relationship values | `{"delta_a_to_b": 0, "delta_b_to_a": 0}` |
| `interaction_feedback` | Two-avatar interaction feedback | Returns the valid "no extra effect" structure the caller requires; fields must be pinned to the actual parser before implementation |
| `single_choice` | Sect recruitment, item exchange, world secrets, etc. | Do not guess the option directly; the existing `single_choice` fallback policy should resolve a valid key. If needed, the registry returns an explicit fallback marker and the resolver picks a valid option |
| `sect_decider` | Annual sect planning | Returns a caller-parseable status-quo plan: no recruiting, no expansion, no resource transfers |
| `sect_thinker` | Sect annual thinking | Returns an empty or fixed short description, and does not change the decision result |
| `fate_revelation` | Fate revelation | Returns a caller-parseable "not triggered / no effect" structure |
| `random_minor_event` | Random minor events | Returns a caller-parseable "not triggered" structure |
| `world_lore_style_guide` | World lore rewrite | The upper layer skips the entire world lore rewrite pipeline directly; must not fabricate a style guide |
| `world_lore_region_rewrite` | World lore region rewrite | Same as above, skipped |
| `world_lore_sect_group_rewrite` | World lore sect rewrite | Same as above, skipped |
| `world_lore_technique_rewrite` | World lore technique rewrite | Same as above, skipped |
| `world_lore_weapon_rewrite` | World lore weapon rewrite | Same as above, skipped |
| `world_lore_auxiliary_rewrite` | World lore auxiliary rewrite | Same as above, skipped |
| Other dynamic `world_lore_*` jobs | World lore rewrite planner | The upper layer skips entirely in test mode; if one still reaches the registry, raise a controlled error to expose the omission |
| `custom_content_generation` | Custom content, goldfinger drafts | Raise / convert to `TEST_MODE_LLM_UNAVAILABLE`; do not fabricate drafts |
| Conversation reply/summary tasks | roleplay conversation service | Raise / convert to `TEST_MODE_LLM_UNAVAILABLE`; do not fabricate avatar dialogue or summaries |

"The valid structure the caller requires" in the table is not a vague item at implementation time: before coding, read each task's parser and consumers, fill in the exact fields, and lock them in tests. If the current caller already has a high-quality fallback, reuse it first instead of duplicating the domain fallback into the registry.

### 8.4 Layering of action and single-choice

The valid candidates for `action_decision` and `single_choice` depend on the current world state. A pure registry should not reverse-engineer actions/options from prompt text.

Therefore:

1. `single_choice` short-circuits preferably inside the domain resolver in `systems/single_choice` to the existing `FallbackPolicy`, guaranteeing the choice always comes from the current request.options.
2. `action_decision` preferably reuses the existing "no valid plan / conservative plan" rules in the avatar AI decision chain, or adds a domain fallback builder that takes avatar/world.
3. The LLM registry only takes responsibility for "forbidding the LLM, reporting the mode, and returning fixed output for pure-structure tasks"; it should not absorb all decision logic that requires world domain knowledge.

This avoids encoding business choice logic as fragile parsing of prompt strings.

## 9. Initialization, Simulation, and Special Capabilities

### 9.1 Initialization

File: `src/server/init_flow.py`

In test mode, initialization still proceeds through the existing phases: loading the map, creating the world, generating avatars, initializing sects, generating first-step events, etc. LLM dependency points are completed or skipped via the rule path.

Additional rules:

1. `_run_llm_check_background()` must not be started.
2. `llm_check_failed=True` must not be set when initialization completes.
3. The runtime may set `llm_check_pending=False`, and may add a non-error `llm_mode="test"` for the query layer to display.
4. The user's `world_lore` input is still saved as world text/snapshot; but in test mode no LLM-driven world lore rewrite job is executed.
5. If skipping the world lore rewrite means some UI copy needs explanation, the UI should use the test mode note, rather than misreporting it as an initialization failure.

### 9.2 Simulation Loop

File: `src/server/loop/runner.py`

When `GameLoopRunner.run_once()` executes inside `runtime.run_mutation(sim.step)`, it must establish the LLM mode scope corresponding to the world. This way, all calls triggered within a tick by async phases such as actions, relationships, stories, and sects are protected by test mode.

Do not cache `test_mode` when the loop runner module is constructed; after a restart or load, every tick reads from the current world snapshot.

### 9.3 World Lore Rewrite

Files: `src/systems/world_lore_rewrite/**`

In test mode, the public entry of the world-lore pipeline immediately returns a structured "skipped" result. The reason is that this pipeline is not an isolated text field; it batch-rewrites data such as regions, sects, and items. Letting each subtask continue with empty JSON would leave an incomplete, half-rewritten state.

When skipping, it should:

1. Keep the original `world_lore` input.
2. Keep the static/default world data.
3. Not write partial rewrite artifacts.
4. Not raise an initialization failure.

### 9.4 Custom Content

Files:

- `src/server/services/custom_content_service.py`
- `src/server/services/custom_goldfinger_service.py`

The call entry first checks whether the target world/current run is in test mode and directly returns a stable error code. This check should happen before prompt generation and the LLM client call.

The user can still use the non-LLM capability of "submit an already-written draft and create it", provided the command itself does not generate LLM content and existing domain validation passes.

### 9.5 Roleplay

Regular finite choices can still go through the deterministic `single_choice` fallback. Free-form dialogue and paths that turn natural-language intent into complex action chains must refuse and keep the current runtime state consistent if they cannot provide a strictly valid domain fallback.

When refusing free-form dialogue in test mode:

1. Do not create a half-finished conversation session.
2. Do not write to the long-term event stream.
3. Do not clear the pause reason related to the session, unless the user explicitly ends the session.
4. Return `TEST_MODE_LLM_UNAVAILABLE`, which the frontend shows with a localizable message.

## 10. Error Model and Observability

### 10.1 Error Classification

New internal exception categories:

```text
TestModeLLMError
├─ TestModeUnsupportedLLMTask(task_name)
└─ TestModeLLMUnavailable(feature)
```

The service layer should map an unavailable proactive feature to a stable API error code:

```json
{
  "status": "error",
  "error": {
    "code": "TEST_MODE_LLM_UNAVAILABLE",
    "message": "LLM content generation is not available in test mode."
  }
}
```

If the project's current unified response wrapper has an established field shape, follow the existing `ok_response/error_response` contract; the example above only expresses the semantics.

An unregistered task is a development completeness issue and should not be swallowed as an ordinary user error. Its log must include the task name, the current run identifier, and the call site; tests should fail on it.

### 10.2 Logging

Test mode does not write real `log_llm_call()` records, to avoid test results being miscounted as model usage. Optionally write low-frequency structured debug logs, for example:

```text
[test-mode] resolved LLM task with rule fallback: relation_delta
```

Logs must not contain the API Key, the full prompt, or sensitive user configuration.

### 10.3 Connectivity

In test mode, `test_connectivity()` is not called, and the provider endpoint is not read. The status is not "LLM check failed" but "LLM check not applicable".

## 11. Test Strategy

### 11.1 Configuration and API

1. `NewGameDefaults` and `RunConfig` default to `test_mode is False`.
2. `NewGameDefaultsPatch(test_mode=True)` can be saved, and `GET /api/settings` echoes it back.
3. After passing `test_mode=True` to `POST /api/v1/command/game/start`, `current-run` returns the field.
4. A normal game start without the field yields `false`.
5. No command exists to toggle the field during a run.

### 11.2 Frontend

1. `newGameDraft` defaults to `test_mode: false`.
2. The value is restored correctly after hydrating from `AppSettingsDTO.new_game_defaults`.
3. `GameStartPanel` shows the checkbox and the visible description text.
4. After toggling the checkbox, the payload sent by `startGameWithDraft()` contains the correct boolean.
5. The readonly state disables the control.

### 11.3 Saves

1. The save data of a test mode world has `run_config.test_mode` as `true`.
2. After loading that save, `world.run_config_snapshot.test_mode` is `true`.
3. A normal mode save is `false` after loading.
4. Loading does not rewrite the next-game defaults in `settings.json`.

### 11.4 No-Network Guarantee

In tests, monkeypatch the lowest-level network function of the LLM provider (e.g. `_call_with_requests`) to raise AssertionError when called. Then:

1. Enable test mode and run full initialization.
2. Run several consecutive `Simulator.step()`/`GameLoopRunner.run_once()` calls.
3. Cover paths that trigger tasks, such as world lore input, avatar generation, relationships/events.
4. Assert the network stub was not triggered.
5. Assert `test_connectivity()` was not executed.

Correspondingly, normal mode client unit tests must verify that the existing provider call path is still used when test mode is not enabled.

### 11.5 Fallback Validity

Each registered task must have at least:

1. A return-shape test calling the registry directly.
2. A business test where the real consumer parses the result, or coverage of its existing fallback branch.
3. For action/single-choice that need world context, verification that results are valid using real `request.options` or an avatar fixture.
4. No nonexistent action IDs, avatar IDs, item IDs, region IDs, or enum values are produced.

### 11.6 Fail-Closed

1. Calling an unknown task in test mode must raise `TestModeUnsupportedLLMTask`.
2. When this exception occurs, the provider must not be called.
3. Proactive generation features return `TEST_MODE_LLM_UNAVAILABLE`.
4. Initialization/simulation should not produce an error state due to an expected "skip generation".
5. The test mode scope is restored after exceptions and cancellation; the next normal mode call must not be wrongly intercepted.

### 11.7 Suggested Test Files

Place tests near the existing test organization, preferring to add:

- `tests/test_llm_test_mode.py`
- run config/API cases in `tests/test_settings_service.py`
- test mode initialization cases in `tests/test_game_init_integration.py`
- run_config save/restore cases in `tests/test_save_load_*.py`
- `web/src/__tests__/stores/setting.test.ts`
- `web/src/__tests__/components/game/GameStartPanel.test.ts`

## 12. Implementation Phases

### Phase 1: Configuration, UI, and Data Loop

1. Add schema, DTO, settings persistence, and defaults.
2. Add the Start Game checkbox and `en-US` copy.
3. Confirm the `RunConfig` loop across start/current-run/save/load.
4. Add backend and frontend field tests.

Completion criteria: the user can start a game with test mode enabled, and current-run and the save both accurately show the value.

### Phase 2: LLM Runtime Gateway

1. Add the ContextVar scope and world helper.
2. Establish the scope at initialization, the simulation loop, and related service entries.
3. Add the fail-closed test mode branch in `call_llm_with_task_name()`.
4. Add the registry, the unknown task exception, and no-network tests.

Completion criteria: in test mode, no covered call can reach the provider; normal mode is unchanged.

### Phase 3: Domain Fallbacks and Skip Strategy

1. Implement exact fallbacks for the current task list.
2. Keep candidate selection for `single_choice` and action in the domain layer, without parsing prompts.
3. Skip the entire world-lore pipeline.
4. Implement stable refusal for custom content / roleplay conversation.
5. Add business parsing and initialization integration tests item by item.

Completion criteria: test mode can complete initialization and run continuously; proactive generation capabilities fail predictably; no real LLM requests.

### Phase 4: Documentation and Regression

1. Write a summary of this document's stable constraints into the applicable `.cursor/rules` and `AGENTS.md`.
2. Update `docs/specs/external-control-api.md` depending on external API status field changes.
3. Run the targeted backend and frontend tests and type checks.

Completion criteria: when later developers add an LLM task, they can discover from rules and tests whether the test mode contract is missing.

## 13. Acceptance Criteria

An implementation is considered complete only when all of the following hold:

1. The Start Game panel leaves test mode unchecked by default and shows the visible note "for testing only, does not connect to a real LLM".
2. The test mode field stays consistent across the full chain of settings, game start, current run query, world snapshot, save, and load.
3. Test mode initialization succeeds, and at least several world ticks can run.
4. With the real network function replaced by an assertion failure in test mode, the full test suite still passes.
5. Any unknown task fails explicitly in test mode and never falls back to the real provider.
6. Every current LLM task has an explicit rule fallback, domain fallback, or controlled refusal strategy.
7. The LLM connectivity check does not run in test mode, and the UI/API does not report it as an LLM configuration error.
8. Existing regression tests for normal mode LLM calls, failure notifications, retries, and logging pass.
9. The related frontend unit tests and type-check, and the related backend pytest, all pass.

## 14. Ongoing Maintenance Checklist

When adding or modifying an LLM task later, check in order:

1. Does the task enter the unified gateway through `call_llm_with_task_name()`?
2. In test mode, is it a rule fallback, a domain fallback, a whole-pipeline skip, or explicitly unavailable?
3. Does the fallback produce only valid values the caller can parse?
4. Has a fail-closed coverage test for unknown tasks been added?
5. Does the call happen inside the world scope, so it can read the correct `RunConfig.test_mode`?
6. Could it wrongly run an LLM connectivity check, read the API Key, or write a real call log?
7. Do this spec, the related rules, and the `AGENTS.md` summary need updating?
