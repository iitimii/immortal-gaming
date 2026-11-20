from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from tqdm import tqdm

from tools.img_gen.client import edit_image_bytes
from tools.img_gen.prompts_yaoguai_avatars import (
    SPECIES_NAMES,
    YAOGUAI_REALM_SLUGS,
    yaoguai_avatar_prompt_records,
)

BASE_REALM_SLUG = "qi_refining"
TARGET_REALM_SLUGS = ["foundation", "golden_core", "nascent_soul"]

REALM_EDIT_STYLES = {
    "Foundation Establishment": (
        "Foundation Establishment upgrade intensity is moderate: clothing, jewelry and accessories become neater, steadier and more refined within the existing color scheme; "
        "yao patterns become clearer but not overly ornate, conveying a solid foundation. "
    ),
    "Golden Core": (
        "Golden Core upgrade intensity is pronounced: clothing, jewelry and accessories become more powerful, more ornate and more condensed in texture within the existing color scheme; "
        "yao patterns, accessory materials and pupil highlights may be more striking. "
    ),
    "Nascent Soul": (
        "Nascent Soul upgrade intensity is the highest but more ethereal: clothing, jewelry and accessories become more immortal-like, more translucent and more luxurious within the existing color scheme; "
        "yao patterns are more elegant, materials lighter and more exquisite; powerful overall but not heavy. "
    ),
}


def build_yaoguai_edit_prompt(
    *,
    appearance_prompt: str,
    realm_prompt: str,
    realm_name: str,
) -> str:
    return (
        f"Upgrade the input yao avatar to the {realm_name} stage with roughly 55% change; it must be clearly stronger than the original. "
        "Keep only enough to recognize the same yao character: the input image's pixel art style, low level of detail, chibi anime manga style, face shape and rough facial proportions, hairstyle silhouette, hair color, core yao race traits, front-facing portrait composition, and pure white background. "
        "Clearly allowed to change: expression, temperament, apparent age, collar and clothing, complexity of hair ornaments or earrings, accessory materials, gaze intensity, pupil highlights, existing yao patterns, close-fitting faint glow. "
        "Must make significant visible changes: at least four of gaze, clothing layers, accessory refinement, yao patterns or close-fitting light effects must be clearly upgraded. "
        f"{REALM_EDIT_STYLES.get(realm_name, '')}"
        "You may make yao patterns clearer, accessory materials more premium, the collar more ornate and close-fitting light effects stronger, but light effects must stay close to the character's body. "
        "Do not just slightly adjust colors; the realm advancement and increase in yao power must be obvious at a glance. "
        "Do not change the gender; do not change the core race traits; do not add a background, border, scene, halo, spread wings or large-area effects. "
        "Do not switch to a realistic, high-definition illustration, thick-paint or overly detailed style; it must remain a pixel avatar. "
        f"Appearance reference: {appearance_prompt} "
        f"Realm change: {realm_prompt}"
    )


