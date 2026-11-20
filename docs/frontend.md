# Frontend Architecture Guide

This document helps developers (and AI assistants) quickly understand the frontend architecture under `web/`, file responsibilities, and core data flow. Refer to it when vibe coding or refactoring.

## 1. Tech Stack

*   **Core framework**: Vue 3 (Composition API + `<script setup>`) + TypeScript
*   **Build tool**: Vite
*   **State management**: Pinia (modular stores)
*   **UI library**: Naive UI (system menu, panels, and other conventional UI)
*   **Game rendering**: Vue3-Pixi (2D rendering on Pixi.js for the map and avatar animation)
*   **Networking**: a lightweight `fetch` wrapper (`web/src/api/http.ts`)
*   **Internationalization**: Vue I18n (see `docs/frontend-i18n.md`)

## 2. Directory Structure

Root: `web/src/`

### 2.1 API Layer (`src/api/`)
Wraps all HTTP interaction with the backend.
*   `index.ts`: single export point.
*   `modules/`:
    *   `system.ts`: system-level control (start, pause, reset, saves).
    *   `world.ts`: map data, initial state, celestial phenomena.
    *   `event.ts`: paginated event log fetching.
    *   `avatar.ts` / `llm.ts`, etc.: avatar details, LLM configuration, and other domain-specific endpoints.
*   `mappers/`:
    *   `event.ts`: `EventDTO -> GameEvent` conversion and timeline order normalization.
    *   `world.ts`: normalization of `rankings/config` responses, reducing scattered compatibility logic in components and stores.
    *   New endpoints that need structural conversion should be normalized here first, then handed to stores / composables.

### 2.2 Component Layer (`src/components/`)
*   **`game/` (core game view)**
    *   `GameCanvas.vue`: Pixi.js application entry; manages the `Viewport` and layer order.
    *   `MapLayer.vue`: template shell for map rendering; Pixi lifecycle, tile building, animated water, region labels, etc. are in `components/game/composables/useMapLayerRenderer.ts`.
    *   `EntityLayer.vue`: renders avatars and interpolates movement animation.
    *   `CloudLayer.vue`: fog of war or decorative cloud layer.
    *   `panels/`: in-game floating panels.
        *   `EventPanel.vue`: left-side event log view; scrolling, filtering, and loading state are in `composables/useEventPanel.ts`.
        *   `info/`: container for detail panels of the selected object (avatar/tile).
        *   `system/`: sub-panels inside the system menu (saves, settings, LLM config, avatar creation).
*   **`layout/`**: global layout components.
    *   `StatusBar.vue`: top status bar (year, resources, etc.).
*   **`common/`**: shared UI components (custom buttons, progress bars, etc.).
*   **`settings/`**:
    *   `SettingsPanel.vue`: reusable settings panel. Owns settings such as language, volume, and autosave; it does not own the menu shell.
*   **`system-menu/`**:
    *   `tabs/`: thin wrapper components for each menu tab.
        *   `SystemMenuSettingsTab.vue`: mounts `SettingsPanel`.
        *   `SystemMenuAboutTab.vue` / `SystemMenuOtherTab.vue`: static tab content.
        *   Other tab components mainly mount existing `panels/system/` sub-panels.
*   `SystemMenuShell.vue`: system menu shell. Owns the modal frame, header, tab bar, and content slot.
*   `SystemMenu.vue`: system menu assembly entry. Combines `SystemMenuShell` with each tab's content and does not hold large chunks of business UI itself.
*   `SplashLayer.vue`: cover/start screen shown at launch.

### 2.3 Composables (`src/composables/`)
Encapsulate complex business logic to keep components light.
*   `useAppShell.ts`: app shell state machine. Manages the `boot / splash / initializing / game` scenes and when overlays such as the system menu and `LoadingOverlay` are mounted.
*   `useGameInit.ts`: game startup checks and backend heartbeat.
*   `useSystemMenuFlow.ts`: system menu flow layer. Owns menu tabs, context (`splash/game`), closability, the LLM startup check, and opening/closing the menu.
*   `useGameControl.ts`: pure game control logic, e.g. pause/resume, ESC handling, and pausing/resuming in step with menu visibility.
*   `useSidebarResize.ts`: drag-to-resize logic for the sidebar (event panel).
*   `useAudio.ts` / `useBgm.ts`: sound effects and background music.
*   `useEventPanel.ts`: event panel data loading, filtering, scrolling, and visibility.
*   `useLoadingOverlayState.ts`: progress text, phase state, and derived display state for the loading overlay.
*   `useRankingModal.ts` / `useDynastyOverviewModal.ts` / `useMortalOverviewModal.ts` / `useTimeOverviewModal.ts` / `useSectRelationsModal.ts` / `useHiddenDomainOverviewModal.ts`: data loading and derived fields for status-bar modals.
*   `useRegionDetailPanel.ts` / `useSectDetailPanel.ts` / `useAvatarPortraitPanel.ts`: local business state for detail pages and portrait swapping.
*   `components/game/composables/useTextures.ts`: Pixi texture preloading and cache management.
*   `components/game/composables/useMapLayerRenderer.ts`: map Pixi object lifecycle, static tile building, water ticker, region labels, and interaction.

