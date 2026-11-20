# AGENTS.md

This is the repository-level working guide for agents. It consolidates the rules, skills, and commands under `.cursor/` so that Codex, Cursor, and other agents can read it directly when they enter the repository.

## 1. How Codex reads AGENTS.md (checked against the official docs)

As of 2026-03-11, Codex resolves the AGENTS instruction chain as follows:

1. File format: `AGENTS.md` is plain Markdown with no required fields.
2. Global layer: Codex checks `~/.codex/AGENTS.override.md` first, then `~/.codex/AGENTS.md`. Only the first non-empty file in this layer is used.
3. Project layer: walking from the project root down to the current working directory, each directory is checked for:
   - `AGENTS.override.md`
   - `AGENTS.md`
   - the fallback file names configured in `project_doc_fallback_filenames`
   At most one file is included per directory.
4. Merge order: files are concatenated from the root down to the current directory; the closer a file is to the current directory, the higher its priority (it is appended later and overrides earlier meaning).
5. Empty files are ignored.
6. There is a size cap (default `project_doc_max_bytes = 32 KiB`); once it is exceeded, no further instructions are appended.
7. Conflict priority: system/developer/user messages > AGENTS.md; a deeper directory's AGENTS file > a shallower one.

## 2. Scope of this file

1. Scope: the repository root and all of its subdirectories.
2. There is currently no deeper `AGENTS.md` or `AGENTS.override.md`, so this file is the project-level primary guide.
3. Instruction sources: `.cursor/rules/*.mdc`, `.cursor/skills/*/SKILL.md`, `.cursor/commands/*.md`.
4. Supplementary design docs: `docs/specs/*.md` record important system designs that have already landed. For the config system see `docs/specs/config-architecture.md`; for the map system see `docs/specs/region-first-map-system.md`; for the story event system see `docs/specs/story-event-system.md`; for roleplay mode see `docs/specs/avatar-roleplay-mode.md` and `docs/specs/single-choice-unified-framework.md`; for cultivation realm aliases see `docs/specs/cultivation-alias-system.md`.
5. The external control API server has gone through a round of modularization. Prefer the "server module map after landing" section in `docs/specs/external-control-api.md`, and do not pile query builders, command handlers, initialization phases, or host wiring back into `src/server/main.py`.
6. Language: the repository and the game are English-only. `en-US` is the single locale and the source of truth (`static/locales/registry.json`). Write code, comments, docs, specs, commit messages, and user-facing strings in English.

## 3. `.cursor/rules` summary

### 3.1 Rule index

