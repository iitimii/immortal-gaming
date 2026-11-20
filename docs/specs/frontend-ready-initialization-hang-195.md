# Issue #195: Frontend Stuck at the Enter-Game Stage After Ready in Dev Mode

This document records the symptom analysis, LLM relevance assessment and follow-up fix plan for issue #195 from 2026-05.

Current status: this document is still a troubleshooting/fix spec pending closure, not a completed historical document. The code's `runtime.finish_initialization()` already supports passing `phase_name="complete"`, but the main initialization flow for a new game still needs further review of the phase semantics after ready and the recoverable frontend initialization logic.

## 1. User Symptoms

User report:

1. Started in dev mode.
2. After clicking to enter the game, the UI no longer advances.
3. F12 Network keeps showing `runtime/status` polling.
4. `runtime/status` returns:

```json
{
  "ok": true,
  "data": {
    "status": "ready",
    "phase": 6,
    "phase_name": "generating_initial_events",
    "progress": 100,
    "error": null,
    "llm_check_failed": false,
    "llm_error_message": "",
    "is_paused": false
  }
}
```

Key judgement: this is not the typical "backend initialization has not finished" state. `status=ready` and `progress=100` show that the server already considers world initialization complete.

## 2. Current Initialization Chain

The server-side initialization order is in `src/server/init_flow.py`:

1. phase 0: scan resources.
2. phase 1: load map.
3. phase 2: generate world background.
4. phase 3: initialize sects.
5. phase 4: generate avatars.
6. phase 5: check LLM.
7. phase 6: generate initial events.
8. `runtime.finish_initialization()` sets `init_status` to `ready` and sets progress to 100.

The frontend initialization order is in `web/src/composables/useGameInit.ts`:

1. Poll `/api/v1/query/runtime/status` every second.
2. Preload map, avatars and textures early at certain phases.
3. When the status changes from non-`ready` to `ready` and `isInitialized=false`, run `initializeGame()`.
4. `initializeGame()` connects the Socket and loads the world snapshot, map, base textures, events and sect territories.
5. Only after `systemStore.setInitialized(true)` does `useAppShell` switch from `initializing` to `game`.

Therefore the most likely location of this problem is not the server-side new-game task, but the second-stage frontend initialization after ready.

## 3. Suspect Points

### 3.1 Leftover phase_name causes misjudgement

The server's `finish_initialization()` currently only guarantees `status=ready` and `progress=100`; it does not force `phase_name` to be cleaned up to `complete`.

So `status=ready` together with `phase_name=generating_initial_events` is an explainable leftover state, and should not on its own be judged as the backend hanging.

Improvement direction:

1. After ready, set `phase_name` to `complete`.
2. Frontend display and logic use only `status` as the completion check, and must not be misled by the phase text.

### 3.2 The ready transition triggers only once

`useGameInit.ts` currently only runs `initializeGame()` when the following condition holds:

```ts
prevStatus !== 'ready' && res.status === 'ready' && !isInitialized.value
```

This leads to several edge-case problems:

1. If `initializeGame()` ran on that ready tick, but some internal request failed, hung or was cancelled by the browser, subsequent polls are still ready but will not retry.
2. If the first status the frontend sees is already ready, but the frontend's internal state did not correctly become initialized, the chance to recover may also be missed.
3. A user looking only at Network sees `runtime/status` polling normally, while the page stays on the initialization shell.

Improvement direction:

1. Change the trigger condition to `res.status === 'ready' && !isInitialized.value && !isInitializingFrontend.value`.
2. Add a frontend initialization guard to avoid concurrent duplicate initialization.
3. Release the guard on initialization failure, and record clear error context.
4. Add a retry strategy for frontend initialization after ready.

### 3.3 Frontend initialization swallows errors internally

`worldStore.initialize()` currently only logs the error after catching it, and does not rethrow. Callers cannot know whether the world was actually initialized successfully.

Risks:

1. When `world/state`, map, events, sect territories or resource requests fail, the caller may keep going.
2. The error may only appear in the console, with no explicit error state on the page.
3. If some fetch stays pending forever, since the HTTP client has no timeout, `initializeGame()` will not return for a long time.

Improvement direction:

1. `worldStore.initialize()` returns an explicit result or rethrows on failure.
2. `initializeGame()` checks `worldStore.isLoaded` before setting `isInitialized=true`.
3. Add a configurable timeout to the HTTP client so initialization requests do not stay pending indefinitely.
4. When ready but frontend initialization exceeds a threshold, the loading overlay shows "Loading world data/resources" and provides diagnosable error information.