### 2.4 State Management (`src/stores/`)
Pinia-based state management.
*   **`world.ts` (aggregation layer)**: **the core store**.
    *   Responsibilities: global time (year/month), celestial phenomena, hidden domains.
    *   Role: facade entry point for world-level orchestration (`initialize/handleTick`).
        Note: some compatibility proxy fields remain for a smooth migration; new code should depend on the sub-stores (`map/avatar/event`) directly.
*   **`map.ts`**: map matrix (`mapData`) and region data (`regions`).
*   **`avatar.ts`**: all avatar data (`avatars`), with incremental updates.
*   **`event.ts`**: event log (`events`), with paginated loading, filtering, and live pushes.
*   `ui.ts`: current selection and UI visibility; the system menu tab, closability, and menu context (`splash/game`) also live here.
*   `setting.ts`: frontend settings and their sync with backend configuration.
*   `socket.ts`: connection state and subscription management (light business logic).
*   `socketMessageRouter.ts`: socket message dispatch and business response routing (`tick/toast/llm_config_required/...`).

### 2.5 Types (`src/types/`)
*   `core.ts`: core frontend domain models (e.g. `AvatarSummary`, `RegionSummary`, `GameEvent`).
*   `api.ts`: data structures returned by backend endpoints (DTOs).

## 3. Core Architecture and Data Flow

### 3.1 Game Initialization
1.  **Entry**: `App.vue` mounts.
2.  **Check**: `useGameInit` checks backend status (Idle/Ready/Running).
3.  **Load**: the user clicks "Start" -> triggers `worldStore.initialize()`.
    *   Loads map data (`mapStore.preloadMap`) and initial state (`worldApi.fetchInitialState`) in parallel.
    *   Resets the event list (`eventStore.resetEvents`).
4.  **Render**: data is ready (`isLoaded = true`) -> `GameCanvas` and `MapLayer` start rendering.

### 3.2 Tick Loop
The game is server-authoritative.
1.  **Source**: the backend pushes a `TickPayloadDTO` over WebSocket or a polling endpoint.
2.  **Store update**: `worldStore.handleTick(payload)` receives the data.
    *   Updates time (`year`, `month`).
    *   Calls `avatarStore.updateAvatars` to merge avatar state incrementally.
    *   Calls `eventStore.addEvents` to insert new events into the log stream.
    *   Updates the celestial phenomenon (`currentPhenomenon`).
3.  **Reactivity**: Vue's reactivity system detects the store changes.
    *   `EntityLayer` sees coordinate changes -> triggers smooth movement animation.
    *   `EventPanel` sees new events -> auto-scrolls to the bottom.
    *   `InfoPanel` sees attribute changes on the selected avatar -> refreshes values live.

### 3.3 App Shell State Machine
Root-level page orchestration is managed centrally by `useAppShell`; `App.vue` only assembles views by scene.
1. `useGameInit` polls `initStatus` and triggers frontend initialization once when the backend is `ready` and the frontend is not yet initialized.
2. `useAppShell` reduces the root scene to four states:
    * `boot`: settings or the first `initStatus` are not ready yet; only a plain black shell is shown.
    * `splash`: the app is ready but no game has been entered; `SplashLayer` is shown underneath.
    * `initializing`: the player has started a new game or loaded a save, but frontend/backend initialization has not finished; the black shell stays underneath and `LoadingOverlay` is shown as an overlay.
    * `game`: only once both frontend and backend have finished initializing may the game UI (`StatusBar / GameCanvas / EventPanel`, etc.) render.
3. The system menu and loading screen no longer decide the underlying scene; they are mounted as overlays on top of the current scene.
4. `useSystemMenuFlow` owns the menu flow: opening/closing the menu, LLM validation, menu context, and tab navigation.
5. `useGameControl` handles only game control; it no longer switches root scenes between splash and game, nor does it hold menu business flow.