| Rule file | Scope (globs) | Key constraints |
|---|---|---|
| `.cursor/rules/action-development.mdc` | `src/classes/action/**/*.py`, `src/classes/mutual_action/**/*.py` | New actions must provide `ACTION_NAME_ID/DESC_ID/REQUIREMENTS_ID/EMOJI/PARAMS`, lifecycle methods, the registration decorator, the `__init__.py` export, and tests; parameters chosen from world state must declare `PARAM_OPTION_SOURCES`, with tests proving each `param_options.value` is executable. |
| `.cursor/rules/config-architecture.mdc` | `src/config/**/*.py`, `src/server/**/*.py`, `src/utils/config.py`, `src/utils/llm/**/*.py`, `src/sim/save/**/*.py`, `src/sim/load/**/*.py`, `web/src/stores/setting.ts`, `web/src/api/modules/system.ts`, `web/src/api/modules/llm.ts`, `web/src/components/game/panels/system/**/*.vue`, `web/src/App.vue` | Config is split into read-only release config, `settings.json/secrets.json` app settings, and the per-run `RunConfig` snapshot; user data always goes through the data root; the frontend settings source of truth is `/api/settings`; LLM keys are never sent back to the frontend; saves must store `run_config`. |
| `.cursor/rules/development-phase.mdc` | `*.py`, `*.vue`, `*.ts`, `*.tsx`, `*.json` | Development phase: forward/backward compatibility is **not required in principle**; clarity of new code comes first. Compatibility may be added only when it is **free** (e.g. a one-line `.get` that does not distort structure); never pay for it with dual paths, extra branches, or a less readable main path. |
| `.cursor/rules/docker-persistence.mdc` | `docker-compose.yml`, `deploy/Dockerfile.backend`, `deploy/Dockerfile.frontend`, `deploy/nginx.conf`, `src/config/data_paths.py`, `src/server/main.py`, `src/utils/config.py`, `tests/test_docker_build_contract.py`, `tests/test_data_paths_runtime_contract.py`, `tests/test_docker_runtime_smoke.py`, `tests/test_nginx_proxy_contract.py`, `tests/test_server_binding.py`, `README.md` | Docker always persists through `CWS_DATA_DIR`; containers must not exit because nobody is connected; the frontend health check must reflect that the backend proxy chain works; production images install runtime dependencies only; related changes must add contract/smoke tests and update the docs. |
| `.cursor/rules/external-control-api.mdc` | `src/server/**/*.py`, `web/src/api/**/*.ts`, `web/src/stores/**/*.ts`, `tests/test_api_*.py`, `tests/test_websocket_handlers.py`, `tests/test_init_status_api.py`, `tests/test_game_init_integration.py`, `docs/specs/external-control-api.md`, `README.md` | The external control API is designed from the perspective of external agents / Claw; breaking compatibility is allowed, runtime/service/API layering comes first; stable endpoints are split into query/command with a unified response format; all mutations must be serialized, and the pattern of `main.py` writing directly to `game_instance` must not spread. |
| `.cursor/rules/event-system.mdc` | `src/classes/event.py`, `src/classes/event_storage.py`, `src/systems/**/*.py` | Keep the `is_major/is_story` semantics clear, fill `related_avatars` accurately, let the simulator persist events centrally, and paginate queries. |
| `.cursor/rules/frontend-sound.mdc` | `web/src/**/*.vue|ts|tsx` | Standard buttons get sound effects automatically; use `v-sound` for special sounds and `data-no-sound` to mute; programmatic `useAudio` playback only for special cases. |
| `.cursor/rules/frontend-typing-error.mdc` | `web/src/**/*.vue|ts|tsx` | Update DTOs in `types/api.ts` first, keep mapping logic in `api/mappers`, avoid spreading `any`, route errors through `appError`, dispatch socket messages in `socketMessageRouter`; config-style selectors should use localized backend DTOs instead of hardcoded user-visible options in the frontend; UI strings live under `web/src/locales/en-US/`; short-slot i18n keys get short labels or `*_short`, with full explanations in `*_desc/help`. |
| `.cursor/rules/frontend.mdc` | `web/src/**/*.{vue,ts,js}` | Backend-driven architecture, clear store responsibilities, root UI uses `scene + overlay`, the boot state machine lives in `useAppShell`, the system menu is split into shell/content/flow layers, layered sockets, complex panel logic moves into composables, lazily loaded dialogs need an `immediate` `show` watcher, `shallowRef`/long-list performance strategies, container sizes always via `useElementSize()`; frontend `public` assets must never use hardcoded site-root absolute paths and must go through a `BASE_URL` helper or `src/assets` module imports. |
| `.cursor/rules/i18n.mdc` | `*.py`, `*.vue`, `*.json`, `*.po` | `en-US` is the single source-of-truth locale (`static/locales/registry.json`); edit backend strings in `static/locales/en-US/modules/*.po` and `game_configs_modules/*.po` (`LC_MESSAGES/*.po` are merged build products), then run `python tools/i18n/build_mo.py`; frontend strings live in `web/src/locales/en-US/`; `msgid` is English source text or a stable key; race/yao effect labels are a cross-stack DTO contract; runtime/LLM text goes through `static/locales/en-US/templates/*.txt` or translation keys; short slots stay concise; a future language starts by registering it in the registry. |
| `.cursor/rules/llm-integration.mdc` | `src/utils/llm/**/*.py`, `src/**/*.py` | Always go through `src.utils.llm.client`, choose `LLMMode` by scenario, leave retries to the lower layer, catch `LLMError/ParseError` and degrade gracefully. |
| `.cursor/rules/map-system.mdc` | `src/run/map_*.py`, `src/run/load_map.py`, `src/classes/environment/**/*.py`, `src/server/services/game_queries.py`, `static/game_configs/maps/**/*.json`, `static/game_configs/region_tile.csv`, `tools/map_presets/**/*.py`, `tools/map_creator/**/*.py`, `tests/test_map_presets.py`, `tests/test_save_load_map_snapshot.py`, `web/src/components/game/**/*.vue`, `web/src/types/**/*.ts` | Official maps use `region_rows` in `map.json` as the only semantic matrix; tiles are derived from `region_tile.csv` and `wilderness_tile`; one region has exactly one tile image; `-1` is wilderness and not clickable; map-specific names/descriptions go through `region_overrides` and are preserved by saves and map tools; run map validation/preview/related tests after editing a map. |
| `.cursor/rules/python-registry.mdc` | `src/classes/**/*.py` | New classes that use a registration decorator must be imported in the matching `__init__.py`, otherwise registration does not happen; add registration tests too. |
| `.cursor/rules/roleplay-mode.mdc` | `src/server/**/*.py`, `src/systems/single_choice/**/*.py`, `src/classes/mutual_action/**/*.py`, `src/sim/**/*.py`, `web/src/components/game/**/*.vue`, `web/src/stores/roleplay.ts`, `web/src/api/modules/avatar.ts`, `web/src/types/api.ts`, `tests/test_public_api_v1.py`, `tests/test_single_choice.py`, `tests/test_action_social.py`, `tests/test_mutual_actions.py`, `web/src/__tests__/components/game/**/*.test.ts`, `docs/specs/avatar-roleplay-mode.md`, `docs/specs/single-choice-unified-framework.md` | The default is still the god view; roleplay is a single-avatar runtime takeover; pause only at decision boundaries; phase 2 refactors `single_choice` into a unified finite-decision framework first; phase 3 dialogue must be attached to the `Conversation` action, and raw chat logs are never saved. |
| `.cursor/rules/save-load-serialization.mdc` | `src/sim/save/**/*.py`, `src/sim/load/**/*.py`, `src/classes/**/*.py` | Saves contain only JSON primitive types and store cross-object references as IDs; complex class serialization lives in mixins; the load side favors a clear current model, and accommodating old saves follows `development-phase.mdc` (a free `.get` is fine; no paid compatibility, no dual paths). |
| `.cursor/rules/sect-system.mdc` | `src/classes/core/sect.py`, `src/classes/core/world.py`, `src/classes/sect_decider.py`, `src/sim/managers/sect_manager.py`, `src/systems/sect_decision_context.py`, `src/classes/ranking.py`, `src/server/**/*.py`, `src/systems/sect_relations.py`, `web/src/**/*.{ts,vue}` | Unified sect domain model and API layering; `SectContext` manages the sects enabled in a run; power snapshots are computed centrally by `SectManager`; `SectDecider` produces each sect's yearly thinking every January and writes it back to `yearly_thinking`, exposed to the frontend via detail; the frontend detail chain must go through strongly typed DTOs + mappers. |
| `.cursor/rules/simulator-logic.mdc` | `src/sim/simulator.py`, `src/sim/**/*.py` | Phases are split into standalone functions in `simulator_engine/phases`, and `step()` only orchestrates; shared state goes through `SimulationStepContext`; new phases require re-indexing; LLM/heavy phases are async; maintain `living_avatars` after death settlement; wrap up through `finalizer.finalize_step()`. |
| `.cursor/rules/story-event-system.mdc` | `src/classes/story_event_service.py`, `src/classes/action/**/*.py`, `src/classes/mutual_action/**/*.py`, `src/classes/gathering/**/*.py`, `src/systems/battle.py`, `src/systems/fortune.py`, `static/config.yml`, `tests/**/*.py` | Story events always go through `StoryEventService`; generate the base result event first, then try to append a story; non-gathering stories are controlled by `StoryEventKind + game.story.probabilities`, while `gathering` is fixed at 100%; all LLM-expanded story text is marked `is_story=True`. |
| `.cursor/rules/testing.mdc` | `tests/**/*.py` | Reuse `conftest.py` fixtures (`dummy_avatar`/`mock_llm_managers`, etc.), mark async tests with `@pytest.mark.asyncio`, build test paths for the current platform instead of hardcoding Windows/Linux absolute paths, avoid over-engineering; use `pytest -n 8` for quick vibe-coding regression runs. |
| `.cursor/rules/vue-performance.mdc` | `web/src/**/*.vue|ts|tsx` | Large objects must use `shallowRef`, long lists use pagination or virtual scrolling, expensive derivations use `computed`, and keep before/after performance baselines when refactoring. |

