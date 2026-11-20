# External Control API Foundation Refactor Plan

This document records the overall design and rollout plan for the "external control API" direction. The goal is not to patch in a few scattered endpoints, but to refactor the server into a stable foundation that is suited to long-term evolution, easy for external agents to integrate with, and easy to keep vibe coding on.

## 1. Background and Goals

The project already has a set of usable read-only query APIs and a small number of control APIs:

- Read side: world snapshot, map, detail, paginated events, rankings, sect relations, dynasty/mortal overview.
- Write side: start game, pause/resume, reset, set long-term objective, set celestial phenomenon, create/delete avatar, avatar adjustment, save/load.

These capabilities are already enough for external tools to "observe the world", and a third-party skill has already integrated successfully on top of the existing APIs.

However, the current architecture still has the following problems:

1. The routing layer is too thick: `src/server/main.py` directly handles a large amount of domain reads and writes.
2. Runtime state is concentrated in the global `game_instance` dict, with unclear boundaries.
3. Write endpoints have no unified serialization entry point, which creates a risk of state races once external agents call them at high frequency.
4. Existing endpoints are more of an "internal frontend contract" than a "stable external contract".
5. Success/failure response styles are inconsistent, which is bad for the README, docs, skills, and third-party integrations.

Core goals of this refactor:

1. Define a clear stable boundary for the external API.
2. Make "querying the world" and "intervening in the world" two clearly separate models.
3. Make adding future endpoints a matter of adding a query/command inside the existing framework, rather than piling on more logic.
4. Support playing, observing, and limited control through external agents such as Claw.

## 2. Refactor Principles

### 2.1 No forward compatibility required

This refactor is allowed to break the old internal endpoint names and response formats.

Principles:

- Prioritize straightening out the structure.
- Do not keep spreading old names, old response formats, or old mixed responsibilities for the sake of compatibility.
- If the frontend needs to adapt, prefer having the frontend follow the new contract.

### 2.2 Take "external integration", not "private frontend endpoints", as the primary perspective

The primary consumers of the new API are assumed to be:

- External AI skills
- Claw / agents
- Automation scripts
- Debugging tools

Therefore the endpoints should have:

- Clear naming
- Clear DTOs
- Stable error responses
- A clear read-only/write boundary
- Clearly stated side effects

### 2.3 No "universal patch API"

This refactor does not recommend designing a generic write endpoint along the lines of "patch any field on any object".

Prefer a "semantic command" model instead, for example:

- `set_long_term_objective`
- `set_world_phenomenon`
- `create_avatar`
- `delete_avatar`
- `adjust_avatar_loadout`
- `relocate_avatar`
- `change_avatar_sect`
- `modify_avatar_relation`

This keeps:

- Constraints clear
- Validation logic centralized
- Documentation readable
- Tests easy to write

## 3. Target Architecture

### 3.1 Layering

Recommended split into four layers:

#### A. Runtime / Session layer

Suggested new modules, for example:

- `src/server/runtime/session.py`
- `src/server/runtime/locks.py`

Responsibilities:

- Hold the current runtime state in one place
- Replace the direct reads/writes of `game_instance` scattered across `main.py`
- Expose the current `world / sim / run_config / init_status / llm_status`
- Provide unified pause/resume/reset/start/load/save lifecycle entry points
- Provide the mutation serialization lock

Suggested core objects:

- `GameSessionState`
- `GameSessionRuntime`

#### B. Application Services layer

Suggested new modules, for example:

- `src/server/services/game_queries.py`
- `src/server/services/game_lifecycle.py`
- `src/server/services/world_control.py`
- `src/server/services/avatar_control.py`

Responsibilities:

- Receive the business intent corresponding to route parameters
- Call the runtime and domain objects
- Return explicit DTOs or result objects

Requirements:

- Services may depend on the runtime, assemblers, and the domain layer
- Services do not depend directly on FastAPI request/response objects

#### C. API / DTO / Assembler layer

Suggested new modules, for example:

- `src/server/api/public_v1/*.py`
- `src/server/schemas/public_api.py`
- `src/server/assemblers/*.py`

Responsibilities:

- Parameter validation
- DTO definitions
- Unified success/failure response format
- Route mounting