### 3.4 Scene + Overlay Constraints
To prevent invalid combinations such as "menu open with the wrong page rendered underneath", root views must follow these constraints:
1. `App.vue` must not assemble pages from multiple booleans like `showSplash/showMenu/showLoading`.
2. The main game UI may only be driven by `scene === 'game'`, never inferred from inverted conditions like "`!showSplash`".
3. When `settings/load/about` is opened from `SplashLayer`, the underlying scene is still `splash`; only a `SystemMenu` overlay is added.
4. `SystemMenu` must record its context explicitly (`splash` or `game`) for close behavior, returning to the main screen, and future extensions.

### 3.5 Menu / Settings Layering
System menu and settings UI are split into "shell + content + flow" layers:
1. `SystemMenuShell` only owns the modal container, tab bar, and content slot.
2. `SystemMenu.vue` only routes tab keys to the corresponding content components.
3. `SettingsPanel` only owns the settings themselves and doesn't know whether it lives in the system menu, the splash screen, or a future standalone settings page.
4. `useSystemMenuFlow` is the menu flow layer and owns:
    * opening/closing the menu
    * default tab and tab switching
    * the `splash/game` menu context
    * the LLM startup check and forced navigation to the `llm` tab
5. `useGameControl` must not make menu business decisions such as "which tab to jump to after opening the menu".

### 3.6 Socket Message Flow (Transport -> Router -> Store/UI)
1. `api/socket.ts` only handles WebSocket connect/reconnect/subscribe.
2. `stores/socket.ts` maintains connection state and hands messages to `socketMessageRouter`.
3. `stores/socketMessageRouter.ts` dispatches by message type to world/ui/message actions.
4. When adding a message type, change the router and DTOs first; don't branch on messages in components.

### 3.7 Rendering Architecture
*   **Vue3-Pixi**: Pixi objects are written declaratively as Vue components; complex Pixi lifecycles go into local composables, and components own the mount point and event forwarding.
*   **Performance and gotchas**:
    *   **Never put native PIXI objects (such as `Sprite`, `Container`) into Vue deep-reactive objects (`ref`, `reactive`).** This breaks PIXI's internal strict-equality (`===`) checks (e.g. `removeChild` stops working), causing memory leaks and accumulating logic bugs. To keep instance references in a component, use plain variables or `shallowRef`.
    *   The map is stored in a `shallowRef` so Vue doesn't deep-watch the 100x100 map array.
    *   Tile rendering is built once by `useMapLayerRenderer` after mount as Pixi sprites; static tiles don't take part in reactive updates and are rebuilt only when map data reloads.
    *   Dynamic effects (such as flowing water) are driven independently by `PIXI.Ticker`, not by Vue's render loop.
    *   Map region names (`MapLayer` / `utils/mapLabels.ts`) should use collision avoidance by default rather than "hide on overlap". The avoidance strategy must work for every locale enabled in `static/locales/registry.json`: compact scripts (CJK) and Latin scripts each use their own text-size estimation and line-wrapping strategy.
    *   Region-name avoidance must stay lightweight. Prefer a fixed number of candidate positions plus neighborhood collision checks (e.g. spatial buckets / grid index); avoid global pairwise comparison, force-directed simulation, per-frame layout, or any other algorithm that degrades quickly as the number of regions grows.

### 3.8 Component / Composable Boundary
The default direction for large frontend components is "template presentation layer + composable business layer".
1. Panels, modals, and detail pages keep only DOM structure, styles, event bindings, and minor display conditions.
2. Data loading, derived fields, navigation, submission, timers, Pixi lifecycles, and similar logic go into `web/src/composables/*` or local `components/**/composables/*` first.
3. If a status-bar modal is lazy-loaded with `defineAsyncComponent + v-if` and relies on `props.show` to trigger requests, the watcher must use `{ immediate: true }`; otherwise the "open on first mount" case skips fetching data.
4. The dynasty, rankings/World Martial Tournament, mortals, sect relations, time, and deceased-avatar modals should all keep regression tests for "initial `show=true` still fetches data".

## 4. Critical Files Index

