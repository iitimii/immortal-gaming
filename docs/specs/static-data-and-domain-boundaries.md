# Static Data and Domain Boundary Refactor Plan

## 1. Background

The project's current server runtime and query / command boundaries already have a basic structure, but another set of
boundary problems remains that will keep amplifying maintenance cost: static data is loaded on import in multiple modules and each reloads on its own; some
systems mix configuration, runtime state, simulation settlement, persistence and API presentation in the same file; the LLM transport
still carries a legacy string error protocol.

This plan targets responsibility boundaries and verifiable behavior, and does not change world rules, public API business semantics or the save format.

## 2. Goals

1. Replace the scattered module-level `reload()` coordination with a unified static data catalog and reload lifecycle.
2. Split the definition, runtime, discovery flow, save and API presentation responsibilities of world secrets.
3. Evolve fortune / misfortune into an extensible outcome handler registration model.
4. Separate the LLM transport, failure classification and call orchestration, and retire the string error protocol.
5. Establish an extensible structured definition model for the effect system, but do not rewrite it solely because "the file is too long".

## 3. Non-Goals

1. Do not modify `/api/v1/*` endpoints, the response envelope or frontend DTOs, unless fixing a clear contract error.
2. Do not change random probabilities, event text semantics, action settlement or the save JSON shape.
3. Do not introduce a generic DI framework or a new global catch-all container.
4. Do not maintain long-term dual tracks for legacy import paths and old error strings; zero-cost adapters may only be used as a migration means with a removal condition.

## 4. Overall Dependency Direction

```text
config files -> static catalog -> domain definitions -> runtime state -> simulation services
                                                               -> persistence / API assemblers

LLM task -> runtime coordinator -> provider adapter
                           -> failure classifier
```

- Static definitions must not hold current-run objects such as world or avatar.
- Runtime state only stores JSON primitive types and cross-object IDs.
- API assemblers only read domain / runtime state, and do not drive simulation settlement in reverse.
- Dynamic values after config reload must be obtained through call-time getters or a catalog snapshot.

## 5. Static Data Catalog and Reload Lifecycle

### 5.1 Current Problems

`src/run/data_loader.py` has to manually orchestrate the `reload()` of multiple domain modules, while each module loads global dicts directly on import.
After reload, `fix_runtime_references()` is still needed to repair avatars' references to old sect, item,
race and other objects, which shows that the identity, version and runtime binding of static definitions have no unified entry point.

### 5.2 Target Design

Add `StaticCatalogService` (may live in `src/run/static_catalog/`):

```text
StaticCatalogService
  - load() -> StaticCatalogSnapshot
  - current() -> StaticCatalogSnapshot
  - generation: int
  - reload(reason) -> StaticCatalogSnapshot
  - rebind_world(world, previous, current)
```

`StaticCatalogSnapshot` is an immutable catalog view containing definitions keyed by ID for sect, technique, weapon, auxiliary,
persona, race, goldfinger, phenomenon and so on. Each loader registers in explicit dependency order;
the catalog is responsible for building a new snapshot in one pass, and atomically replaces the current snapshot on success.

### 5.3 Requirements

1. New code must not call `reload()` on import or expose mutable module-level config dicts as the source of truth.
2. `data_loader.reload_all_static_data()` shrinks into a facade over the catalog, and no longer hardcodes the call order of each domain module.
3. `rebind_world()` migrates runtime references uniformly by ID and returns a structured report; missing definitions must not be silently swallowed.
4. locale / settings reload is triggered through the catalog generation; callers must not cache a stale CONFIG.
5. Old module-level dicts may only serve as short-term read-only adapters, and are deleted once migration is complete.

### 5.4 Acceptance

- After reloading the same config, the catalog generation increments and references within the snapshot are consistent.
- Rebinding of living avatars, dead avatars, sect members and the current celestial phenomenon uses a unified mechanism.
- A single loader failure does not replace the currently usable snapshot.
- Static reference tests after locale switching, starting a new game and loading a save cover both success and failure paths.

## 6. World Secret Boundaries

### 6.1 Target Modules

```text
src/systems/world_secret/
  definitions.py       # config table parsing, option DTO, definition lookup
  models.py            # fragment, binding, knowledge, runtime state
  initialization.py    # current-run random selection and trigger binding
  discovery.py         # monthly discovery and single-choice disclosure flow
  persistence.py       # JSON serialize / load
  overview.py          # API overview assembler
  __init__.py          # stable public entry point
```