## 4. LLM Relevance Assessment

Judging from the response the user provided, this problem is most likely not caused by LLM configuration or LLM call failure.

Reasons:

1. The LLM check happens in phase 5: `checking_llm`.
2. Even if the LLM connectivity check fails, the server only sets:
   - `llm_check_failed=true`
   - `llm_error_message=<error message>`
   and then continues to phase 6.
3. The user's response has `llm_check_failed=false` and `llm_error_message=""`, meaning the server considers the LLM check passed.
4. The user's response is already `status=ready` and `progress=100`, meaning the server has already passed the LLM check and initial event generation stages.

Possible remaining LLM impact:

1. If LLM responses are slow, they may lengthen phase 5 or phase 6.
2. phase 6 runs one `sim.step()` to generate initial events; some actions, story events or systems may indirectly trigger the LLM.
3. But once `ready` has finally been returned, the LLM is no longer the direct blocker for "cannot enter the game".

Evidence criteria for further LLM investigation:

1. Only if the status stays at `checking_llm` or `generating_initial_events` for a long time with `status=in_progress` should the LLM or initial event generation be suspected first.
2. If the status is `ready`, first investigate the frontend's post-ready world snapshot, map, events, sect territories, texture resources and Socket initialization.
3. If `llm_check_failed=true`, this is the configuration reminder path and should not cause the frontend to hang after ready.

## 5. Suggested Diagnostic Information to Request from the User

Ask the issue author to provide from F12:

1. Whether the Console has red errors.
2. Whether, in Network, besides `runtime/status`, the following requests are pending, failed or 404:
   - `/api/v1/query/world/state`
   - `/api/v1/query/map`
   - `/api/v1/query/events`
   - `/api/v1/query/sects/territories`
   - `/api/v1/query/avatars/meta`
   - `tiles/*.png`
   - `males/*.png`
   - `females/*.png`
3. Whether the current page still shows the loading overlay, or a black screen / empty shell.
4. Whether a non-root path, proxy, Electron dev, reverse proxy or custom `VITE_API_TARGET` is used.

## 6. Fix Plan

### 6.1 Consolidate server status semantics

1. Set `phase_name` to `complete` when initialization finishes.
2. Keep `status=ready` as the sole completion semantics.
3. Add test coverage: the ready status no longer retains `generating_initial_events` as the current phase name.

### 6.2 Make frontend post-ready initialization recoverable

1. Add `isInitializingFrontend` in `useGameInit`.
2. Attempt initialization when `res.status === 'ready' && !isInitialized.value`.
3. Do not start a second initialization while one is in progress.
4. After initialization failure, record the error, release the guard, and allow the next poll to retry.
5. Set `isInitialized=true` only after initialization succeeds.

### 6.3 Make world initialization errors explicit

1. `worldStore.initialize()` no longer silently swallows fatal initialization errors.
2. The initialization caller sets a frontend initialization error state based on the error.
3. When ready but frontend initialization fails, the loading overlay shows a readable error instead of an endless spinner or an empty shell.

### 6.4 HTTP timeout and diagnostics

1. `httpClient` supports a default timeout.
2. Critical initialization requests can provide more specific error labels.
3. Console logs need to distinguish:
   - status polling failure
   - world snapshot failure
   - map failure
   - event pagination failure
   - sect territory failure
   - texture resource failure

## 7. Verification Strategy

Frontend tests:

1. When the first poll directly returns ready, `initializeGame()` should run.
2. When frontend initialization fails after ready, the next poll should be able to retry.
3. While initialization is in progress, consecutive ready polls should not call `initializeGame()` concurrently.
4. After initialization succeeds, it is not repeated.
5. When `worldStore.initialize()` fails, `isInitialized=true` should not be set.

Backend tests:

1. After initialization completes, `status=ready` and `progress=100`.
2. After initialization completes, `phase_name=complete` or an equivalent completion state.
3. When the LLM check fails, ready can still be reached, but `llm_check_failed=true` is retained.

Manual verification:

1. `cd web && npm run test`.
2. `pytest tests/test_init_status_api.py tests/test_game_init_integration.py`.
3. Start in dev mode, and enter the game normally with a new game.
4. Artificially make `world/state` return a failure, and confirm the page does not hang permanently without diagnostics.