### 3.2 Hard constraints to follow first

1. After adding a registrable module, update the corresponding `__init__.py`.
2. Action system changes must come with tests, especially for the `can_possibly_start` branches.
3. Action parameters chosen from the current world state (avatars, regions, items, realms, directions, etc.) must declare `PARAM_OPTION_SOURCES`; each `value` in `param_options` must be a value the action's execution layer can actually resolve, with matching tests.
4. Large frontend objects and Pixi instances must not be wrapped in deep reactive proxies.
5. i18n: `en-US` is the only locale and the source of truth. Add or edit user-facing strings only in the en-US sources; `static/locales/registry.json` is the single source of truth for the locale list, and Python i18n tools, validation, and any future new-language flow read it instead of hardcoding locale codes.
6. Saves and persistence: the technical shape in `save-load-serialization.mdc` must still be followed; whether to accommodate old saves is decided by `.cursor/rules/development-phase.mdc` — **clarity first**, compatibility only when it is **free**, never adding real burden for compatibility.
7. The i18n source files are `static/locales/en-US/modules/*.po` and `static/locales/en-US/game_configs_modules/*.po`; `static/locales/en-US/LC_MESSAGES/messages.po` and `static/locales/en-US/LC_MESSAGES/game_configs.po` are merged build products. Do not edit them directly; run `python tools/i18n/build_mo.py` after editing the sources.
8. In `.po` files, `msgid` uses English source text or a stable key (e.g. `feature_xxx_label`).
9. Short slots must stay concise without losing meaning: `title`, `label`, `tab`, `button`, `badge`, `status`, `*_short`, menu items, status bar entries, card titles, etc. get short natural wording; full explanations go into `*_desc`, tooltips, help, or body keys, adding separate short/long keys when needed instead of making one long string serve both a narrow button and a dialog description.
10. Races, yao action/effect keys, race options in avatar creation, and race detail display form a frontend/backend i18n contract: the backend provides localized structured DTOs, and the frontend must not hardcode user-visible race labels (Human/Fox/Wolf/Bird/Snake/Turtle, etc.).
11. LLM/runtime-generated text (e.g. `backstory`, `thinking`, goals) is separate from UI translation; new generated-text constraints or prompt fragments go through locale templates (`static/locales/en-US/templates/`) or translation keys, never hardcoded final natural-language text in Python logic.
12. Rule-based simulation test mode is the per-run `RunConfig.test_mode` semantic and must be saved with the save file; test mode must never call a real LLM or run connectivity checks. Every new LLM task must register a parseable rule fallback in `src/utils/llm/test_mode_fallbacks.py`, or be explicitly and controllably rejected at the domain entry point; unknown tasks must fail closed and never fall back to a real provider.
13. User settings must no longer be written to `static/local_config.yml`; the real source of truth is `settings.json/secrets.json` in the user data directory, and per-run parameters must go through `RunConfig` and be saved with the save file.
14. Story events are always generated through `src/classes/story_event_service.py`; business code first produces the factual event, then decides whether to append a story event.
15. `gathering` stories are fixed at `100%`, and all LLM-expanded story text uses `is_story=True`; do not mix in `is_major=True` as a story text marker.
16. Frontend bundled static assets (`web/public/*`) must not use hardcoded root paths such as `/icons/...`, `/sfx/...`, `/bgm/...`; fixed images go into `web/src/assets/*` as module imports, and runtime paths are always generated through an `import.meta.env.BASE_URL` helper.
17. Frontend system-level UI icons currently use `Lucide` outline SVGs, stored in `web/src/assets/icons/ui/lucide/`; reuse that directory for new icons and keep a single icon family, never mixing styles; keep text on key entry points, prefer rendering with `currentColor + mask-image`; see `docs/frontend.md` and the `README.md` in that directory.
18. The map system's official source of truth is `static/game_configs/maps/<id>/map.json`, with `region_rows` as the only semantic matrix; do not restore `tile_map.csv/region_map.csv` as a parallel main path; one region binds exactly one tile image, `-1` is wilderness and not clickable, map-specific names/descriptions must go through `region_overrides` and be preserved by map tools and saves; after editing an official map run at least `python tools/map_presets/validate_presets.py`.
19. Root-level frontend page orchestration must use `scene + overlay` semantics: `SystemMenu` and `LoadingOverlay` must not infer the current underlying page from side effects such as closing the Splash; the main game UI may render only when `scene === 'game'`.
20. Status bar and system navigation colors must separate the "module base color" from the "state override color": the base color expresses which section an item belongs to, and the state color is used only for dynamic information such as active/available/rarity; avoid making yellow-orange carry several meanings at once.
21. In Docker / Compose deployments the container lifecycle is controlled by the process manager; containers must not exit automatically because of desktop-style logic such as WebSocket disconnects or no connected clients.
22. Docker health checks must reflect real availability as closely as possible; in particular the frontend proxy chain must not check only the static index page; when depending on the backend, `depends_on` should wait for `service_healthy`.
23. Docker production images install only runtime dependencies; do not put `pytest` or other test dependencies into runtime images, and do not depend again on old runtime directories such as `/app/assets/saves` or `/app/logs`.
24. When changing Docker configuration, images, proxies, or persistence semantics, update the contract/smoke tests and the deployment instructions in `README.md` at the same time.
25. Stable contracts of the external control API serve external agent / Claw integrations first; when adding a public endpoint, decide first whether it is a `query` or a `command`, and land it in the runtime/service layers and the stable `/api/v1/*` namespace.
26. All APIs that modify world state must be serialized through the unified mutation entry point to avoid writing the world concurrently with `Simulator.step()`; the pattern of route handlers mutating `game_instance` directly must not spread.
27. If external control API query builders / command handlers / services depend on functions or config that tests patch, that config reloads, or that will be split further, prefer `get_*` getters or read them at call time; do not bind dependencies at module initialization.
28. Config that affects runtime semantics must be read at call time, especially the save directory, data root, and config derived from settings/secrets; do not assume that a module-level `CONFIG` is always the latest object.
29. When writing or changing tests, never hardcode absolute paths that only hold on one operating system; for path assertions use `tmp_path`, `pathlib.Path`, `os.path.join()`, etc. so results match on local Windows and GitHub Actions Linux.
30. Roleplay mode is "single-avatar takeover within the god view" by default, not a separate global mode; do not split "personal mode" and "god mode" into two systems.
31. Roleplay state, `pending_request`, `conversation_session`, and choice continuations all belong to the runtime; they must never be written to saves and must be cleared explicitly after `load/reinit/reset/start`.
32. Roleplay may pause only at decision boundaries, never in the middle of an action chain; phase 2 finite choices must go through the unified choice resolver / continuation, instead of scattering `if roleplay ... else ...` across business scenarios.
33. Phase 3 free dialogue must be triggered through the `Conversation` action, using a one-sided takeover where the player types for one side and the target avatar replies via the LLM; raw chat logs do not enter the long-term event stream and land only as a summary.
34. Business state, data loading, derived fields, navigation, submission, timers, and Pixi lifecycles of large frontend panels/dialogs/detail pages belong in existing composables; do not pile this logic back into `.vue` presentational components.
35. For dialogs lazy-loaded with `defineAsyncComponent` + `v-if` whose requests depend on `props.show`, the watcher must use `{ immediate: true }`, with a test proving that an initial mount with `show=true` also triggers the request, so status bar entries such as Dynasty or the World Martial Tournament are never empty on first open.