Requirements:

- The routing layer only does "validate -> call service -> return DTO"
- No hand-written business logic scattered across the routing layer

#### D. Domain layer

Existing `src/classes/**`, `src/sim/**`, `src/systems/**`

Responsibilities unchanged:

- Maintain rules, state, simulator stepping, and domain behavior

Constraints:

- The domain layer does not depend back on `server/main.py`
- The domain layer is unaware of "what the HTTP endpoints look like"

### 3.4 Server module map after the current rollout

As of the current refactor rollout, the `src/server` side has the following division of responsibilities:

- `src/server/main.py`
  - The repository's default entry point and composition root
  - Assembles the runtime, services, app, and startup entry point
- `src/server/services/game_query_service.py`
  - Aggregates public v1 queries and DTO assembly
  - Owns the runtime, assembler, serializer, and static data dependencies
- `src/server/services/game_command_service.py`
  - Aggregates public v1 command orchestration
  - Owns write operations such as lifecycle / avatar / save-load / custom content
- `src/server/init_flow.py`
  - Aggregates the game-start initialization flow
  - Includes resource scanning, map loading, world creation, applying the world setting, sect/NPC initialization, LLM checks, and first-step event generation
- `src/server/loop_runtime.py`
  - Aggregates the background game loop, tick payload assembly, and autosave triggering logic
- `src/server/host_app.py`
  - Aggregates the FastAPI app / lifespan / router / mounts / startup entry host logic
- `src/server/bootstrap.py`
  - Aggregates runtime path resolution, host/port resolution, and browser target address preparation
- `src/server/serialization.py`
  - Aggregates shared serialization functions, such as events, celestial phenomena, and hidden domain state
- `src/server/public_helpers.py`
  - Aggregates general runtime helpers, such as avatar asset scanning, save name validation, and applying the runtime locale

This means that when adding new external capabilities, you should prefer to:

- Consider placing new read-only endpoints in `GameQueryService` and the corresponding assembler first.
- Consider placing new write endpoints in `GameCommandService` first.
- Extend `init_flow.py` for new initialization steps first; do not stuff phase logic back into `main.py`.
- Extend `host_app.py` / `bootstrap.py` for new host/startup behavior first.

### 3.2 Namespaces

Suggested stable prefixes for all new endpoints:

- `/api/v1/system/*`
- `/api/v1/query/*`
- `/api/v1/command/*`

Or a more resource-style alternative:

- `/api/v1/runtime/*`
- `/api/v1/world/*`
- `/api/v1/avatars/*`
- `/api/v1/events/*`

This project recommends the first option, because it naturally separates query / command and makes side effects easy for external agents to understand.

Suggested split:

- `query`
  - Read-only, no side effects
  - Safe for skills and agents to call at high frequency
- `command`
  - Has side effects
  - Must go through the unified lock and unified validation

### 3.3 Response format

Suggested unified format:

Success:

```json
{
  "ok": true,
  "data": {}
}
```

Failure:

```json
{
  "ok": false,
  "error": {
    "code": "WORLD_NOT_READY",
    "message": "World not initialized",
    "details": {}
  }
}
```

Constraints:

- No more mixing the two semantics of `200 + {"error": ...}` and `HTTPException(detail=...)`.
- HTTP status codes may still be used internally to distinguish error categories, but the response body structure should be stable.
- `error.code` must be a stable string so that skills can make programmatic decisions.

## 4. Concurrency and Robustness Foundations

### 4.1 Mutation serialization

This refactor must establish a unified mutation entry point.

Recommendations:

- The runtime holds a single unified `asyncio.Lock`
- All write operations go through `runtime.run_mutation(...)`
- `Simulator.step()` also runs through the same execution channel

Goals:

- Avoid HTTP mutations and `sim.step()` modifying the world concurrently
- Avoid multiple external commands writing to the world at the same time

### 4.2 Cultivation realm aliases and stable IDs

Cultivation realms may appear in query results as two kinds of fields at once:

- Stable IDs: `realm`, `stage`, `realm_id`, `stage_id`, with values from the domain enums, e.g. `FOUNDATION_ESTABLISHMENT`, `EARLY_STAGE`.
- Display aliases: `cultivation.display_full_name`, `cultivation_display`, which vary with the avatar's orthodoxy or race. For example, the same standard realm may be displayed as "Foundation Establishment Early Stage", "Tendon-Tempering, Initial Attainment", "Principle Illumination, Early Realm", or "Form Transformation Early Stage".

External API constraints:

- All commands, action params, and script automation input must use stable IDs.
- Display aliases returned by queries are only for UI, logs, narrative, or helping agents understand the world; they must not be fed back as command parameters.
- If the same response includes both `realm` and `cultivation`, `realm` keeps the stable ID semantics and `cultivation` carries the display semantics.

### 4.3 Snapshot semantics of queries

Queries should not directly expose "mid-update" temporary state.

Recommendations:

- Simple queries may read the current state directly
- For large queries or queries that assemble multiple objects, prefer encapsulating them in a service so that fields within a single response are semantically consistent

### 4.4 Lifecycle guards

All commands must uniformly validate:

- Whether the world has been initialized
- Whether mutations are currently allowed
- Whether a load/initialization is currently in progress
- Whether the target object exists

Avoid having each endpoint repeat these checks on its own.

## 5. Scope of the First Batch of v1 APIs

### 5.1 Query API

First batch opened as stable:

1. `GET /api/v1/query/runtime/status`
2. `GET /api/v1/query/world/state`
3. `GET /api/v1/query/world/map`
4. `GET /api/v1/query/detail`
5. `GET /api/v1/query/events`
6. `GET /api/v1/query/rankings`
7. `GET /api/v1/query/sect-relations`
8. `GET /api/v1/query/sects/territories`
9. `GET /api/v1/query/system/current-run`
10. `GET /api/v1/query/meta/game-data`
11. `GET /api/v1/query/meta/avatars`
12. `GET /api/v1/query/meta/avatar-adjust-options`
13. `GET /api/v1/query/meta/avatar-list`
14. `GET /api/v1/query/meta/phenomena`
15. `GET /api/v1/query/mortals/overview`
16. `GET /api/v1/query/dynasty/overview`
17. `GET /api/v1/query/dynasty/detail`
18. `GET /api/v1/query/saves`

### 5.2 Command API

First batch opened as stable:

1. `POST /api/v1/command/game/start`
2. `POST /api/v1/command/game/pause`
3. `POST /api/v1/command/game/resume`
4. `POST /api/v1/command/game/reset`
5. `POST /api/v1/command/game/reinit`
6. `POST /api/v1/command/game/save`
7. `POST /api/v1/command/game/load`
8. `POST /api/v1/command/game/delete-save`
9. `POST /api/v1/command/system/shutdown`
10. `DELETE /api/v1/command/events/cleanup`
11. `POST /api/v1/command/world/set-phenomenon`
12. `POST /api/v1/command/avatar/set-long-term-objective`
13. `POST /api/v1/command/avatar/clear-long-term-objective`
14. `POST /api/v1/command/avatar/create`
15. `POST /api/v1/command/avatar/delete`
16. `POST /api/v1/command/avatar/update-adjustment`
17. `POST /api/v1/command/avatar/update-portrait`
18. `POST /api/v1/command/avatar/generate-custom-content`
19. `POST /api/v1/command/avatar/create-custom-content`

### 5.3 Deferred to the second batch

These capabilities are better added once the foundation is stable:

1. Change avatar location
2. Change avatar sect membership
3. Change avatar relations
4. Trigger specific world events
5. Write world values directly
6. Multiple sessions / multiple instances
7. Authentication and permission levels

## 6. Recommended Directory Structure

```text
src/server/
  api/
    public_v1/
      __init__.py
      query.py
      command.py
      system.py
  runtime/
    __init__.py
    session.py
    locks.py
  schemas/
    public_api.py
    query.py
    command.py
  services/
    game_queries.py
    game_lifecycle.py
    world_control.py
    avatar_control.py
```

Notes:

- It is not required to split out all files at once.
- The first stage can extract the runtime and core services first, then gradually migrate routes to `public_v1`.

## 7. Phased Implementation Plan

### Phase 0: Design freeze

Goals:

- Define the namespaces
- Define the unified response format
- Define the runtime/service layering
- Confirm the scope of the first batch of v1 APIs

