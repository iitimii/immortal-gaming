---
name: i18n-development
description: Internationalization (i18n) development guide for the English-only (en-US) game. Use when adding new text, creating items/events, editing strings or LLM prompt templates, or managing PO/MO files.
---

# I18n Development Guide

The game is English-only. `static/locales/registry.json` lists `en-US` as the single locale, and it is the default, fallback, schema, and source-of-truth locale. Long-term constraints live in `.cursor/rules/i18n.mdc`.

## Where Text Lives

| Kind of text | Source to edit |
|---|---|
| Backend messages (`t()` in Python) | `static/locales/en-US/modules/*.po` |
| Game config names/descriptions (CSV `name_id` / `desc_id`, effects) | `static/locales/en-US/game_configs_modules/*.po` |
| Locale-specific game config data (e.g. name lists) | `static/locales/en-US/game_configs/*.csv` |
| LLM prompt templates | `static/locales/en-US/templates/*.txt` |
| Frontend UI strings | `web/src/locales/en-US/*.json` |

Build products, never edited directly:

- `static/locales/en-US/LC_MESSAGES/messages.po` and `static/locales/en-US/LC_MESSAGES/game_configs.po` are merged from the split modules.
- The `.mo` files next to them are compiled from those.

## Core Daily Operations

### 1. Adding a new message

Append the entry to the matching `.po` file in `static/locales/en-US/modules/` or `static/locales/en-US/game_configs_modules/`.

**Format requirements:**
- Keep **one blank line** between entries.
- `msgid` is the English source text or a stable key (e.g. `attack_description`).
- `msgstr` is the final English text shown to players. For source-text msgids it is usually identical to `msgid`.

```po
msgid "Found {amount} spirit stone"
msgstr "Found {amount} spirit stone"

msgid "attack_description"
msgstr "Attack the target with your weapon and techniques."
```

### 2. Adding a new PO file

When developing a new feature, create a new `.po` file (for example `modules/new_feature.po`).
- **Rule**: do **not** add PO headers (such as `Project-Id-Version`) to these split module files. The build script handles headers. Start directly with `msgid` entries.

### 3. Key design: short slots vs. long text

- Short-slot keys (`title`, `label`, `tab`, `button`, `badge`, `status`, `*_short`, menu items, status bar entries, card titles) must be concise and natural.
- Full explanations go into `*_desc`, `help`, tooltip, or body keys. If one string would have to serve both a narrow button and a dialog explanation, split it into separate short/long keys.

### 4. Critical: always rebuild

Changes to `.po` or `.csv` files do **not** take effect in game until they are merged and compiled to `.mo`.
**Always run the build script after any string change:**

```bash
python tools/i18n/build_mo.py
```

---

## Critical Rules (summary)

- **Never** use redirection (`>>`) in Windows PowerShell to append to PO files (it produces UTF-16LE encoding and `\x00` corruption).
- **Encoding**: UTF-8 without BOM.
- **Do not edit** `LC_MESSAGES/messages.po` or `LC_MESSAGES/game_configs.po` directly. Edit the split `.po` files in `modules/` or `game_configs_modules/`, then run `build_mo.py`.
- **Locale list**: always read it from `static/locales/registry.json` (Python: `src/i18n/locale_registry.py`, re-exported by `tools/i18n/locale_registry.py`; frontend: `web/src/locales/registry.ts`). Never maintain a handwritten locale list in tools or tests.
- **No hardcoded player-facing text in logic**: put user-visible strings behind `t()` keys, frontend locale keys, or templates. LLM/runtime-generated text constraints and prompt fragments belong in `static/locales/en-US/templates/` or translation keys, not in Python string literals.
- **Backend-driven labels**: for configuration-type selectors (races, yao race action/effect keys, avatar creation options, etc.) the backend provides localized structured DTOs; the frontend must not hardcode those labels.

## Workflows and Patterns (summary)

### Python dynamic text
Use `t()` from `src.i18n`.

```python
from src.i18n import t
msg = t("{actor} performs action", actor=self.avatar.name)
```

### CSV game configs
1. Edit the CSV (add `name_id` and `desc_id`).
2. Extract the POT: `python tools/i18n/extract_csv.py`
3. Add the English text in `static/locales/en-US/game_configs_modules/{category}.po`.
4. Rebuild: `python tools/i18n/build_mo.py`

### Effects (JSON) & avatar info
- **JSON**: use `_desc` and `when_desc` to override descriptions via translation keys.
- **Dictionaries**: translate keys directly (for example `t("Name"): self.name`).

### Frontend strings
Add keys to the matching file in `web/src/locales/en-US/` (e.g. `common.json`, `game.json`). Keep JSON valid and follow the same short-slot vs. `*_desc` split.

### Validation

```bash
pytest tests/test_backend_locales.py tests/test_frontend_locales.py
```

Other helpers in `tools/i18n/` (use as needed): `split_po.py`, `cleanup_po_comments.py` / `preview_po_cleanup.py`, `split_action_module.py` / `preview_action_split.py`, `generate_missing_report.py`.

## Adding a Language Later

1. Register the locale in `static/locales/registry.json` first.
2. Then scaffold its directories and resources: `static/locales/<lang>/modules/`, `game_configs_modules/`, `game_configs/`, `templates/`, and `web/src/locales/<lang>/`.
3. Tools under `tools/i18n/` and the locale tests read the registry; never hardcode a locale list in scripts.
4. `.po` `msgid`s stay as English source text or stable keys; non-English locales must never use copied English (or any other language's) `msgstr` as placeholder translations.
5. If non-English UI languages are added, the language entry in `web/src/components/SystemMenu.vue` must keep a visible English `Language` hint (e.g. `<localized word> / Language`).