| File path | Responsibility | Change frequency |
| :--- | :--- | :--- |
| `web/src/composables/useAppShell.ts` | Core of the app shell state machine. Manages `scene + overlay`, menu context, and splash/game scene switching. | High |
| `web/src/composables/useSystemMenuFlow.ts` | System menu flow layer. Owns tabs, closability, menu context, and the LLM startup check. | High |
| `web/src/App.vue` | Root assembly layer. Renders the underlying page by `scene` only and mounts the menu/loading overlays. | High |
| `web/src/components/SystemMenuShell.vue` | Menu shell component. Owns the modal/header/tab bar, not the tab content. | Medium |
| `web/src/components/settings/SettingsPanel.vue` | Reusable settings content panel. Owns language, volume, autosave, and similar settings. | Medium |
| `web/src/stores/world.ts` | World-level orchestration and time/phenomenon state. | High |
| `web/src/stores/socketMessageRouter.ts` | Socket business message routing hub. Change this first when adding message types. | High |
| `web/src/components/layout/StatusBarPanels.vue` | Status-bar modal assembly layer. Owns lazy loading and open state, not modal data logic. | Medium |
| `web/src/components/game/panels/EventPanel.vue` | Event log view. Data, filtering, and scrolling logic are in `useEventPanel.ts`. | Medium |
| `web/src/composables/useEventPanel.ts` | Event log panel logic. Owns loading, filtering, scrolling, and visibility. | Medium |
| `web/src/components/game/MapLayer.vue` | Map rendering template shell. Owns the mount container and event forwarding. | Medium |
| `web/src/components/game/composables/useMapLayerRenderer.ts` | Core of map Pixi rendering: textures, sprite lifecycle, ticker, labels, and interaction. | Medium |
| `web/src/composables/useLoadingOverlayState.ts` | Loading overlay display state and derived progress text. | Low |
| `web/src/composables/useGameControl.ts` | Game control layer. Owns pause/resume, ESC input, and pausing in step with menu visibility. | Low |
| `web/src/api/modules/*.ts` + `web/src/api/mappers/*.ts` | API requests and DTO normalization. Add a mapper alongside new endpoints. | Medium |
| `web/src/locales/en-US/*.json` | UI text. Must be updated whenever UI wording changes. | High |

---

**Vibe coding tips**:
*   When changing UI, check `stores/ui.ts`, `useAppShell.ts`, `useSystemMenuFlow.ts`, and the relevant panel component first.
*   When changing data logic, start with `stores/world.ts` and its sub-stores.
*   For Pixi rendering issues, focus on `web/src/components/game/composables/useMapLayerRenderer.ts` and `components/game/composables/useTextures.ts`.
*   If a status-bar modal is empty on first open, check whether it is a first mount via `defineAsyncComponent + v-if` and whether the `props.show` watcher has `{ immediate: true }`.
*   Change socket message logic in `stores/socketMessageRouter.ts`; don't scatter message branches across components.
*   When adding backend response fields, consolidate conversion in `types/api.ts` and `api/mappers/`.
*   When changing map text display, check `web/src/components/game/utils/mapLabels.ts` and `web/src/utils/mapStyles.ts` first; don't pile up random offsets or hardcoded locale branches in `MapLayer.vue`.
*   When changing settings, edit `SettingsPanel.vue`; unless it is menu container behavior, don't put settings UI back into `SystemMenu.vue`.

## 5. Desktop Distribution

There are currently two desktop/release paths, which should be understood separately.

1.  **GitHub / source browser mode**:
    *   `start()` in `src/server/main.py` computes the target URL first, then decides from configuration whether to call `webbrowser.open()` to open the system default browser.
    *   The `uvicorn` backend keeps running in the current Python process.
    *   In development mode, the frontend is still started as a child process with `npm run dev`, so HMR keeps working.

2.  **Desktop Electron mode**:
    *   `desktop/` is a standalone Electron host project.
    *   The Electron main process starts the packaged backend, waits for `/api/health`, then loads the local HTTP UI.
    *   The general desktop packaging entry is `tools/package/pack_desktop.ps1`; the final content root is written to `tmp/desktop_content_root.txt`.
    *   Electron mode controls backend behavior through environment variables, e.g. disabling automatic browser launch.

3.  **Packaging and release**:
    *   The regular open-source package can still use the local server + system browser experience.
    *   Store releases are all based on the Electron desktop content root; per-platform publish scripts are maintained in layers under `tools/package/<platform>/publish.ps1`.
    *   The Steam publish entry is `tools/package/publish_steam.ps1` and the Epic entry is `tools/package/publish_epic.ps1`; a real upload requires passing `-RequireUpload` explicitly.
    *   The old PyInstaller Steam packaging scripts have been removed; Steam only reuses the general desktop build output as a platform publishing layer.

4.  **Canvas sizing principle**:
    *   **Do not** use `useWindowSize()` (which depends on `window.resize`) to drive the PIXI canvas size.
    *   **Use** `useElementSize(container)` (based on `ResizeObserver`) so the canvas size follows the container directly.
    *   Current implementation (`GameCanvas.vue`): `width/height` and the `Viewport`'s `screenWidth/screenHeight` all come straight from `useElementSize`, the same source as `resizeTo="container"`, so there is no conflict.