Deliverables:

- This document
- `.cursor` rules and skill
- `AGENTS.md` summary

### Phase 1: Runtime foundation refactor

Goals:

- Introduce `GameSessionRuntime`
- Consolidate `game_instance`
- Provide unified read/write entry points
- Establish the mutation lock

Suggested tasks:

1. Create the runtime module
2. Encapsulate `world/sim/run_config/init_status/is_paused` in the runtime
3. Migrate `start/reinit/reset/pause/resume` to the lifecycle service
4. Make `game_loop` and HTTP mutations share a unified serialization mechanism

Done criteria:

- Routes no longer operate on `game_instance` directly in scattered places
- `sim.step()` and mutations do not write to the world concurrently

### Phase 2: Query Service and Public Query API

Goals:

- Organize the main read-only endpoints into a stable query contract

Suggested tasks:

1. Extract `GameQueryService`
2. Migrate `/state`, `/map`, `/detail`, `/events`, etc. to the query service
3. Create `/api/v1/query/*`
4. Return `ok/data` uniformly

Done criteria:

- Read-only endpoints have a stable prefix, stable DTOs, and a stable error format

### Phase 3: Command Service and Public Command API

Goals:

- Migrate existing control endpoints to the command model

Suggested tasks:

1. Extract `AvatarControlService`
2. Extract `WorldControlService`
3. Extract `GameLifecycleService`
4. Create `/api/v1/command/*`

Done criteria:

- All commands go through the unified runtime mutation entry point
- Commands no longer modify the world directly in the routing layer

### Phase 4: Frontend and documentation follow-up

Goals:

- Switch the frontend to the v1 contract
- Complete the README / docs / skill

Suggested tasks:

1. Switch frontend `web/src/api/**` to the new endpoints
2. Add a "supports external agent / Claw integration" section to the README
3. Add external API usage documentation
4. Add example requests and error code descriptions

### Phase 5: Second batch of control capabilities

Once the foundation is stable, continue adding:

- Location control
- Sect membership changes
- Relation control
- World intervention commands

## 8. Testing Strategy

This refactor must add the following tests:

### 8.1 Runtime tests

- Lifecycle state transition tests
- Mutation lock behavior tests
- Initializing / uninitialized / ready state guard tests

### 8.2 Query API tests

- Success response format for `/api/v1/query/*`
- Unified error format for an empty world / uninitialized state
- Event pagination contract does not regress

### 8.3 Command API tests

- Happy path for all commands when the world is ready
- Error codes for invalid parameters, missing targets, and disallowed states
- Serialization behavior between commands and the runtime

### 8.4 Regression tests

- Initialization flow
- Save/load
- WebSocket tick
- Avatar adjustment
- Event queries

## 9. Vibe Coding Checklist

Anyone who continues extending the external control API should first check:

1. Is this a query or a command?
2. Should it go into an existing service rather than being written into `main.py` again?
3. Does it reuse the unified runtime rather than touching global state directly?
4. If it is a command, does it go through the unified mutation lock?
5. Does the response conform to the unified `ok/data` or `ok/error` contract?
6. Did you add API tests, rather than only testing domain logic?
7. Do the README / docs / skill need to be updated as well?

## 10. Current Conclusion

This direction is worth pursuing, and it is suitable for a one-time "foundation refactor".

The most important thing in this round is not how many endpoints get added, but locking down these four things:

1. A stable v1 namespace
2. The three-layer runtime/service/API boundary
3. Query / command separation
4. Mutation serialization

Once these four are in place, adding new endpoints will go very smoothly; whether it is the README, the Claw skill, or further vibe coding, there will be a single consistent handle to work from.

## 11. Compatibility Layer Status and Removal Order

As of the current stage, `/api/v1/*` is already the main path for both the frontend runtime and external agents; the old `/api/*` routes mostly serve as a compatibility layer.

### 11.1 Removed legacy namespaces

The first and final batches of legacy query compatibility layers have now all been removed, including:

- `/api/meta/*`
- `/api/events`
- `/api/events/cleanup`
- `/api/rankings`
- `/api/sect-relations`
- `/api/sects/territories`
- `/api/mortals/overview`
- `/api/dynasty/overview`
- `/api/dynasty/detail`
- `/api/control/*`
- `/api/action/*`
- `/api/game/*`
- `/api/saves`

