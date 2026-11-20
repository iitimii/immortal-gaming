# Adding a New Language

The game currently ships only `en-US`, which is the source-of-truth locale. This is a checklist for adding another language in the future. Day-to-day string work is covered by `docs/i18n-guide.md` and `docs/frontend-i18n.md`.

## 1. Register the Locale First

Always start with `static/locales/registry.json`. Do not copy directories or touch the language menu before this step.

```json
{
  "code": "fr-FR",
  "label": "Français",
  "html_lang": "fr",
  "enabled": true
}
```

- `code`: directory name, runtime locale code, and the code stored in saves
- `label`: name shown in the language selector
- `html_lang`: value written to `<html lang>`; also decides name joining (see 5.1)
- `enabled`: whether the locale is active
- `source_of_truth`: keep this on `en-US` only

The global fields `default_locale`, `fallback_locale`, and `schema_locale` normally stay `en-US`.

Never hardcode locale lists in scripts, tests, or runtime code. Everything below reads the registry.

## 2. What Already Picks Up New Locales Automatically

These read the registry or scan locale directories, so they need no code changes:

- Python helpers: `src/i18n/locale_registry.py`
- Backend language switching and defaults: `src/classes/language.py`, `src/i18n/__init__.py`
- Template resolution with fallback: `src/i18n/template_resolver.py`
- Frontend registry and loader: `web/src/locales/registry.ts`, `web/src/locales/index.ts`
- `<html lang>` sync: `web/src/stores/setting.ts`
- i18n tools in `tools/i18n/` and the locale tests (`tests/test_frontend_locales.py`, `tests/test_backend_locales.py`, `tests/test_i18n_modules.py`, `tests/test_csv_loading.py`)

The work is mostly resources and translation.

## 3. Create the Resource Skeleton

Copy the full `en-US` structure, then translate. Do not start with just the menu entry or a single JSON/PO file; that produces a locale you can switch to but that is mostly missing.

| Path | Contents |
|---|---|
| `web/src/locales/<locale>/*.json` | Frontend UI strings; same file names and key structure as `en-US` |
| `static/locales/<locale>/modules/*.po` | Backend `t()` dynamic text; edit these, never `LC_MESSAGES/messages.po` |
| `static/locales/<locale>/game_configs_modules/*.po` | CSV `name_id`/`desc_id` translations; never edit `LC_MESSAGES/game_configs.po` |
| `static/locales/<locale>/LC_MESSAGES/` | Build output from `python tools/i18n/build_mo.py` |
| `static/locales/<locale>/templates/*.txt` | LLM prompt templates (same file set as `en-US`) |
| `static/locales/<locale>/game_configs/*.csv` | Locale-specific CSV data such as `given_name.csv` / `last_name.csv` |

Keep `msgid`s identical to `en-US` (English source text or stable keys); only `msgstr` changes.

## 4. Recommended Order

1. Update `static/locales/registry.json`.
2. Copy `web/src/locales/en-US/` to `web/src/locales/<locale>/`.
3. Copy `static/locales/en-US/` to `static/locales/<locale>/`.
4. Check `templates/` and the name CSVs in `game_configs/`.
5. Run `python tools/i18n/build_mo.py`.
6. Run the validation commands below.
7. Translate, keeping terminology consistent (consider adding a column for the new language to `docs/glossary.csv`).

Steps 1-6 give you a wired-up skeleton; step 7 makes the language actually usable.

## 5. Common Pitfalls

### 5.1 Name joining

Whether given/family names are joined with a space is derived from `html_lang` (`uses_space_separated_names` in `src/i18n/locale_registry.py`): `zh`, `ja`, and `ko` join without a space, everything else with one. Adjust if the new language needs different behavior.

### 5.2 Missing templates

If `templates/*.txt` are missing, the game still runs but falls back to the source-locale templates, so generated content stays in English.

### 5.3 Frontend only

Translating only the frontend leaves backend `t()` text, CSV config names, and story templates in English.

### 5.4 Forgetting to rebuild

After any `.po` change, run `python tools/i18n/build_mo.py`, or the runtime will not see it.

### 5.5 Short slots

Languages such as French or Vietnamese run long. Keep `title`/`label`/`tab`/`button`/`*_short` translations concise and natural; put full explanations in `*_desc` / help keys, adding a short/long key split if needed.

## 6. Validation

```bash
python tools/i18n/build_mo.py
python tools/i18n/generate_missing_report.py
python tools/i18n/compare_msgids_across_locales.py
pytest tests/test_frontend_locales.py tests/test_backend_locales.py tests/test_i18n_modules.py tests/test_i18n_integrity.py
pytest tests/test_csv_loading.py tests/test_language.py
cd web && npm run type-check
cd web && npm run test:run -- src/__tests__/stores/setting.test.ts src/__tests__/components/SystemMenu.test.ts
```

## 7. Done Checklist

- [ ] Registered in `static/locales/registry.json`
- [ ] Full frontend and backend directory sets exist
- [ ] `templates/` and name CSVs handled
- [ ] `.mo` files rebuilt
- [ ] Locale tests and type-check pass
- [ ] Terminology agreed (glossary)
- [ ] One in-game playthrough checked in the new language

New scaffolding scripts should reuse `src/i18n/locale_registry.py` and keep the locale list defined only in `static/locales/registry.json`.
