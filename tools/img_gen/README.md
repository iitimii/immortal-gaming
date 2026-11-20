# Image Generation Tools

This directory is a local asset generation toolkit that currently uses an OpenAI-compatible image API.
API configuration, prompt data, generation scripts and post-processing scripts all live under `tools/img_gen/`.

See [DESIGN.md](./DESIGN.md) for image generation design principles.

## Setup

Create the local env file first:

```powershell
Copy-Item tools/img_gen/image_api.env.example tools/img_gen/image_api.env
```

Then fill in `tools/img_gen/image_api.env`:

```env
IMAGE_API_KEY=your-key
```

`image_api.env` is ignored by `.gitignore`; never commit a real key. A system environment variable with the same
name overrides the value in `image_api.env`.

Before running these tools, install this directory's tool dependencies:

```powershell
pip install -r tools/img_gen/requirements.txt
```

## Entry Points

| Task | Script | Common command | Default output |
|---|---|---|---|
| Test whether the image API works | `generate_preview.py` | `python tools/img_gen/generate_preview.py --open` | `tools/img_gen/tmp/preview/` |
| Stage 1: generate human female Qi Refinement base avatars | `generate_avatars.py` | `python tools/img_gen/generate_avatars.py --gender female` | `tools/img_gen/tmp/avatars/female/` |
| Stage 1: generate human male Qi Refinement base avatars | `generate_avatars.py` | `python tools/img_gen/generate_avatars.py --gender male` | `tools/img_gen/tmp/avatars/male/` |
| Stage 2: edit human Qi Refinement images into the three higher realms | `edit_avatar_realms.py` | `python tools/img_gen/edit_avatar_realms.py --gender female` | Writes back to the input directory by default |
| Stage 1: generate yao Qi Refinement base avatars | `generate_yaoguai_avatars.py` | `python tools/img_gen/generate_yaoguai_avatars.py` | `tools/img_gen/tmp/yaoguai_avatars/` |
| Stage 2: edit yao Qi Refinement images into the three higher realms | `edit_yaoguai_avatar_realms.py` | `python tools/img_gen/edit_yaoguai_avatar_realms.py` | Writes back to the input directory by default |
| Generate sect images | `generate_sects.py` | `python tools/img_gen/generate_sects.py` | `tools/img_gen/tmp/sects/` |
| Generate map tile images | `generate_tiles.py` | `python tools/img_gen/generate_tiles.py plain forest mountain` | `tools/img_gen/tmp/tiles/` |
| Post-process human avatars | `postprocess_avatars.py` | `python tools/img_gen/postprocess_avatars.py --input-dir tools/img_gen/tmp/avatars/female --output-dir tools/img_gen/tmp/processed_avatars/female` | The given `--output-dir` |
| Post-process yao avatars | `postprocess_yaoguai_avatars.py` | `python tools/img_gen/postprocess_yaoguai_avatars.py` | `tools/img_gen/tmp/processed_yaoguai_avatars/` |
| Publish avatars to game assets | `publish_avatar_assets.py` | `python tools/img_gen/publish_avatar_assets.py --use-processed` | `assets/avatars/` and `assets/yao/` |
| Post-process sect images | `postprocess_sects.py` | `python tools/img_gen/postprocess_sects.py` | `tools/img_gen/tmp/processed_sects/` |

All generation and edit scripts skip target files that already exist by default, to avoid paying twice. Add
`--overwrite` to regenerate.

## Human Avatars

Human avatar prompts are maintained in `prompts_avatars.py`.

The current pipeline has two stages:

1. Text-to-image generates the Qi Refinement base avatar.
2. The Qi Refinement image is used as input to the image edit endpoint to generate Foundation Establishment,
   Golden Core and Nascent Soul.

Each gender currently has 48 appearance descriptions. A full run produces:

```text
48 appearances * 4 realms * 2 genders = 384 images
```

Generate Qi Refinement first:

```powershell
python tools/img_gen/generate_avatars.py --gender female
python tools/img_gen/generate_avatars.py --gender male
```

Then edit the three higher realms from the Qi Refinement images:

```powershell
python tools/img_gen/edit_avatar_realms.py --gender female
python tools/img_gen/edit_avatar_realms.py --gender male
```

Trial run with only a few images:

```powershell
python tools/img_gen/generate_avatars.py --gender female --limit 2
python tools/img_gen/edit_avatar_realms.py --gender female --limit 2 --realm golden_core
```

Filenames keep the gender, appearance index and realm:

```text
tools/img_gen/tmp/avatars/female/female_001_qi_refining.png
tools/img_gen/tmp/avatars/female/female_001_foundation.png
tools/img_gen/tmp/avatars/female/female_001_golden_core.png
tools/img_gen/tmp/avatars/female/female_001_nascent_soul.png
```

`manifest.json` records Qi Refinement text-to-image jobs. `realm_edit_manifest.json` records image edit jobs,
including the source image, target realm and full prompt.

## Yao Avatars

Yao avatar prompts are maintained in `prompts_yaoguai_avatars.py`.

There are currently 5 races:

```text
fox     Fox
wolf    Wolf
bird    Bird
snake   Snake
turtle  Turtle
```

Each race has 9 appearances, each appearance has 4 realms, with one set per gender. A full run produces:

```text
5 races * 9 appearances * 4 realms * 2 genders = 360 images
```

Generate Qi Refinement first:

```powershell
python tools/img_gen/generate_yaoguai_avatars.py
```

Then edit the three higher realms from the Qi Refinement images:

```powershell
python tools/img_gen/edit_yaoguai_avatar_realms.py
```

If the first 3 appearances were already generated, just run the commands above; the scripts skip existing files by
default and only fill in the new appearances 4-9. Do not add `--overwrite`, or the old images will be regenerated
and billed again.

Trial run with only the first fox female appearance:

```powershell
python tools/img_gen/generate_yaoguai_avatars.py --species fox --gender female --limit 1
python tools/img_gen/edit_yaoguai_avatar_realms.py --species fox --gender female --limit 1
```

Files are grouped into directories by race and gender:

```text
tools/img_gen/tmp/yaoguai_avatars/fox/female/fox_female_01_qi_refining.png
tools/img_gen/tmp/yaoguai_avatars/fox/female/fox_female_01_foundation.png
tools/img_gen/tmp/yaoguai_avatars/fox/female/fox_female_01_golden_core.png
tools/img_gen/tmp/yaoguai_avatars/fox/female/fox_female_01_nascent_soul.png
```

`manifest.json` and `realm_edit_manifest.json` are written as well.

## Post-processing

Avatar post-processing trims the edges, removes the pure white background and resizes to `512x512` by default.
Human avatars keep their original filenames, so `gender_index_realm` is still visible after processing.

```powershell
python tools/img_gen/postprocess_avatars.py --input-dir tools/img_gen/tmp/avatars/female --output-dir tools/img_gen/tmp/processed_avatars/female
python tools/img_gen/postprocess_avatars.py --input-dir tools/img_gen/tmp/avatars/male --output-dir tools/img_gen/tmp/processed_avatars/male
```

Yao avatar post-processing walks the race and gender directories recursively and keeps the same directory
structure:

```powershell
python tools/img_gen/postprocess_yaoguai_avatars.py
```

Sect images are only trimmed and resized; the white background is not removed:

```powershell
python tools/img_gen/postprocess_sects.py
```

## Maintenance Notes

1. Real keys belong only in `tools/img_gen/image_api.env` or system environment variables.
2. When adding human avatar prompts, keep the male and female counts equal.
3. Qi Refinement images are the source for the higher-realm edits; do not delete them casually.
4. Realm differences should come from the strength, refinement and temperament of existing visible traits; do not
   apply the same spirit pattern or light effect to every character.
5. Background constraints should stay pure white, clean, shadowless and gradient-free to ease background removal.
6. Image-to-image edits must keep the input image's pixel art style, low level of detail and chibi anime manga
   style; never turn avatars into realistic, HD illustration, thick-paint or overly detailed styles.
7. Image-to-image edits must also protect character-identifying traits: face shape, facial proportions, skin tone,
   hairstyle, hair color, eye color, pupil shape, base expression, existing facial marks, main ornaments, subject
   size, head-and-shoulder ratio and the pure white background.
8. Yao image-to-image edits must additionally protect the position and basic shape of race traits, such as fox
   ears, wolf ears, ear plumes, slit pupils, scale patterns, tortoiseshell patterns and cheek markings.
