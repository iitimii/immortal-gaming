# High-Cohesion Modules and Boundary Consolidation Refactor Plan

This document defines the scope of the next refactor round, aimed at maintainability. It introduces no new player features and does not change world rules; the goal is to eliminate the mixed responsibilities, dependency buses and duplicated query implementations that have already appeared in the current code and will keep amplifying maintenance cost.

This document uses the current code as its baseline. The repository already has a server runtime, query/command services, and transitional re-exports for `avatar_init` and `opportunity`, but these apparent module boundaries do not mean the responsibilities have actually moved. This round uses the real implementation location and dependency direction as the completion criteria.

## 1. Goals

1. Shrink `src/server/main.py` into a process entry point and composition root, no longer serving as a global business dependency bus.
2. Keep `Sect` holding domain state and rules, no longer directly responsible for i18n text, frontend DTOs and static registry loading.
3. Give event queries a single testable set of filtering, sorting, hydration and error semantics, with SQLite and the in-memory fallback kept consistent.
4. Split avatar initialization and the opportunity system into real modules, rather than having `__init__.py` forward to implementations that still live in the same file.
5. Replace the string error protocol in the LLM transport with structured provider exceptions.
6. Critical read and write failures must not masquerade as empty business results.

## 2. Non-Goals

1. Do not change the business semantics of `/api/v1/*`, frontend DTOs or the save JSON shape, unless required to fix a clearly wrong error boundary.
2. Do not introduce a generic DI framework or service locator, or replace the existing dependency dicts with a new catch-all `dict[str, Any]`.
3. Do not maintain long-term dual tracks for historical `main.py` patch points, old module paths or old saves; zero-cost re-exports and `.get()` may be kept temporarily, but must have a removal phase.
4. Do not rewrite world rules, action settlement, sect diplomacy or the roleplay finite decision framework in this round.
5. Do not write the roleplay session, pending request, conversation session or continuation into saves.

## 3. Overall Principles

### 3.1 Dependency Direction

```text
API / Host -> application service -> runtime + domain service -> domain model
                                      -> assembler / serializer
```

- `src/classes/**` and `src/systems/**` do not depend on `src/server/**`.
- Domain models do not import FastAPI, frontend DTOs or concrete i18n presentation formats.
- `main.py` only creates and wires objects; it does not do business forwarding and is not a common entry point for test patches.

### 3.2 Dynamic vs. Stable Dependencies

- Content that changes due to settings reload, data root switching or config updates is read at call time through narrow getters.
- Stable domain services, serializers and assemblers are injected at construction time through named fields.
- Dataclass fields must be responsibility-level objects or explicit Protocols; do not flatten dozens of bare functions into a "typed giant dict".

### 3.3 Migration Principles

- First establish the new path and contract tests, then migrate one complete call surface, and finally delete the old implementation.
- Transitional modules may only re-export real implementations that have already been migrated; it is forbidden to have a "new module import the old giant `__init__`" and then declare the split complete.
- Each phase must reduce the real responsibilities of the old entry point by its end; migrations that only add wrapper layers are not accepted.

## 4. Target Design

### 4.1 Server Composition

The current `main.py` still centrally constructs large dependency sets for queries, commands and runtime hooks. Although `GameQueryDependencies` and `GameCommandDependencies` are already dataclasses, they still mainly carry a large number of bare functions, and the services themselves are mostly just forwarders.

Target structure:

```text
ServerComposition
  - runtime: GameSessionRuntime
  - connection_manager: ConnectionManager
  - settings: SettingsServicePort
  - static_data: StaticGameDataRegistry
  - queries: GameQueryService
  - commands: GameCommandService
  - lifecycle: GameLifecycleService
  - host: HostDependencies
```

Requirements:

1. `create_server_composition()` lives in `src/server/composition.py` or a package with the same responsibility, and is responsible for assembling the objects above.
2. `create_configured_app()` receives `ServerComposition` and a small `HostDependencies`, and no longer receives dozens of function parameters.
3. `GameQueryService` and `GameCommandService` depend only on collaborators with clear responsibilities, such as `WorldQueryFacade`, `AvatarCommandFacade`, `SaveLoadService`, `RoleplayService`; the flat function list must not keep growing.
4. `main.py` is ultimately only responsible for parsing the startup environment, creating the composition, creating the app and calling `start_server()`.
5. Collaborators affected by config reload must read the current config through getters inside their own methods, and must not treat `CONFIG` as a permanent snapshot.