## 4. `.cursor/skills` summary

| Skill | Purpose | Key flow |
|---|---|---|
| `external-control-api` | Plan or implement the stable control API for external agents / Claw | Map existing queries/commands and the `main.py`/`game_instance` coupling -> settle runtime/service/API layering and the v1 namespace -> do mutation serialization and stable DTOs/error codes first -> finally sync `README.md` / `docs/specs/external-control-api.md` / `AGENTS.md`. |
| `git-pr` | Create a well-formed PR | Branch from up-to-date `main`, standard commit types, push, then `gh pr create` following the PR template. |
| `desktop-distribution` | Desktop packaging and GitHub/Steam/Epic releases | `pack_*` only builds, `publish_*` builds and publishes; the only desktop store build source is `tools/package/desktop/pack.ps1`, and Steam/Epic only consume its content root; Epic EOS releases default to the Live deployment, Dev validation must pass `-EosEnv dev` explicitly; the default LLM seed lives in the desktop config, platform accounts in each platform's directory. |
| `img-gen-avatar` | Maintain the `tools/img_gen` avatar portrait generation, realm image editing, prompts, and post-processing flow | Two-stage flow: Qi Refinement portraits by text-to-image, later realms edited from the Qi Refinement image; preserve the pixel-art, low-detail, chibi anime style, character identity, pure white background, and yao race traits; never leak `image_api.env`. |
| `i18n-development` | Day-to-day i18n work | `en-US` is the only and source-of-truth locale; maintain entries in the split `.po` sources under `modules/` / `game_configs_modules/`, never edit `LC_MESSAGES/*.po` directly, and always run `build_mo.py` afterwards; frontend strings in `web/src/locales/en-US/`, prompts in `static/locales/en-US/templates/`; adding a language later starts with `static/locales/registry.json`. |
| `grave-poi-death-test` | Verify avatar death and the grave POI with a real simulation | Use an isolated test data directory and trigger death through a normal `Simulator.step()`, never calling `handle_death()` directly; verify the deceased archive, the grave map POI, and that clicking it on the map opens the avatar detail; clean up dedicated processes and temporary resources. |
| `roleplay-mode-implementation` | Plan, implement, or refactor roleplay mode | Check which phase (1/2/3) is affected -> compare against `avatar-roleplay-mode.md` and `single-choice-unified-framework.md` -> keep "single-avatar takeover within the god view, pause only at decision boundaries, runtime never saved" -> then land runtime/API/frontend/tests. |
| `spec-interview` | Produce a spec after a requirements interview | Ask multiple rounds of questions to surface hidden constraints and risks, then write the spec (in English) to `docs/specs/<feature>.md`. |
| `test-validate` | Test execution reference | Backend `pytest`, frontend `npm run test/type-check`, and which tests each change type needs. |

