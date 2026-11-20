from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from tqdm import tqdm

from tools.img_gen.client import edit_image_bytes
from tools.img_gen.prompts_avatars import AVATAR_REALMS, avatar_realm_prompt_records

BASE_REALM_SLUG = "qi_refining"
TARGET_REALM_SLUGS = ["foundation", "golden_core", "nascent_soul"]

REALM_EDIT_STYLES = {
    "Foundation Establishment": (
        "Foundation Establishment upgrade intensity is moderate: clothing, jewelry and accessories become neater, steadier and more refined within the existing color scheme; "
        "not overly ornate, conveying a solid foundation. "
    ),
    "Golden Core": (
        "Golden Core upgrade intensity is pronounced: clothing, jewelry and accessories become more powerful, more ornate and more condensed in texture within the existing color scheme; "
        "clearer metal, jade or high-tier patterns may be added. "
    ),
    "Nascent Soul": (
        "Nascent Soul upgrade intensity is the highest but more ethereal: clothing, jewelry and accessories become more immortal-like, more translucent and more luxurious within the existing color scheme; "
        "materials are lighter and more exquisite; powerful overall but not heavy. "
    ),
}


def build_avatar_edit_prompt(
    *,
    appearance_prompt: str,
    realm_prompt: str,
    realm_name: str,
) -> str:
    return (
        f"Upgrade the input avatar to the {realm_name} stage with roughly 55% change; it must be clearly stronger than the original. "
        "Keep only enough to recognize the same person: the input image's pixel art style, low level of detail, chibi anime manga style, face shape and rough facial proportions, hairstyle silhouette, hair color, front-facing portrait composition, and pure white background. "
        "Clearly allowed to change: expression, temperament, apparent age, collar and clothing, complexity of hair ornaments or earrings, accessory materials, gaze intensity, pupil highlights, existing patterns, close-fitting faint glow. "
        "Must make significant visible changes: at least four of gaze, clothing layers, accessory refinement, patterns or close-fitting light effects must be clearly upgraded. "
        f"{REALM_EDIT_STYLES.get(realm_name, '')}"
        "You may make the collar more ornate, accessory materials more premium, existing patterns clearer and close-fitting light effects stronger, but light effects must stay close to the character's body. "
        "Do not just slightly adjust colors; the realm advancement and increase in power must be obvious at a glance. "
        "Do not change the gender; do not add a background, border, scene, halo or large-area effects. "
        "Do not switch to a realistic, high-definition illustration, thick-paint or overly detailed style; it must remain a pixel avatar. "
        f"Appearance reference: {appearance_prompt} "
        f"Realm change: {realm_prompt}"
    )


def edit_avatar_gender_realms(
    gender: str,
    *,
    input_dir: str | Path | None = None,
    output_dir: str | Path | None = None,
    limit: int | None = None,
    realm_slugs: list[str] | None = None,
    overwrite: bool = False,
    max_retries: int = 3,
    retry_delay: float = 5.0,
) -> list[Path]:
    source_dir = Path(input_dir) if input_dir else Path("tools/img_gen/tmp/avatars") / gender
    target_dir = Path(output_dir) if output_dir else source_dir
    target_dir.mkdir(parents=True, exist_ok=True)

    selected_realms = realm_slugs or TARGET_REALM_SLUGS
    records = avatar_realm_prompt_records(gender, realm_slugs=selected_realms)
    if limit is not None:
        records = [record for record in records if record.index <= limit]

    saved: list[Path] = []
    manifest: list[dict[str, str | int]] = []
    failures: list[dict[str, str | int]] = []
    for record in tqdm(records, desc=f"Editing {gender} avatar realms"):
        source_name = f"{gender}_{record.index:03d}_{BASE_REALM_SLUG}.png"
        source_path = source_dir / source_name
        if not source_path.exists():
            tqdm.write(f"Missing Qi Refinement source image, skipping: {source_path}")
            continue

        output_path = target_dir / f"{record.filename_stem}.png"
        if output_path.exists() and not overwrite:
            tqdm.write(f"Already exists, skipping: {output_path}")
            continue

        edit_prompt = build_avatar_edit_prompt(
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
                    "gender": record.gender,
                    "index": record.index,
                    "source_file": source_name,
                    "realm_slug": record.realm_slug,
                    "realm_name": record.realm_name,
                    "file": output_path.name,
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
                "gender": record.gender,
                "index": record.index,
                "source_file": source_name,
                "realm_slug": record.realm_slug,
                "realm_name": record.realm_name,
                "file": output_path.name,
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


def edit_avatar_realms(
    *,
    genders: list[str] | None = None,
    input_dir: str | Path | None = None,
    output_dir: str | Path | None = None,
    limit: int | None = None,
    realm_slugs: list[str] | None = None,
    overwrite: bool = False,
    max_retries: int = 3,
    retry_delay: float = 5.0,
) -> list[Path]:
    selected_genders = genders or ["female", "male"]
    saved: list[Path] = []
    for gender in selected_genders:
        gender_input_dir = Path(input_dir) / gender if input_dir else None
        gender_output_dir = Path(output_dir) / gender if output_dir else None
        saved.extend(
            edit_avatar_gender_realms(
                gender,
                input_dir=gender_input_dir,
                output_dir=gender_output_dir,
                limit=limit,
                realm_slugs=realm_slugs,
                overwrite=overwrite,
                max_retries=max_retries,
                retry_delay=retry_delay,
            )
        )
    return saved


def main() -> None:
    parser = argparse.ArgumentParser(description="Edit qi-refining avatars into higher realms.")
    parser.add_argument(
        "--gender",
        action="append",
        choices=["male", "female"],
        help="Gender. Repeat to select both. Empty means both genders.",
    )
    parser.add_argument("--input-dir")
    parser.add_argument("--output-dir")
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--realm",
        action="append",
        choices=[realm_slug for realm_slug, _, _ in AVATAR_REALMS if realm_slug != BASE_REALM_SLUG],
        help="Target realm slug. Repeat to select multiple. Empty means foundation/golden_core/nascent_soul.",
    )
    parser.add_argument("--overwrite", action="store_true", help="Regenerate existing files.")
    parser.add_argument("--max-retries", type=int, default=3, help="Retries per image for transient API errors.")
    parser.add_argument("--retry-delay", type=float, default=5.0, help="Initial retry delay seconds.")
    args = parser.parse_args()

    edit_avatar_realms(
        genders=args.gender,
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        limit=args.limit,
        realm_slugs=args.realm,
        overwrite=args.overwrite,
        max_retries=args.max_retries,
        retry_delay=args.retry_delay,
    )


if __name__ == "__main__":
    main()
