# I18n Rollout Spec

## 1. Background and Goals

The game is English-only. `static/locales/registry.json` defines `en-US` as the single locale: it is the default locale, the fallback locale, the schema locale, and the source of truth. The former `zh-CN`, `zh-TW`, `ja-JP`, `vi-VN` and `fr-FR` locales have been removed.

Because the project was forked from a Chinese-first codebase, the remaining i18n work is not about adding languages but about making the `en-US` locale complete and keeping all user-visible text flowing through the i18n sources:

1. Every feature must be fully usable in `en-US`.
2. No user-visible text may remain hardcoded in Chinese (or any other language) outside the i18n sources.
3. Locale tests are part of regular validation.

Currently enabled locale:

1. `en-US`

The goal of this spec is to define:

1. Where the i18n sources of truth live in the repository.
2. The work packages needed to complete the rollout.
3. The recommended implementation order.
4. Required tests and manual acceptance checks.

## 2. Scope

This i18n rollout covers:

1. Frontend UI copy.
2. Backend runtime text.
3. Dynamic events and formatted text.
4. LLM prompt / template text.
5. Game configuration text.
6. Runtime fallback behavior.

Out of scope:

1. Reworking the mechanism for adding new languages.
2. Turning global translation quality review into a platform.
3. Integrating third-party automatic translation services.

## 3. I18n Sources of Truth in the Project

### 3.1 Locale Registry

Single source of truth:

`static/locales/registry.json`

Requirements:

1. All tools, tests and fill-in scripts read this file first.
2. New scripts must not hardcode a language list.

### 3.2 Day-to-Day Source Files

The translation sources shared by backend and frontend are mainly:

1. `static/locales/en-US/modules/*.po`
2. `static/locales/en-US/game_configs_modules/*.po`
3. `static/locales/en-US/templates/*.txt`
4. `static/locales/en-US/game_configs/*.csv`

Notes:

1. `modules/*.po` holds regular runtime text, UI text and dynamically formatted text.
2. `game_configs_modules/*.po` holds configuration text such as materials, regions, techniques and sects.
3. `templates/*.txt` holds LLM prompt templates.
4. `game_configs/*.csv` holds configuration data such as names.

### 3.3 Build Artifacts

The following files are build artifacts and must not be used as day-to-day editing entry points:

1. `static/locales/en-US/LC_MESSAGES/messages.po`
2. `static/locales/en-US/LC_MESSAGES/game_configs.po`
3. `static/locales/en-US/LC_MESSAGES/*.mo`

After modifying source files, always run:

`python tools/i18n/build_mo.py`

## 4. Current State and Main Gaps

The repository already has a complete i18n infrastructure:

1. The registry `registry.json`
2. The locale directory skeleton
3. A missing-entry report script
4. `.po` merge and `.mo` build scripts
5. Locale tests

The main gap is not the framework but "recently added features whose `en-US` text is incomplete or still Chinese".

Key risk areas:

1. Template files under `templates/*.txt` that are missing or still contain Chinese.
2. New features whose `modules/*.po` entries are missing or still carry Chinese `msgstr` values.
3. Runtime fallbacks or hardcoded Chinese copy in the frontend.
4. Game configuration text that was added without being re-extracted or translated.

Recently added templates that need particular attention:

1. `roleplay_conversation_turn.txt`
2. `roleplay_conversation_summary.txt`
3. `relation_delta.txt`
4. `random_minor_event_pair.txt`
5. `random_minor_event_solo.txt`

## 5. Work Packages

### 5.1 Work Package A: Gap Inventory

Goal: produce a full list of missing entries for the repository.

Steps:

1. Run `python tools/i18n/generate_missing_report.py`
2. Read the missing-entry report produced by the command
3. Break the gaps down by file type and feature module

Deliverables:

1. An up-to-date missing-entry report
2. A prioritized fill-in list

### 5.2 Work Package B: Complete the Templates

Goal: ensure `en-US` has a complete set of LLM prompt templates.

Scope:

1. `static/locales/en-US/templates/*.txt`

Requirements:

1. Add any missing template files.
2. Keep the prompt structure semantically consistent; do not translate only selected fields.
3. If a template has recently been split into new files, follow the split rather than keeping the old single-file semantics.

Key modules:

1. roleplay
2. single choice
3. conversation
4. relation / story / random event
5. sect-related thinker / decider

### 5.3 Work Package C: Complete modules/*.po

Goal: complete regular runtime text and frontend/backend feature text.

Scope:

1. `static/locales/en-US/modules/*.po`

Requirements:

1. Fill every missing entry in `en-US/modules`.
2. Do not edit `LC_MESSAGES/messages.po` directly.
3. `msgid` must stay an English source string or a stable key.
4. Dynamic format strings must keep their placeholders complete and consistent.

Suggested priority:

1. `ui.po`
2. `labels.po`
3. `single_choice.po`
4. `mutual_action.po`
5. `decision_description.po`
6. `event_content.po`
7. Other system modules

### 5.4 Work Package D: Complete game_configs_modules/*.po

Goal: complete world configuration text.

Scope:

1. `static/locales/en-US/game_configs_modules/*.po`

Includes but is not limited to:

1. Regions
2. Sects
3. Techniques
4. Spirit roots
5. Materials
6. Weapons
7. Elixirs
8. Minor event configuration text

Requirements:

1. When adding configuration entries, update the CSV / config source first, then extract and translate.
2. Do not complete only UI copy while ignoring in-game content text.

### 5.5 Work Package E: Complete Frontend Runtime Copy

Goal: clean up hardcoded frontend text and fallback gaps.

Scope:

1. `web/src/**/*.vue`
2. `web/src/**/*.ts`

Key checks:

1. Default store error messages
2. API error fallback messages
3. Runtime status hints
4. Empty-state copy
5. Overlay / dock / panel / system menu copy

Requirements:

1. New user-visible copy must go through frontend i18n.
2. Hardcoded copy must not be relied on as a long-term solution.
3. If the system menu keeps a language entry, it must keep the English `Language` hint.

### 5.6 Work Package F: Complete Backend Runtime Copy

Goal: clean up hardcoded user-visible text on the Python side outside of `t()`.

Scope:

1. `src/**/*.py`

Key checks:

1. `HTTPException.detail`
2. Runtime fallback copy
3. Query / command error messages
4. Status text returned directly to the frontend by new features
5. roleplay / single choice / conversation prompts

Requirements:

1. User-facing strings must go through the i18n sources.
2. Raw exception messages must not be passed straight through to the final UI.

### 5.7 Work Package G: Config Extraction and Build

Goal: keep translation sources and build artifacts consistent.

Steps:

1. If CSVs changed, run `python tools/i18n/extract_csv.py` first
2. Edit `modules/*.po` / `game_configs_modules/*.po`
3. Run `python tools/i18n/build_mo.py`

Requirements:

1. `.po` files must be UTF-8 without BOM.
2. Do not append to `.po` files via PowerShell redirection.

## 6. Recommended Implementation Order

Proceed in the following order rather than filling entries randomly across the repository:

1. Generate the missing-entry report.
2. Complete `templates/*.txt` first.
3. Then complete the `modules/*.po` entries directly tied to recently added features.
4. Then complete `game_configs_modules/*.po`.
5. Then scan frontend and backend for hardcoded copy.
6. Build `.mo`.
7. Run the locale tests.
8. Do manual acceptance testing.

Rationale:

1. Missing `templates` directly affect whether LLM features work.
2. New feature paths are more likely than older modules to have obvious gaps.
3. Configuration text is the largest workload and is best handled in bulk after the framework path works end to end.

## 7. Suggested Batches

### Batch 1: Basic Closed Loop

Goals:

1. All `en-US` template files are present.
2. Locale tests run and produce stable results.
3. New features are fully usable in `en-US`.

### Batch 2: Feature Path Completion

Goals:

1. Complete runtime text for recently added systems.
2. Prioritize:
   1. roleplay
   2. single choice
   3. conversation
   4. frontend hints related to the external-control API

### Batch 3: Content Layer Completion

Goals:

1. Complete configuration text and world content.
2. Improve overall immersion in English, not just make the interface readable.

### Batch 4: Quality Wrap-Up

Goals:

1. Unify terminology.
2. Unify placeholder style.
3. Clean up duplicate, outdated or structurally inconsistent entries.

## 8. Testing and Validation

### 8.1 Required

1. `python tools/i18n/generate_missing_report.py`
2. `python tools/i18n/build_mo.py`
3. `pytest tests/test_frontend_locales.py`
4. `pytest tests/test_backend_locales.py`

### 8.2 Recommended

1. `pytest tests/test_i18n_dynamic.py`
2. `pytest tests/test_i18n_integrity.py`
3. `pytest tests/test_i18n_modules.py`
4. `pytest tests/test_runtime_i18n_guards.py`
5. `pytest tests/test_locale_registry_migration.py`

### 8.3 Manual Acceptance

Check at least the following path in `en-US`:

1. Open the system menu.
2. Start a new game.
3. Review the basic UI of the main screen.
4. Open avatar detail.
5. Review the event panel on the right.
6. Perform one roleplay decision.
7. Perform one roleplay choice.
8. Perform one roleplay conversation.
9. Save and load, then confirm all text is still in English.

## 9. Acceptance Criteria

The i18n rollout is considered complete when:

1. The `en-US` locale has a complete directory skeleton as defined by `registry.json`.
2. `generate_missing_report.py` no longer reports gaps in new feature paths.
3. Locale tests pass.
4. New feature paths are fully usable in `en-US`.
5. User-visible hardcoded text (especially Chinese) is reduced to an acceptable level.
6. The `en-US` template files are structurally consistent.

## 10. Implementation Advice

If only one "first-stage rollout" round is planned, the suggested priority is:

1. Complete the templates first.
2. Then complete the new roleplay / choice / conversation path.
3. Then complete frontend and backend runtime fallbacks.
4. Finally complete the bulk of configuration text.

Rationale:

1. This path is the fastest way to eliminate "new features are only fully usable in Chinese".
2. It also shows the most tangible benefit in tests and hands-on play.
