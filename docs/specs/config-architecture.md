# Config Architecture Refactor Notes

This document records the results of the 2026-04 config system refactor and serves as the single design reference for subsequent development.

## Goals

The goal of this refactor was not to stay compatible with the old structure, but to straighten out the config boundaries:

1. `static/config.yml` only keeps the static config built into the release.
2. User settings and sensitive information are managed uniformly by `SettingsService`.
3. New-game parameters are expressed uniformly by `RunConfig` and saved with the save file.
4. Historically deprecated config is removed, with no fallback for old fields.

## Final Layering

### 1. Static Config

Files:

- `static/config.yml`
- `src/utils/config.py`

Responsibilities:

- Version number
- Static resource directories
- Game balance parameters
- World rules and story probabilities
- Default modes per LLM task
- Built-in frontend default presentation parameters

Restrictions:

- Does not hold user preferences
- Does not hold API keys
- Does not hold current-run startup parameters
- Does not hold deployment addresses and ports

### 2. Application Settings

Files:

- `settings.json`
- `secrets.json`
- `src/config/settings_schema.py`
- `src/config/settings_service.py`

Responsibilities:

- UI language
- Volume
- Autosave settings
- LLM profile
- New-game default parameters
- API key

Restrictions:

- Never written back to `static/config.yml`
- The frontend's single source of truth is `/api/settings`

### 3. Current-Run Config

Type:

- `RunConfig`

Responsibilities:

- `content_locale`
- `init_npc_num`
- `sect_num`
- `npc_awakening_rate_per_month`
- `world_lore`

Rules:

1. Generated from the frontend request when starting a new game.
2. The server writes the snapshot into `game_instance["run_config"]`.
3. The world object stores it in `world.run_config_snapshot`.
4. Saves must serialize `run_config`.
5. When loading, this snapshot is restored first instead of falling back to static config.

### 4. Deployment Environment Config

Sources:

- `SERVER_HOST`
- `SERVER_PORT`
- `CWS_DATA_DIR`

Responsibilities:

- Server listen address
- Server port
- User data root directory

Restrictions:

- No longer carried by `static/config.yml`

## Frontend Config Boundaries

The frontend currently has two distinct config chains, which must be understood separately:

### 1. Application Settings Chain

Sources:

- `/api/settings`
- `useSettingStore`

Responsibilities:

- UI language
- Volume
- Autosave
- LLM settings
- New-game default parameters

Constraints:

- `ui.locale` and `new_game_defaults.content_locale` are two independent chains
- The frontend must not automatically overwrite the content language when the UI language is switched
- The `RunConfig` submitted when starting a new game should come directly from the current draft

### 2. Map Render Defaults Chain

Sources:

- `/api/v1/query/world/map -> render_config`
- `useMapStore`

Responsibilities:

- `water_speed`
- `cloud_frequency`

Constraints:

- These parameters represent static map presentation defaults and are not user settings
- Naming uniformly uses `render_config` / `renderConfig` / `MapRenderConfigDTO`
- Overly broad names like `config` / `frontendConfig` are no longer used

## Current Static Config Structure

`static/config.yml` currently uses the following top-level structure:

- `meta`
- `resources`
- `llm`
- `ai`
- `world`
- `sect`
- `avatar`
- `social`
- `nickname`
- `save`
- `frontend_defaults`
- `df`
- `play`

Of these:

- `resources` only describes the static resource root directory
- `world` only describes world rules and no longer contains new-game defaults
- `frontend_defaults` represents built-in frontend default presentation, not user settings

## Removed Deprecated Config

The following config has been completely removed from static config:

- `system.language`
- `system.host`
- `system.port`
- `paths.saves`
- `ai.max_concurrent_requests`
- Leftover old `templates/game_configs` paths kept as comments

These fields no longer have compatibility aliases or fallback logic.

## Core Design Constraints

### 1. `CONFIG` Is Not a Universal Source of Truth

`src.utils.config.CONFIG` now only represents static config and the resource paths derived from it at runtime.

Forbidden:

- Reading user settings from `CONFIG`
- Reading current-run startup parameters from `CONFIG`
- Reading host/port from `CONFIG`

### 2. `RunConfig` Is the Only Source of Truth for New-Game Parameters

The server's `get_runtime_run_config()` is only allowed to:

1. Return the currently running `game_instance["run_config"]`
2. Otherwise return `SettingsService.get_default_run_config()`

Falling back to reading new-game parameters from `CONFIG.world` is forbidden.

### 3. The User Data Directory Is Determined Uniformly by `data_paths`

The runtime `CONFIG.paths.saves` is only a derived result injected by `data_paths`.

It is not a static config field and may not be redefined in `static/config.yml`.

### 4. Language Resource Paths Must Be Switched Explicitly

The responsibility of `update_paths_for_language()` is "switch the static resource paths for a given language",
not "guess the current user language from static config".

Therefore default language selection belongs to the settings / runtime layer, not the static config layer.

## Placement Rules for New Config

Before adding a field, first determine which layer it belongs to:

1. If it ships with the release and is mainly used for balance or static rules, put it in `static/config.yml`.
2. If it is a user preference that can be changed on the settings page, put it in `settings.json`.
3. If it is determined only at the start of this run and must be saved with the save file, put it in `RunConfig`.
4. If it relates to the deployment environment, put it in an environment variable.

If a field seems to belong in two layers at once, it usually means the responsibility split is wrong and it should be remodeled first.
