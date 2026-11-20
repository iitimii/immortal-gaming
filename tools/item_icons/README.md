# Item Icon Generation

This directory batch-generates item icons, covering:

- `weapon`: weapons
- `elixir`: elixirs
- `auxiliary`: auxiliary equipment
- `technique`: techniques
- `goldfinger`: goldfingers (innate talents)
- `material`: other materials

## Secrets

Put the real key in `tools/item_icons/.env`; that file is ignored by this directory's `.gitignore`.

```env
ITEM_ICON_API_KEY=sk-user-...
ITEM_ICON_API_BASE_URL=https://api2.tabcode.cc/openai/draw/v1
ITEM_ICON_API_MODEL=gpt-image-2
ITEM_ICON_API_SIZE=1024x1024
```

You can also inject the same names as environment variables to avoid writing them to disk.

## Connectivity

```powershell
$env:ITEM_ICON_API_KEY="sk-user-..."
python -m tools.item_icons.ping_api
```

On success it writes `tools/item_icons/connectivity.png` and `connectivity.json`. These verification artifacts are not committed to git.

## Manifest

```powershell
python -m tools.item_icons.build_manifest
```

The script builds the list of items to draw from `static/game_configs/*.csv` and writes it to `manifest.generated.json`, which is ignored by default.

## Postprocess

```powershell
python -m tools.item_icons.postprocess split raw/sheet.png split --columns 4 --rows 4 --prefix weapon_batch_001
python -m tools.item_icons.postprocess clean split/weapon_batch_001_01.png processed/weapon_1001.alpha.png
python -m tools.item_icons.postprocess pixelate processed/weapon_1001.alpha.png processed/weapon_1001.png
```

Suggested production pipeline:

1. Batch the manifest by category and visual similarity, 9 or 16 items per batch.
2. Use `prompts.build_contact_sheet_prompt()` to generate a 3x3 or 4x4 contact sheet.
3. Split the sheet, remove the `#ff00ff` background and pixelate to a uniform size.
4. Check blank ratio, transparent corners, size and filenames manually or with a script.
5. Publish to `web/src/assets/icons/items/`, then generate the frontend mapping file.