### 4.2 Separating Sect Domain, Presentation and Registry

`Sect` currently stores state, computes member status, outputs localized descriptions, assembles frontend structured data, and shares a module with static registry loading.

Target modules:

```text
src/classes/core/sect.py              # Sect, SectHeadQuarter, pure domain rules
src/classes/sect_member_status.py     # member status, contribution and combat power normalization
src/classes/sect_registry.py          # static data loading, reload, lookup by id/name
src/server/assemblers/sect_detail.py  # API DTO and localized presentation
```

Requirements:

1. `Sect` may keep domain behavior such as adding/removing members, race acceptance, sect rule checks and resource state.
2. `Sect` must not directly import `src.i18n`, `techniques_by_name` or API assemblers; `get_structured_info()` and user-facing string descriptions move into an assembler/presenter.
3. Extract the member status algorithm into an independently testable service, so that `Sect` does not bloat from coupling presentation sort rules with the battle system.
4. Move `sects_by_id`, `sects_by_name` and `reload()` out of the core model file; callers obtain them through the registry or the existing static data registry.
5. New DTOs must keep the frontend contract of backend localization and strongly typed mappers, and must not add Chinese fallbacks on the frontend.

### 4.3 Event Query Spec

Define a storage-internal query object:

```python
class EventAudience(str, Enum):
    DIRECT = "direct"          # directly involved via related_avatars
    OBSERVED = "observed"      # visible via event_observations

class EventMemoryScope(str, Enum):
    ALL = "all"
    MAJOR = "major"            # is_major and not is_story
    MINOR = "minor"            # not is_major or is_story

@dataclass(frozen=True)
class EventQuery:
    avatar_ids: tuple[str, ...] = ()
    audience: EventAudience = EventAudience.DIRECT
    sect_id: int | None = None
    memory_scope: EventMemoryScope = EventMemoryScope.ALL
    cursor: EventCursor | None = None
    limit: int = 100
    chronological: bool = False
```

Semantic requirements:

1. A single avatar's long-term/short-term memory uses `OBSERVED`, and avatar-pair events use `DIRECT`; this is explicit business semantics and is no longer implied by different SQL fragments.
2. `EventStorage` has only one query compiler/executor, which uniformly handles filtering, sorting, pagination, batch association hydration, observation text rendering and database error translation.
3. The in-memory mode of `EventManager` must execute the same `EventQuery` semantics; it can no longer quietly define a different set of filter rules in a separate loop.
4. Semantic APIs such as `get_major_events_by_avatar()` and `get_events_between()` continue to be provided externally; they are only responsible for constructing an `EventQuery`.
5. Database errors must be raised or converted into an explicit domain read failure; an empty list only means there really are no matching events.

### 4.4 Real Split of Avatar Initialization

Target modules:

```text
src/sim/avatar_init/
  social_initialization.py  # initial relations, friendliness
  initial_attributes.py     # age, lifespan, equipment, sect position, contribution, golden finger
  population_planning.py    # MortalPlan, PopulationPlan, constraint graph, sect assignment
  avatar_factory.py         # AvatarFactory, single/batch construction
  manual_avatar.py          # external request parsing, validation, override, manual creation
  __init__.py               # stable exports, nothing more
```

Requirements:

1. Transitional modules such as `factory.py`, `planning.py` and `request_parser.py` must be changed to hold the real implementations, and can no longer import from the package `__init__`.
2. `__init__.py` only re-exports stable public entry points and declared public types, and contains no actual algorithms; target is under 100 lines.
3. `create_random_mortal()` and `make_avatars()` keep their existing call semantics; `create_avatar_from_request()` remains the sole entry point for manual creation.
4. The random population algorithm does not depend on HTTP/request types; input parsing and API validation are not mixed with the random algorithm in the same file.
5. After migration, add module-level tests covering at least constraint solving, relation materialization, manual creation parameters, age limits and race/sect compatibility.

### 4.5 Real Split of the Opportunity Package

Target modules:

```text
src/systems/opportunity/
  models.py       # OpportunityRecord, enums, OpportunityManager
  config.py       # dynamic reading of probabilities, durations, weights
  targeting.py    # target selection, direction and hints
  outcomes.py     # reward selection and outcome settlement
  phases.py       # monthly checks and state advancement
  persistence.py  # save/load
  __init__.py     # stable exports
```

Requirements:

1. The real definitions in the modules above must move out of `__init__.py`; the existing thin modules of the same name no longer import `__init__.py` in reverse.
2. `OpportunityManager` only manages runtime records and cooldown state, and does not directly take on target generation, event text or reward settlement.
3. Probabilities and config are read from the current config at call time, consistent with current-run / settings reload semantics.
4. Opportunity event generation still follows the rule "first the base factual event, then try to append a story via `StoryEventService`".
5. Save data only contains JSON primitive types and IDs; temporary object references are not persisted.

### 4.6 LLM Provider Exception Model

Goal: replace string protocols such as `Exception("HTTP_...::...")` and `Exception("NETWORK_ERROR::...")` with internal exceptions.

```python
@dataclass
class ProviderCallError(Exception):
    kind: ProviderFailureKind
    message: str
    status_code: int | None = None
    response_body: str = ""
    provider_message: str = ""
    cause: Exception | None = None
```

Requirements:

1. The OpenAI-compatible and Anthropic adapters each convert HTTP, network and invalid-response failures into `ProviderCallError`, preserving the original cause.
2. The error classification function consumes structured exceptions; string parsing is only a short-term compatibility adapter and must not become the main path.
3. `call_llm()` keeps the existing semantics of concurrency control, logging and global config failure notification.
4. `call_llm_json()` only retries parseable failures; provider/network errors propagate upward per the existing failure classification, and are not misreported as JSON parse problems.
5. `test_connectivity()` returns user-readable errors, but must not use `print` in place of structured logging.

## 5. Implementation Phases

### Phase A: Architecture Contracts and Composition

1. Add tests for composition, `main.py` slimming and dynamic getters.
2. Create `ServerComposition`, and migrate the app factory and service construction.
3. Delete `main.py` forwarding entry points that have no production callers; tests are changed to construct the composition or patch local dependencies.

Acceptance: `main.py` has no giant dependency dict, business helpers or new legacy exports; the app factory does not receive a list of function parameters.

### Phase B: Event and Sect Boundaries

1. Implement `EventQuery` and migrate SQLite/in-memory queries.
2. Build the same set of parameterized contract tests for both backends.
3. Extract `SectMemberStatusService`, `sect_registry.py` and the server assembler presentation logic.

Acceptance: event filtering and hydration each have only one execution path; the core `Sect` no longer depends on i18n, the static technique registry or API DTOs.

### Phase C: Real Module Migration

1. Move all implementations out of `avatar_init/__init__.py` and delete the reverse re-exports.
2. Move all implementations out of `opportunity/__init__.py` and delete the reverse re-exports.
3. Keep stable package imports, and clean up compatibility files that are no longer needed.

Acceptance: both `__init__.py` files only serve as the public API; importing from any submodule does not indirectly load the full subsystem through `__init__.py`.

### Phase D: LLM Error Model and Failure Observability

1. Introduce `ProviderCallError` and replace the transport string exceptions.
2. Audit broad `except Exception` in the modules of this round; critical I/O, queries and mutations must not return fake empty values.
3. Add tests for provider HTTP/network/invalid-response, SQLite read failures and mutation failures.

Acceptance: critical failures have the original exception chain, structured logs and stable error classification; callers can distinguish "no results" from "read failure".

## 6. Testing and Definition of Done

Each phase runs at least the affected tests; after a phase is complete run `pytest -n 8`, and run `pytest` before merging the whole round.

This spec is complete when:

1. `main.py` is a thin composition root, and application services are no longer assembled from long function lists.
2. `Sect`, event queries, avatar init and opportunity all have real module boundaries consistent with their responsibilities.
3. The SQLite and in-memory event backends return the same event set, order and major/minor/story semantics for the same query spec.
4. The LLM transport uses structured exceptions and no longer recovers error types from encoded strings.
5. All new modules in this round follow the existing architecture constraints for runtime mutation, i18n, save JSON and story events.
6. The affected unit tests, public API tests, save tests and full backend test suite pass.