## 6. Startup Rendering Guard and Scene Boundaries

To avoid flicker when the frontend first takes over the page, and to avoid accidentally rendering the game shell before a game has started, the app keeps a startup rendering guard and scene boundaries.

1.  **`boot` anti-flicker design**:
    *   While the page has just loaded and settings have not finished hydrating, or the first backend `initStatus` response has not arrived, the root scene stays `boot` and shows a plain black shell.
2.  **Hard boundary between `splash` and `game`**:
    *   When the backend reports `idle` and the frontend is not initialized, the scene enters `splash`.
    *   The scene may enter `game` only after both frontend and backend are ready and the frontend has `gameInitialized === true`.
    *   Opening overlays such as the menu, settings, or about page must not implicitly switch the underlying scene to `game`.
3.  **`initializing` transition scene**:
    *   After the player starts a new game or loads a save, and until frontend loading truly completes, the root enters `initializing`; the black shell stays underneath and `LoadingOverlay` communicates progress to the user.

## 7. Preloading Strategy

During game initialization, some backend phases (such as calling the LLM to generate avatar backstories) take several to a dozen-plus seconds. To put that time to use, and to avoid the jarring "stuck at 100%" moment where the frontend still has to load images after the backend reaches 100%, the frontend implements an asynchronous preloading mechanism.

1. **Phase monitoring**: through `useGameInit`, the frontend keeps polling `/api/v1/query/runtime/status`, reading not only the overall progress but also the current `phase_name`.
2. **Constant mapping (`GAME_PHASES`)**: `constants/game.ts` maintains the minimum backend phase at which each resource can start loading:
   *   `MAP_READY`: once the backend has placed sects or generated avatars, the map data is ready.
   *   `AVATAR_READY`: once the backend enters the LLM check or initial event generation, all avatars' basic info (including portrait IDs) is final.
   *   `TEXTURES_READY`: in step with avatar readiness; at this point all relevant avatar portraits and tile textures can be fetched and PixiJS `Assets` preloading can run.
3. **Using the wait for free**: while polling, as soon as the backend enters the `TEXTURES_READY` phase (usually corresponding to the backend's long blocking LLM operations), `useGameInit` triggers `loadBaseTextures()` without blocking.
4. **Seamless entry**: thanks to PixiJS `Assets`' built-in cache, when the backend finally reports `ready` and control returns to the frontend's `initializeGame()`, the second `await loadBaseTextures()` hits the cache instantly (near 0 ms), so the view appears seamlessly once loading ends.

## 8. Error Policy & Performance Baseline

### 8.1 Error handling
*   Always use `logError/logWarn` from `utils/appError.ts` to record context; don't scatter raw `console.error/warn` calls.
*   User-visible notices go through the single `message` outlet to avoid duplicate notices and inconsistent styling.

### 8.2 Performance baseline metrics (lightweight)
*   `useGameInit.ts`:
    *   `initializeDurationMs`: duration of one initialization.
    *   `lastPollDurationMs`: duration of the most recent status poll.
*   `stores/event.ts`:
    *   `lastMergeDurationMs`: tick event merge duration.
    *   `lastLoadDurationMs`: historical event load duration.

These metrics are for regression comparison, not for user-visible display.

## 9. UI Icon Guidelines

The frontend has converged on a single UI icon approach. New system-level icons should reuse it rather than mixing icons from different sources.

1. **Single source**:
   * Use `Lucide` outline SVGs throughout.
   * Local icon directory: `web/src/assets/icons/ui/lucide/`
   * Source and current mapping notes: `web/src/assets/icons/ui/lucide/README.md`
2. **Scope**:
   * Top floating control buttons
   * System menu tabs
   * Top status-bar entries
   * Settings, saves, about/other, and other system-level panels
3. **Style constraints**:
   * Don't mix multiple icon families in the same UI area.
   * Default to outline style; don't mix with filled, emoji, or colorful skeuomorphic icons.
   * Icons are only a recognition aid and do not replace text labels; key entry points must keep their text.
4. **Technical form**:
   * Prefer module imports via `import xxxIcon from '@/assets/icons/ui/lucide/*.svg'`.
   * Prefer rendering with `currentColor + mask-image` so hover / active / disabled states match the text color.
   * Don't inline hand-written SVGs for similar buttons unless the existing icon library genuinely lacks a suitable asset.
5. **Incremental maintenance**:
   * Before adding an icon, check whether `web/src/assets/icons/ui/lucide/` already has a reusable one.
   * If a new icon must be downloaded, add it to the same directory and update that directory's README with its source and suggested mapping.