def edit_yaoguai_avatar_realms(
    *,
    input_dir: str | Path = "tools/img_gen/tmp/yaoguai_avatars",
    output_dir: str | Path | None = None,
    species_slugs: list[str] | None = None,
    genders: list[str] | None = None,
    realm_slugs: list[str] | None = None,
    limit: int | None = None,
    overwrite: bool = False,
    max_retries: int = 3,
    retry_delay: float = 5.0,
) -> list[Path]:
    source_dir = Path(input_dir)
    target_dir = Path(output_dir) if output_dir else source_dir
    target_dir.mkdir(parents=True, exist_ok=True)

    selected_realms = realm_slugs or TARGET_REALM_SLUGS
    records = yaoguai_avatar_prompt_records(
        species_slugs=species_slugs,
        genders=genders,
        realm_slugs=selected_realms,
    )
    if limit is not None:
        records = [record for record in records if record.index <= limit]

    saved: list[Path] = []
    manifest: list[dict[str, str | int]] = []
    failures: list[dict[str, str | int]] = []
    for record in tqdm(records, desc="Editing yaoguai avatar realms"):
        source_name = f"{record.species_slug}_{record.gender}_{record.index:02d}_{BASE_REALM_SLUG}.png"
        relative_parent = Path(record.species_slug) / record.gender
        source_path = source_dir / relative_parent / source_name
        if not source_path.exists():
            tqdm.write(f"Missing Qi Refinement source image, skipping: {source_path}")
            continue

        output_path = target_dir / relative_parent / f"{record.filename_stem}.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_path.exists() and not overwrite:
            tqdm.write(f"Already exists, skipping: {output_path}")
            continue

        edit_prompt = build_yaoguai_edit_prompt(
            appearance_prompt=record.appearance_prompt,
            realm_prompt=record.realm_prompt,
            realm_name=record.realm_name,
        )
        try:
            image_bytes = edit_image_bytes(
                source_path,
                edit_prompt,
                max_retries=max_retries,
                retry_delay=retry_delay,
            )
        except Exception as exc:
            tqdm.write(f"Edit failed, skipping: {output_path} ({type(exc).__name__}: {exc})")
            failures.append(
                {
                    "stage": "realm_edit",
                    "species_slug": record.species_slug,
                    "species_name": record.species_name,
                    "gender": record.gender,
                    "index": record.index,
                    "source_file": str((relative_parent / source_name)).replace("\\", "/"),
                    "realm_slug": record.realm_slug,
                    "realm_name": record.realm_name,
                    "file": str(output_path.relative_to(target_dir)).replace("\\", "/"),
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "prompt": edit_prompt,
                }
            )
            continue
        output_path.write_bytes(image_bytes)
        saved.append(output_path)
        manifest.append(
            {
                "stage": "realm_edit",
                "species_slug": record.species_slug,
                "species_name": record.species_name,
                "gender": record.gender,
                "index": record.index,
                "source_file": str((relative_parent / source_name)).replace("\\", "/"),
                "realm_slug": record.realm_slug,
                "realm_name": record.realm_name,
                "file": str(output_path.relative_to(target_dir)).replace("\\", "/"),
                "prompt": edit_prompt,
            }
        )

    if manifest:
        (target_dir / "realm_edit_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    if failures:
        (target_dir / "realm_edit_failures.json").write_text(
            json.dumps(failures, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return saved


def main() -> None:
    parser = argparse.ArgumentParser(description="Edit qi-refining yaoguai avatars into higher realms.")
    parser.add_argument("--input-dir", default="tools/img_gen/tmp/yaoguai_avatars")
    parser.add_argument("--output-dir")
    parser.add_argument(
        "--species",
        action="append",
        choices=list(SPECIES_NAMES),
        help="Species slug. Repeat to select multiple. Empty means all species.",
    )
    parser.add_argument(
        "--gender",
        action="append",
        choices=["female", "male"],
        help="Gender. Repeat to select both. Empty means both genders.",
    )
    parser.add_argument(
        "--realm",
        action="append",
        choices=[slug for slug in YAOGUAI_REALM_SLUGS if slug != BASE_REALM_SLUG],
        help="Target realm slug. Repeat to select multiple. Empty means foundation/golden_core/nascent_soul.",
    )
    parser.add_argument("--limit", type=int, help="Limit appearance indexes per species and gender.")
    parser.add_argument("--overwrite", action="store_true", help="Regenerate existing files.")
    parser.add_argument("--max-retries", type=int, default=3, help="Retries per image for transient API errors.")
    parser.add_argument("--retry-delay", type=float, default=5.0, help="Initial retry delay seconds.")
    args = parser.parse_args()

    edit_yaoguai_avatar_realms(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        species_slugs=args.species,
        genders=args.gender,
        realm_slugs=args.realm,
        limit=args.limit,
        overwrite=args.overwrite,
        max_retries=args.max_retries,
        retry_delay=args.retry_delay,
    )


if __name__ == "__main__":
    main()
