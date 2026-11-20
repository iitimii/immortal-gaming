# Image Generation Design Notes

This document captures the image generation approach used by `tools/img_gen`, focusing on avatar prompts,
realm changes, naming and post-processing conventions.

## General Principles

1. Generation prompts describe visible content first; do not include character backstories.
2. The cultivation feel is expressed through visible elements such as hair crowns, forehead marks, eye makeup,
   ornaments, collar patterns and close-fitting spiritual glow.
3. Avatars keep a pure white background with the subject centered; hair and ornaments must not touch the image
   edges, which makes background removal easier.
4. Do not generate a four-panel grid in one image; each realm is generated as a separate image.
5. Qi Refinement avatars use text-to-image. Foundation Establishment, Golden Core and Nascent Soul are all image
   edits based on the Qi Refinement image; no chained edits.
6. Filenames must be traceable: gender, appearance index, race and realm all go into the filename.

## Prompt Layers

Avatar prompts are composed in layers:

```text
base avatar constraints
+ appearance description
+ realm appearance modifier
```

The base avatar constraints keep the output form stable:

```text
Anime manga style, slightly chibi, facing the camera head-on.
Pure white background; the background must be clean, with no texture, shadow, gradient, mist, glow or border.
The character is complete and centered, showing only the complete head, face and a little of the shoulders and neck; the subject has crisp edges.
Pixel art style, not too much detail.
```

Appearance descriptions only cover visible traits, for example:

```text
Light yellow loose hair, pale complexion, plain hair band, soft faint brows and eyes, pale green glow like medicinal mist.
```

Do not write invisible identity details such as "alchemist", "curse cultivator", "sect" or background lore.

## Realm Design

The four realms are:

```text
qi_refining   Qi Refinement
foundation    Foundation Establishment
golden_core   Golden Core
nascent_soul  Nascent Soul
```

The Qi Refinement stage uses text-to-image. Foundation Establishment, Golden Core and Nascent Soul use the
OpenAI-compatible Images edits endpoint with the Qi Refinement image as input and no mask. This preserves the
character's core appearance far better than four independent text-to-image generations.

All three higher realms are edited directly from the Qi Refinement image instead of chaining
`Qi Refinement -> Foundation Establishment -> Golden Core -> Nascent Soul`. This reduces quality loss and
appearance drift caused by successive edits.

Realm presentation should follow:

1. Qi Refinement: plainer and more youthful, with weak ornaments and light effects.
2. Foundation Establishment: steadier and fresher, existing ornaments and patterns slightly more refined.
3. Golden Core: more condensed and brighter, existing features gain finer texture.
4. Nascent Soul: more translucent and ethereal, existing light effects and patterns softer and more elegant.

Key point: realm modifiers should enhance the character's *existing visible traits*. Do not append the same
forehead spirit mark, golden halo or silver-white rim light to every avatar, otherwise every high-realm avatar
looks like the same upgrade effect.

Image edit prompts may use constraints like "keep the input avatar's main appearance, composition and pure white
background" because the model has the input image as reference. The text-to-image stage does not rely on such
preservation constraints.

Preservation requirements in the edit stage must be explicit, otherwise the model tends to turn the pixel avatar
into an HD illustration or redraw a different character while "upgrading the realm". Current edit prompt
preservation priorities:

1. Must keep the input image's pixel art style, low level of detail and chibi anime manga style.
2. Must keep face shape, facial proportions, skin tone, hairstyle, hair color, eye color and pupil shape.
3. Must keep the base expression, the position and basic shape of existing facial marks, and the main hair
   ornaments or earrings.
4. Must keep subject size, head-and-shoulder ratio, front-facing portrait composition and pure white background.
5. Yao must additionally keep the position and basic shape of race traits, such as fox ears, wolf ears, ear
   plumes, slit pupils, scale patterns, tortoiseshell patterns and cheek markings.

Allowed changes in the edit stage focus on the sense of advancement: gaze intensity, pupil highlights, collar
layering, ornament refinement, clarity of existing patterns and close-fitting faint glow. Changes may be quite
noticeable, but never at the cost of the pixel style or character recognizability.

The edit stage must not output realistic, HD illustration, thick-paint or overly detailed styles, background
scenes, halos, borders or large-area effects.

## Humans vs. Yao

Human avatars use one fairly abstract set of realm rules, emphasizing plainness, refinement, gaze and the
enhancement of existing traits.

Yao avatars do not share the human realm rules, nor do different yao races share one set of rules. Each race has
its own realm presentation material:

| Race | Realm changes mainly rely on |
|---|---|
| Fox | fox ears, eye-corner makeup, fox-shaped ornaments, soft close-fitting glow |
| Wolf | wolf ears, wolf cheek markings, forehead guard or beast-fang ornaments, cool-toned highlights |
| Bird | feather crest, ear plumes, colored eye-corner markings, feather ornaments |
| Snake | slit pupils, fine scale patterns, snake-shaped earrings, cool-toned highlights |
| Turtle | tortoiseshell patterns, jade ornaments, heavy collar, warm smooth luster |

This keeps realm changes distinct between yao races instead of uniformly applying "yao patterns get brighter".

## Background-Removal-Friendly Constraints

Post-processing currently removes the background with a white flood fill, so prompts must help the model output a
clean background:

1. Explicitly require a pure white background.
2. Explicitly forbid background texture, shadows, gradients, mist, glow and borders.
3. Light effects should stay close to the character, written as eye highlights, glowing hair tips, ornament
   sheen or close-fitting faint glow.
4. Avoid descriptions like "wreathed in mist", "halo behind", "background magic circle" or "spread wings" that
   pollute the white background or enlarge the subject area.
5. White hair, light ornaments and light collars are easily removed by mistake; keep subject edges crisp and away
   from the image edges.

If white-background removal becomes unreliable, consider switching to a pure green or magenta background with a
dedicated chroma-key algorithm. For now the design is optimized around the white-background pipeline.

## Naming and Manifests

Human avatar naming:

```text
female_001_qi_refining.png
male_001_nascent_soul.png
```

Yao avatar naming:

```text
fox_female_01_qi_refining.png
snake_male_03_golden_core.png
```

The Qi Refinement text-to-image output directory gets a `manifest.json`. The Foundation Establishment, Golden Core
and Nascent Soul image edits write `realm_edit_manifest.json`. Manifests record each image's source fields, source
image and full prompt, and are the basis for later debugging, reruns and asset integration.

Post-processing keeps the original filenames and directory structure by default, so this tracking information is
not lost.