## 5. `.cursor/commands` summary

| Command file | Suggested command | Function |
|---|---|---|
| `.cursor/commands/pack_desktop.md` | `/pack_desktop` | Default desktop Electron packaging: run `powershell ./tools/package/pack_desktop.ps1`, producing `tmp/<tag>_desktop/win-unpacked` and writing `tmp/desktop_content_root.txt`; build only, no store upload. |
| `.cursor/commands/publish_github.md` | `/publish_github` | GitHub Release: run `powershell ./tools/package/publish_github.ps1`, which runs `pack_github.ps1`, `compress.ps1`, and `release.ps1` in order. |
| `.cursor/commands/publish_steam.md` | `/publish_steam` | Steam release: run `powershell ./tools/package/publish_steam.ps1`, reusing the `pack_desktop.ps1` content root, then `steam/publish.ps1`. |
| `.cursor/commands/publish_epic.md` | `/publish_epic` | Epic release: run `powershell ./tools/package/publish_epic.ps1 -RequireEosRuntime`, using the Live EOS deployment by default and reusing the `pack_desktop.ps1` content root, then `epic/publish.ps1`; with `-RequireUpload` it calls BuildPatchTool for a real upload; Dev validation passes `-EosEnv dev` explicitly. |
| `.cursor/commands/sync_contributors.md` | `/sync_contributors` | Sync repository contributors from the GitHub contributors API via `tools/github/sync_contributors.py`, regenerating `CONTRIBUTORS.md` and the README contributors section. |
| `.cursor/commands/sync_roleplay_docs.md` | `/sync_roleplay_docs` | Sync the roleplay rule / skill / spec / AGENTS / tests, checking single-avatar takeover within the god view, pausing at decision boundaries, runtime never saved, choice continuations, and `Conversation` dialogue semantics. |
| `.cursor/commands/update_version.md` | `/update_version` | Create a tag, update the version in `static/config.yml`, and commit. |
| `.cursor/commands/sync_agents.md` | `/sync_agents` | Rescan `.cursor` and update the root `AGENTS.md` (in English). |

