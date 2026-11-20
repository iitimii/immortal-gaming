# Frontend I18n Guide

The frontend uses Vue I18n with modular JSON files. `en-US` is the only locale; it comes from `static/locales/registry.json` like every other part of the i18n system. Backend rules and workflows are in `docs/i18n-guide.md`.

## 1. Directory Structure

UI strings are split by feature module instead of one large JSON file. This avoids merge conflicts, keeps keys easy to find, and mirrors the backend layout (`static/locales/en-US/modules/*.po`).

```text
web/src/locales/
├── en-US/
│   ├── ui.json           # menus, basic UI buttons, ...
│   ├── game.json         # in-game text (status bar, panels, details, ...)
│   ├── llm.json          # LLM settings page
│   ├── loading.json      # loading screen and tips
│   └── ...               # other modules
├── registry.ts           # frontend view of static/locales/registry.json
└── index.ts              # auto-discovers and aggregates the JSON modules
```

## 2. Adding Strings

1. **Pick the module** (`ui.json`, `game.json`, ...). For a large new system, create a new module file such as `web/src/locales/en-US/achievement.json`.
2. **Add the key.** Keys are namespaced by the file name automatically.
   - Example: add `"new_button": "New Button"` to `en-US/ui.json`.
   - Use it in Vue as `$t('ui.new_button')`.
3. **Keep short slots short.** Titles, labels, tabs, buttons, badges, and `*_short` keys should be concise; put full explanations in `*_desc` / help keys.
4. **Prefer backend-localized DTOs for config-driven options** (races, sect options, etc.) instead of hardcoding user-visible labels in the frontend.

## 3. Auto-Aggregation (`index.ts`)

You do **not** need to import new JSON files manually. `web/src/locales/index.ts` uses Vite's `import.meta.glob('./*/*.json')` to load every module of every enabled locale and uses the file name as the top-level key:

```typescript
// If en-US/ui.json contains { "start": "Start" }
// the result is { "en-US": { "ui": { "start": "Start" } } }
```

The enabled locales, default locale, and fallback locale come from `web/src/locales/registry.ts`, which reads `static/locales/registry.json` directly.

## 4. Type Safety

The message schema type is derived from the registry's `schema_locale` (currently `en-US`):

```typescript
const schemaMessages = isEnabledLocale(schemaLocale)
  ? loadLocaleMessages(schemaLocale)
  : {}

type MessageSchema = typeof schemaMessages
```

If `$t()` has no autocomplete or TypeScript reports an unknown key, check that the key exists in the `schema_locale` JSON module.

## 5. Validation and CI

```bash
pytest tests/test_frontend_locales.py
cd web && npm run type-check
```

`tests/test_frontend_locales.py` flattens each JSON module into dot-separated key paths and verifies that every registered locale has the same module files and keys (trivially satisfied with one locale, but it protects future locales), plus popup-type coverage.

Both checks run in `.github/workflows/test.yml`: the backend `pytest` step covers the locale tests and the frontend job runs `npm run type-check`.