### 11.2 Current dependency distribution

- `web/src` frontend runtime code:
  - Business endpoints have essentially all switched to `/api/v1/*`
  - The exceptions are the settings source of truth `/api/settings*` and `/api/settings/llm*`, which belong to the application settings surface, not the external control compatibility layer
- `tests/*`:
  - External-control-related tests have all been migrated to `/api/v1/*`
- Docker / deployment contracts:
  - The Docker health check has been migrated to `/api/v1/query/runtime/status`
  - The Docker smoke test has been migrated to `/api/v1/query/world/state`, `/api/v1/command/game/*`, and `/api/v1/query/saves`
- Repository docs and rules:
  - Any remaining references to old paths should be treated as historical docs pending cleanup, not as a compatibility promise

### 11.3 Recommended removal order

The first batch has been removed:

1. Old `/api/meta/*`
2. Old `/api/action/*`
3. Old `/api/control/*`
4. Old `/api/game/*`
5. Old `/api/saves`
6. Old `/api/events*`
7. Old `/api/rankings`, `/api/sect-relations`, `/api/sects/territories`
8. Old `/api/mortals/overview`, `/api/dynasty/*`

Recommended next steps at the current stage:

1. All new APIs are mounted only under `/api/v1/query/*` or `/api/v1/command/*`
2. If docs, rules, or tests still reference old `/api/*` paths, keep cleaning them up
3. Write all future examples, skills, and agent guides against the v1 contract

### 11.4 Current code policy

The old `/api/*` compatibility routes have been removed; the current constraints are:

- New features must not be mounted on the old namespace
- External control, the frontend runtime, tests, and docs all treat `/api/v1/*` as the only stable contract
- `/api/settings*` and `/api/settings/llm*` are still kept as the application settings source of truth and are outside the scope of this compatibility layer discussion

## 12. Minimal Claw / Agent Integration Pattern

If the goal is just to build a control skill that "can observe, decide, and intervene", the following minimal loop is recommended:

### 12.1 Recommended order per round

1. First query `GET /api/v1/query/runtime/status`
2. If `status` is not `ready`:
   - If the game has not started, call `POST /api/v1/command/game/start`
   - If it is initializing, keep polling `runtime/status`
   - If it is in an error state, read the error information first and decide whether to `reinit`
3. Once the world is ready, query:
   - `GET /api/v1/query/world/state`
   - `GET /api/v1/query/events`
   - `GET /api/v1/query/detail` when needed
4. Call one semantic command according to your strategy
5. After the command completes, go back to querying rather than assuming the local state is necessarily correct

### 12.2 Recommended minimal endpoint set

For basic control only, these are usually all you need:

- Status:
  - `GET /api/v1/query/runtime/status`
- Observation:
  - `GET /api/v1/query/world/state`
  - `GET /api/v1/query/events`
  - `GET /api/v1/query/detail`
- Control:
  - `POST /api/v1/command/game/start`
  - `POST /api/v1/command/game/pause`
  - `POST /api/v1/command/game/resume`
  - `POST /api/v1/command/avatar/set-long-term-objective`
  - `POST /api/v1/command/world/set-phenomenon`

### 12.3 Minimal template for adding a new endpoint

When adding a new endpoint later, decide as follows:

- New read-only capability:
  - Once the service / assembler is ready, wire it into `src/server/services/game_query_service.py`
  - Then mount it on `src/server/api/public_v1/query.py`
- New write capability:
  - Put business logic in a service first
  - Wire the command orchestration into `src/server/services/game_command_service.py`
  - Then mount it on `src/server/api/public_v1/command.py`
- If it modifies world / sim:
  - It must go through runtime mutation serialization
- If the frontend also consumes it:
  - Update `web/src/types/api.ts` and the corresponding mapper as well

### 12.4 Discouraged practices

- Do not depend on old `/api/*` paths from a skill
- Do not assume the local cache is the truth after a command; prefer querying again
- Do not add "universal patch" style write endpoints
- Do not pile new public endpoint logic back into `src/server/main.py`