## 6. Test and validation commands (from the skills)

1. Full backend test suite: `pytest`
2. Quick vibe-coding regression: `pytest -n 8`
3. Frontend tests: `cd web && npm run test`
4. Frontend type check: `cd web && npm run type-check`
5. Locale checks (en-US completeness/structure):
   - `pytest tests/test_frontend_locales.py`
   - `pytest tests/test_backend_locales.py`
6. Locale registry / missing-entry report: `python tools/i18n/generate_missing_report.py`

## 6.1 Packaging and release quick reference

`pack_*` only builds local artifacts; `publish_*` builds first and then publishes to the matching channel. See `docs/packaging.md` for a short overview.

1. GitHub build: `powershell ./tools/package/pack_github.ps1`
2. Desktop build: `powershell ./tools/package/pack_desktop.ps1`
3. GitHub release: `powershell ./tools/package/publish_github.ps1`
4. Steam release: `powershell ./tools/package/publish_steam.ps1`
5. Epic release: `powershell ./tools/package/publish_epic.ps1 -RequireUpload`
6. Unified entry point and list: `powershell ./tools/package/task.ps1 -List`

## 7. Maintenance conventions

1. After changing `.cursor/rules`, `.cursor/skills`, or `.cursor/commands`, run `/sync_agents` to resync this file.
2. This file is an "aggregated index + enforced constraints" document and does not replace the original files; the originals are authoritative for details.
3. If subdirectory `AGENTS.md` files are introduced later, follow the "closest wins" override strategy and put local rules in that subdirectory.
4. To add a new language in the future, update `static/locales/registry.json` first, then handle directories, scripts, and resource scaffolding (see `docs/i18n-add-locale.md`); do not start with scattered changes to a frontend menu or a single test file.
5. When adjusting story event logic, keep `.cursor/rules/story-event-system.mdc`, `docs/specs/story-event-system.md`, and the summary in this file in sync.
6. When adjusting the map system or official map presets, keep `.cursor/rules/map-system.mdc`, `docs/specs/region-first-map-system.md`, and the summary in this file in sync.

## 8. Original sources

1. `.cursor/rules/*.mdc`
2. `.cursor/skills/*/SKILL.md`
3. `.cursor/commands/*.md`
4. `docs/specs/story-event-system.md`
5. `docs/specs/avatar-roleplay-mode.md`
6. `docs/specs/single-choice-unified-framework.md`
7. `docs/specs/region-first-map-system.md`