### 6.2 Requirements

1. Definition loading reads from `StaticCatalogService`, rather than repeatedly reading config files in business functions.
2. `WorldSecretRuntime` and avatar knowledge keep save-friendly pure JSON / ID semantics.
3. Disclosure choices continue to go through the unified `single_choice` resolver; the discovery flow only produces factual events, which are then stored per the existing event rules.
4. `overview.py` must not modify the runtime or create knowledge; missing state may only be normalized in the initialization / load layer.
5. Text and DTOs required by the API are produced by backend assemblers; the frontend does not add Chinese fallbacks.

### 6.3 Acceptance

- Definition parsing, initialization binding, discovery, disclosure, save round-trip and overview can each be tested independently.
- Adding a new trigger kind only requires extending the definition schema and discovery handler, without modifying persistence / overview.
- After public disclosure, all avatars' knowledge is synchronized and events are not generated twice.

## 7. Fortune and Misfortune Outcome Registry

### 7.1 Target Design

Split `fortune.py` into:

```text
src/systems/fortune/
  models.py            # FortuneKind, candidate records, result objects
  eligibility.py       # trigger conditions and weights
  outcomes.py          # outcome handler registry
  fortune_service.py   # fortune orchestration
  misfortune_service.py# misfortune orchestration
  events.py            # factual events and StoryEventService integration
```

Each outcome handler is responsible for `can_apply()`, `apply()` and a structured factual result; the orchestration service only selects
candidates, executes handlers and submits events. Fortune and misfortune share filtering, weights and the event protocol, but do not share unrelated reward logic.

### 7.2 Requirements and Acceptance

1. New outcomes are not wired in by extending a large `if / elif` chain.
2. Each handler's eligibility, rewards and event output have their own unit tests.
3. test mode does not call the real LLM; story expansion continues to go through `StoryEventService`.
4. Existing probabilities, reward ranges and event types stay unchanged, and are locked down with parameterized regression tests.

## 8. LLM Transport and Failure Model

### 8.1 Target Modules

```text
src/utils/llm/
  providers/openai_compatible.py
  providers/anthropic.py
  providers/base.py
  failure_classifier.py
  coordinator.py
  client.py             # keeps only the stable public facade
```

### 8.2 Requirements

1. Provider adapters are only responsible for request normalization, HTTP calls and `ProviderCallError` conversion.
2. The failure classifier only consumes structured exceptions; `HTTP_...::...` and `NETWORK_ERROR::...` are supported only briefly in a migration adapter.
3. The coordinator is responsible for concurrency control, test mode, failure notification, JSON parse retry and logging.
4. JSON retry only handles `ParseError`; provider / network failures are raised upward as-is.
5. The connectivity check reuses the adapter and classifier, and does not duplicate request logic.

### 8.3 Acceptance

- HTTP, network and invalid-response failures for both OpenAI-compatible and Anthropic are mapped to structured exceptions.
- Classification of quota, auth, rate limit, server error and unknown error is stable.
- test mode fails closed for unknown tasks and never reaches a real provider.
- Failure notification, the concurrency limit and user-readable errors keep their existing behavior.

## 9. EffectDefinition Registry

`effect/consts.py` currently consists mainly of constants and descriptions, and is not split just because of its line count. Only when effects need types,
default values, stacking rules, visibility or UI metadata is the following introduced:

```python
@dataclass(frozen=True)
class EffectDefinition:
    key: str
    value_type: type
    merge_strategy: MergeStrategy
    default: object
    visibility: EffectVisibility
```

Requirements: the effect parser, merge, config validation and API presentation share the registry; unknown effects fail by default and report the
source path; existing constants may serve as key aliases during migration, and are ultimately exported by the registry.

Acceptance: all existing effect keys can be parsed; wrong types / unmergeable values fail at load time; adding a new effect does not require updating multiple lists of valid keys in sync.

## 10. Implementation Order and Verification

1. StaticCatalogService and the runtime rebinding contract.
2. Split world secrets and switch them to the catalog.
3. Fortune / misfortune outcome registry.
4. LLM provider adapter and failure classifier.
5. Decide whether to implement the EffectDefinition registry based on actual metadata needs.

Run the affected tests at each phase; before merging run:

```powershell
pytest -n 8
cd web; npm.cmd run test -- --run
cd web; npm.cmd run type-check
```

The completion condition is that the old entry points no longer carry real responsibilities, migration adapters have a clear removal point, and the public API, saves and simulation semantics remain stable.
