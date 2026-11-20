from __future__ import annotations

from dataclasses import dataclass

YAOGUAI_COMMON_PROMPT_BASE = (
    "Anime manga style, slightly chibi, facing the camera head-on. "
    "Pure white background; the background must be clean, with no texture, shadow, gradient, mist, glow or border. "
    "The character is complete and centered, showing only the complete head, face and a little of the shoulders and neck; hair and hair ornaments must not touch the image edges; the subject has crisp edges. "
    "Keep the yao race traits clearly visible but attractive. Pixel art style, not too much detail."
)

FEMALE_YAOGUAI_PROMPT_BASE = f"An attractive xianxia yao female character avatar. {YAOGUAI_COMMON_PROMPT_BASE}"
MALE_YAOGUAI_PROMPT_BASE = f"An attractive xianxia yao male character avatar. {YAOGUAI_COMMON_PROMPT_BASE}"

REALM_ORDER = [
    ("qi_refining", "Qi Refinement"),
    ("foundation", "Foundation Establishment"),
    ("golden_core", "Golden Core"),
    ("nascent_soul", "Nascent Soul"),
]

YAOGUAI_REALM_SLUGS = [realm_slug for realm_slug, _ in REALM_ORDER]

SPECIES_REALMS = {
    "fox": [
        (
            "qi_refining",
            "Qi Refinement",
            "Qi Refinement stage look: fox-ear fur plainer and softer, very light makeup at the eye corners, simple fox-shaped ornaments, a slightly inexperienced expression. "
            "Do not add extra runes or large-area light effects.",
        ),
        (
            "foundation",
            "Foundation Establishment",
            "Foundation Establishment stage look: clearer fox-ear contours, more refined makeup at the eye corners, slightly more ornate fox-shaped ornaments, calmer eyes. "
            "Only enhance the existing hair color, earrings and close-fitting faint glow.",
        ),
        (
            "golden_core",
            "Golden Core",
            "Golden Core stage look: brighter pupil highlights, more condensed red or gold makeup at the eye corners, finer texture on fox-shaped ornaments. "
            "The existing fox ears, hair tips and earrings have a slight sheen; keep the effect restrained.",
        ),
        (
            "nascent_soul",
            "Nascent Soul",
            "Nascent Soul stage look: ethereal and elegant expression, lighter fox ears and hair strands, translucent makeup at the eye corners, more exquisite existing fox-shaped ornaments. "
            "Keep only a soft close-fitting glow; no background halo.",
        ),
    ],
    "wolf": [
        (
            "qi_refining",
            "Qi Refinement",
            "Qi Refinement stage look: slightly fluffy wolf ears, very faint wolf markings on the cheeks, a plain collar, eyes with youthful sharpness. "
            "Do not add extra runes or large-area light effects.",
        ),
        (
            "foundation",
            "Foundation Establishment",
            "Foundation Establishment stage look: clearer wolf-ear contours, steadier wolf markings on the cheeks, calm and sharp eyes, slightly more refined hair ornaments. "
            "Only enhance the existing cool-toned highlights.",
        ),
        (
            "golden_core",
            "Golden Core",
            "Golden Core stage look: more focused pupil highlights, crisper edges on the wolf markings, stronger texture on the forehead guard or beast-fang ornaments. "
            "The existing cool light is slightly stronger but stays close to the subject.",
        ),
        (
            "nascent_soul",
            "Nascent Soul",
            "Nascent Soul stage look: calm, ethereal expression, lighter wolf ears and hair strands, clear and elegant wolf markings, softer cool-toned close-fitting light. "
            "No background moon or scenery.",
        ),
    ],
    "bird": [
        (
            "qi_refining",
            "Qi Refinement",
            "Qi Refinement stage look: plainer feather ornaments, very faint colored markings at the eye corners, a small feather crest, a light, inexperienced expression. "
            "Do not add extra runes or large-area light effects.",
        ),
        (
            "foundation",
            "Foundation Establishment",
            "Foundation Establishment stage look: clearer feather crest and ear-feather contours, steadier colored markings at the eye corners, slightly more refined feather ornaments. "
            "Only enhance the existing feather colors and close-fitting faint glow.",
        ),
        (
            "golden_core",
            "Golden Core",
            "Golden Core stage look: brighter pupil highlights, clearer layering of the feather crest, colorful feather ornaments with a fine metallic sheen. "
            "Existing colored markings are more condensed; do not add background wings.",
        ),
        (
            "nascent_soul",
            "Nascent Soul",
            "Nascent Soul stage look: ethereal, airy expression, finer and softer feather ornaments, hair strands and feather crest faintly glowing. "
            "Keep only a clear close-fitting light; no spread wings or background effects.",
        ),
    ],
    "snake": [
        (
            "qi_refining",
            "Qi Refinement",
            "Qi Refinement stage look: slit pupils with a weak sheen, very faint scale patterns, simple snake-shaped ornaments, a slightly cold, inexperienced expression. "
            "Do not add extra runes or large-area light effects.",
        ),
        (
            "foundation",
            "Foundation Establishment",
            "Foundation Establishment stage look: clearer slit pupils, steadier fine scale patterns, slightly more refined snake-shaped earrings, calmer eyes. "
            "Only enhance the existing cool-toned faint glow.",
        ),
        (
            "golden_core",
            "Golden Core",
            "Golden Core stage look: sharper slit-pupil highlights, crisper edges on the scale patterns, snake-shaped ornaments with a fine metallic texture. "
            "Existing eyeshadow and scale sheen are more visible but restrained.",
        ),
        (
            "nascent_soul",
            "Nascent Soul",
            "Nascent Soul stage look: ethereal, mysterious expression, clear slit pupils, elegant and delicate scale patterns, hair strands with a faint cool light. "
            "No background snake silhouettes or large areas of mist.",
        ),
    ],
    "turtle": [
        (
            "qi_refining",
            "Qi Refinement",
            "Qi Refinement stage look: plainer tortoiseshell patterns, simple jade ornaments, gentle and inexperienced eyes, a thick, plain collar. "
            "Do not add extra runes or large-area light effects.",
        ),
        (
            "foundation",
            "Foundation Establishment",
            "Foundation Establishment stage look: clearer tortoiseshell patterns, slightly more refined jade ornaments, calm eyes, neater collar texture. "
            "Only enhance the existing teal or jade-colored faint glow.",
        ),
        (
            "golden_core",
            "Golden Core",
            "Golden Core stage look: steadier pupil highlights, crisper edges on the tortoiseshell patterns, jade ornaments with a warm, smooth luster. "
            "The collar may have small geometric patterns; solid and weighty overall but not exaggerated.",
        ),
        (
            "nascent_soul",
            "Nascent Soul",
            "Nascent Soul stage look: peaceful, ethereal expression, elegant and delicate tortoiseshell patterns, more translucent jade ornaments, a steady soft close-fitting glow. "
            "No background magic circles or large halos.",
        ),
    ],
}

SPECIES_NAMES = {
    "fox": "Fox",
    "wolf": "Wolf",
    "bird": "Bird",
    "snake": "Snake",
    "turtle": "Turtle",
}

FEMALE_SPECIES_AFFIXES = {
    "fox": [
        "Fox yao traits, soft platinum-blonde long hair, fluffy fox ears, amber eyes, red makeup at the eye corners, fine gold bell hair ornament, sly and sweet expression.",
        "Fox yao traits, crimson curly hair, deep red fox ears, pale gold slit pupils, peach blossom forehead mark, fluffy earrings, charming smile.",
        "Fox yao traits, ink-black long hair, silver-tipped fox ears, blue-violet eyes, white jade fox-shaped hairpin, cool and mysterious expression.",
        "Fox yao traits, light tea-brown double hair loops, milky white fox ears, honey-colored eyes, red string hair ornament with small bells, lively and playful expression.",
        "Fox yao traits, silver-to-pink gradient long hair, pinkish-white fox ears, rose-gold eyes, fine beaded tassel earrings, gentle and radiant features.",
        "Fox yao traits, blue-gray high ponytail, gray-blue fox ears, pale violet eyes, green jade fox-tail-shaped hair clip, clever and alert expression.",
        "Fox yao traits, chestnut fluffy short hair, russet fox ears, orange-gold eyes, small copper-coin earrings, lively and cheerful smile.",
        "Fox yao traits, moon-white long straight hair, silver-white fox ears, icy blue eyes, white silk hair ribbon and small fox mask ornament, elegant and aloof air.",
        "Fox yao traits, long black hair with gold streaks, black-gold fox ears, amber slit pupils, gold filigree fox-pattern forehead ornament, noble and composed expression.",
    ],
    "wolf": [
        "Wolf yao traits, ash-gray short hair, pointed wolf ears, icy blue eyes, pale wolf markings on the cheeks, black-silver forehead guard, sharp eyes.",
        "Wolf yao traits, dark blue wolf-cut hair, silver-gray wolf ears, golden pupils, beast-fang earrings, wild and bold features.",
        "Wolf yao traits, snow-white long braid, white wolf ears, light blue eyes, crescent moon mark on the forehead, calm and chilly expression.",
        "Wolf yao traits, smoky black shoulder-length hair, black-gray wolf ears, silver eyes, leather-cord beast-fang hair pendant, cold and vigilant expression.",
        "Wolf yao traits, light brown short curly hair, brown wolf ears, amber eyes, fluffy collar trim, hearty and wild smile.",
        "Wolf yao traits, silver-blue high-tied hair, blue-gray wolf ears, very pale blue pupils, thin iron-ring earrings, sharp yet restrained features.",
        "Wolf yao traits, short hair with dark red streaks, dark gray wolf ears, red-gold eyes, black headband, untamed and fierce expression.",
        "Wolf yao traits, misty white fluffy short hair, white-gray wolf ears, pale gray eyes, small bone-chip hair ornaments, quiet and solitary air.",
        "Wolf yao traits, blue-black long hair, ink-colored wolf ears, green-gold eyes, dark wolf markings on the side of the face, composed and dangerous expression.",
    ],
    "bird": [
        "Bird yao traits, peacock-blue long hair, feathered ear plumes, emerald-gold eyes, colorful feather dangling hairpin, colorful markings at the eye corners, proud smile.",
        "Bird yao traits, white-feathered short hair, small feather crest, pale gold eyes, feather earrings, light and bright expression.",
        "Bird yao traits, jet-black long hair, crow-feather hair ornament, dark violet eyes, black feather earrings, cold and quiet beauty.",
        "Bird yao traits, vermilion long hair, red ear plumes, gold-orange eyes, red feather hairpin, passionate and cheerful expression.",
        "Bird yao traits, pale cyan short hair, teal ear plumes, aqua-blue eyes, fine feather hair clips, fresh and nimble air.",
        "Bird yao traits, golden-brown curly hair, sparrow-feather earrings, amber eyes, pale gold markings at the eye corners, clever and quick-witted smile.",
        "Bird yao traits, silver-gray long hair, crane-feather hair crown, pale gray-blue eyes, white feather earrings, elegant and serene expression.",
        "Bird yao traits, violet-to-blue gradient hair, long slender colorful feather earrings, blue-violet eyes, colorful forehead feathers, dreamy and soft expression.",
        "Bird yao traits, dark green updo, kingfisher-feather hairpin, jade-green eyes, fine emerald markings at the eye corners, dignified and proud expression.",
    ],
    "snake": [
        "Snake yao traits, dark green long straight hair, golden slit pupils, fine scale earrings, teal eyeshadow at the eye corners, dangerously elegant smile.",
        "Snake yao traits, silver-white updo, pale cyan slit pupils, tiny scale patterns at the corners of the forehead, transparent jade hairpin, cold expression.",
        "Snake yao traits, purple-black curly hair, dark gold slit pupils, snake-shaped earrings, purplish lips, languid and mysterious expression.",
        "Snake yao traits, teal-blue long hair, jade-green slit pupils, tiny green scales on the side of the face, water-drop earrings, cool yet supple expression.",
        "Snake yao traits, dark tea-brown low ponytail, amber slit pupils, light brown scale patterns, copper snake hair clasp, calm and shrewd expression.",
        "Snake yao traits, light purple short hair, pale gold slit pupils, fine purple lines at the eye corners, silver snake-shaped hair clip, sly smile.",
        "Snake yao traits, pale long hair, icy cyan slit pupils, fine-scale forehead ornament, white jade snake-pattern earrings, eerie and cold air.",
        "Snake yao traits, reddish-brown curly hair, red-gold slit pupils, small red scale markings on the cheeks, red copper earrings, fiery and dangerous expression.",
        "Snake yao traits, peacock-green updo, emerald-gold slit pupils, fine scale patterns on the side of the neck, jade snake-shaped hairpin, gorgeous and mysterious expression.",
    ],
    "turtle": [
        "Turtle yao traits, dark brown updo, gentle round eyes, tortoiseshell-pattern hairpin, green jade earrings, calm and soft expression.",
        "Turtle yao traits, dark green short hair, light green eyes, tortoiseshell-pattern forehead ornament, heavy jade hair clasp, calm expression.",
        "Turtle yao traits, gray-teal long hair, pale gold eyes, deep black tortoiseshell-shaped hair crown, small teal markings on the cheeks, steady and tranquil aura.",
        "Turtle yao traits, light brown double buns, warm dark eyes, pale teal tortoiseshell hair clip, round jade earrings, well-behaved and steady expression.",
        "Turtle yao traits, blue-black long straight hair, jade-green eyes, tortoiseshell-pattern jade hairpin, thick collar, quiet and dependable expression.",
        "Turtle yao traits, off-white short hair, pale brown eyes, white jade tortoiseshell forehead ornament, teal cord hair band, simple and gentle air.",
        "Turtle yao traits, dark gold updo, golden-brown eyes, black-gold tortoiseshell hair crown, small geometric patterns on the side of the face, dignified and steady expression.",
        "Turtle yao traits, pine-green long braid, lake-green eyes, bronze tortoiseshell earrings, small jade hair clasp, slow-to-warm and focused expression.",
        "Turtle yao traits, gray-white high bun, pale cyan eyes, black jade tortoiseshell hairpin, heavy teal-patterned collar, archaic and tranquil air.",
    ],
}

MALE_SPECIES_AFFIXES = {
    "fox": [
        "Fox yao traits, platinum-blonde long hair, fluffy fox ears, amber eyes, red markings at the eye corners, fine gold ear studs, sly and handsome expression.",
        "Fox yao traits, crimson short hair, deep red fox ears, pale gold slit pupils, peach blossom forehead mark, fluffy collar, slight smirk.",
        "Fox yao traits, ink-black tied-up hair, silver-tipped fox ears, blue-violet eyes, white jade fox-shaped hair crown, cool and mysterious expression.",
        "Fox yao traits, light tea-brown short hair, milky white fox ears, honey-colored eyes, red string earrings with small bells, clever and friendly expression.",
        "Fox yao traits, silver-to-pink gradient long hair, pinkish-white fox ears, rose-gold eyes, fine beaded tassel hair clasp, gentle and handsome features.",
        "Fox yao traits, blue-gray high-tied hair, gray-blue fox ears, pale violet eyes, green jade fox-pattern hair crown, clever and alert expression.",
        "Fox yao traits, chestnut fluffy short hair, russet fox ears, orange-gold eyes, small copper-coin earrings, carefree and cheerful smile.",
        "Fox yao traits, moon-white long straight hair, silver-white fox ears, icy blue eyes, hair tied with white silk and a small fox mask ornament, elegant and aloof air.",
        "Fox yao traits, long black hair with gold streaks, black-gold fox ears, amber slit pupils, gold filigree fox-pattern forehead ornament, noble and composed expression.",
    ],
    "wolf": [
        "Wolf yao traits, ash-gray short hair, pointed wolf ears, icy blue eyes, pale wolf markings on the cheeks, black-silver forehead guard, piercing eyes.",
        "Wolf yao traits, dark blue wolf-cut hair, silver-gray wolf ears, golden pupils, beast-fang earrings, thick brows, wild and bold.",
        "Wolf yao traits, snow-white long braid, white wolf ears, light blue eyes, crescent moon mark on the forehead, calm and chilly expression.",
        "Wolf yao traits, smoky black short hair, black-gray wolf ears, silver eyes, leather-cord beast-fang hair pendant, cold and vigilant expression.",
        "Wolf yao traits, light brown short curly hair, brown wolf ears, amber eyes, fluffy collar trim, hearty and wild smile.",
        "Wolf yao traits, silver-blue high-tied hair, blue-gray wolf ears, very pale blue pupils, thin iron-ring earrings, sharp yet restrained features.",
        "Wolf yao traits, short hair with dark red streaks, dark gray wolf ears, red-gold eyes, black headband, untamed and fierce expression.",
        "Wolf yao traits, misty white fluffy short hair, white-gray wolf ears, pale gray eyes, small bone-chip hair ornaments, quiet and solitary air.",
        "Wolf yao traits, blue-black long hair, ink-colored wolf ears, green-gold eyes, dark wolf markings on the side of the face, composed and dangerous expression.",
    ],
    "bird": [
        "Bird yao traits, peacock-blue long hair, feathered ear plumes, emerald-gold eyes, colorful feather hair crown, colorful markings at the eye corners, proud smile.",
        "Bird yao traits, white-feathered short hair, small feather crest, pale gold eyes, feather earrings, light and bright expression.",
        "Bird yao traits, jet-black long hair, crow-feather hair ornament, dark violet eyes, black feather earrings, stern and quiet expression.",
        "Bird yao traits, vermilion long hair, red ear plumes, gold-orange eyes, red feather hair crown, passionate and cheerful expression.",
        "Bird yao traits, pale cyan short hair, teal ear plumes, aqua-blue eyes, fine feather hair clips, fresh and nimble air.",
        "Bird yao traits, golden-brown curly hair, sparrow-feather earrings, amber eyes, pale gold markings at the eye corners, clever and quick-witted smile.",
        "Bird yao traits, silver-gray long hair, crane-feather hair crown, pale gray-blue eyes, white feather earrings, elegant and serene expression.",
        "Bird yao traits, violet-to-blue gradient hair, long slender colorful feather earrings, blue-violet eyes, colorful forehead feathers, dreamy and soft expression.",
        "Bird yao traits, dark green tied-up hair, kingfisher-feather hair crown, jade-green eyes, fine emerald markings at the eye corners, dignified and proud expression.",
    ],
    "snake": [
        "Snake yao traits, dark green long straight hair, golden slit pupils, fine scale earrings, teal eyeshadow at the eye corners, dangerously elegant smile.",
        "Snake yao traits, silver-white tied-up hair, pale cyan slit pupils, tiny scale patterns at the corners of the forehead, transparent jade crown, cold expression.",
        "Snake yao traits, purple-black curly hair, dark gold slit pupils, snake-shaped earrings, purplish lips, languid and mysterious expression.",
        "Snake yao traits, teal-blue long hair, jade-green slit pupils, tiny green scales on the side of the face, water-drop earrings, cool yet supple expression.",
        "Snake yao traits, dark tea-brown low-tied hair, amber slit pupils, light brown scale patterns, copper snake hair clasp, calm and shrewd expression.",
        "Snake yao traits, light purple short hair, pale gold slit pupils, fine purple lines at the eye corners, silver snake-shaped hair clip, sly smile.",
        "Snake yao traits, pale long hair, icy cyan slit pupils, fine-scale forehead ornament, white jade snake-pattern earrings, eerie and cold air.",
        "Snake yao traits, reddish-brown curly hair, red-gold slit pupils, small red scale markings on the cheeks, red copper earrings, fiery and dangerous expression.",
        "Snake yao traits, peacock-green tied-up hair, emerald-gold slit pupils, fine scale patterns on the side of the neck, jade snake-shaped hair crown, gorgeous and mysterious expression.",
    ],
    "turtle": [
        "Turtle yao traits, dark brown tied-up hair, gentle round eyes, tortoiseshell-pattern hairpin, green jade earrings, calm and soft expression.",
        "Turtle yao traits, dark green short hair, light green eyes, tortoiseshell-pattern forehead ornament, heavy jade hair clasp, calm expression.",
        "Turtle yao traits, gray-teal long hair, pale gold eyes, deep black tortoiseshell-shaped hair crown, small teal markings on the cheeks, steady and tranquil expression.",
        "Turtle yao traits, light brown tied-up hair, warm dark eyes, pale teal tortoiseshell hair clip, round jade earrings, modest and steady expression.",
        "Turtle yao traits, blue-black long straight hair, jade-green eyes, tortoiseshell-pattern jade hairpin, thick collar, quiet and dependable expression.",
        "Turtle yao traits, off-white short hair, pale brown eyes, white jade tortoiseshell forehead ornament, teal cord hair band, simple and gentle air.",
        "Turtle yao traits, dark gold tied-up hair, golden-brown eyes, black-gold tortoiseshell hair crown, small geometric patterns on the side of the face, dignified and steady expression.",
        "Turtle yao traits, pine-green long braid, lake-green eyes, bronze tortoiseshell earrings, small jade hair clasp, slow-to-warm and focused expression.",
        "Turtle yao traits, gray-white high-tied hair, pale cyan eyes, black jade tortoiseshell hairpin, heavy teal-patterned collar, archaic and tranquil air.",
    ],
}


@dataclass(frozen=True)
class YaoguaiAvatarPromptRecord:
    species_slug: str
    species_name: str
    gender: str
    index: int
    realm_slug: str
    realm_name: str
    appearance_prompt: str
    realm_prompt: str
    prompt: str

    @property
    def filename_stem(self) -> str:
        return f"{self.species_slug}_{self.gender}_{self.index:02d}_{self.realm_slug}"


def yaoguai_avatar_prompt_records(
    *,
    species_slugs: list[str] | None = None,
    genders: list[str] | None = None,
    realm_slugs: list[str] | None = None,
) -> list[YaoguaiAvatarPromptRecord]:
    selected_species = species_slugs or list(SPECIES_NAMES)
    selected_genders = genders or ["female", "male"]
    requested_realm_slugs = set(realm_slugs or YAOGUAI_REALM_SLUGS)

    unknown_species = set(selected_species) - set(SPECIES_NAMES)
    if unknown_species:
        raise ValueError(f"unknown species slug: {', '.join(sorted(unknown_species))}")

    unknown_genders = set(selected_genders) - {"female", "male"}
    if unknown_genders:
        raise ValueError(f"unknown gender: {', '.join(sorted(unknown_genders))}")

    missing_realms = requested_realm_slugs - set(YAOGUAI_REALM_SLUGS)
    if missing_realms:
        raise ValueError(f"unknown realm slug: {', '.join(sorted(missing_realms))}")

    records: list[YaoguaiAvatarPromptRecord] = []
    for species_slug in selected_species:
        for gender in selected_genders:
            prompt_base = (
                FEMALE_YAOGUAI_PROMPT_BASE
                if gender == "female"
                else MALE_YAOGUAI_PROMPT_BASE
            )
            affixes = (
                FEMALE_SPECIES_AFFIXES[species_slug]
                if gender == "female"
                else MALE_SPECIES_AFFIXES[species_slug]
            )
            selected_realms = [
                realm
                for realm in SPECIES_REALMS[species_slug]
                if realm[0] in requested_realm_slugs
            ]
            for index, affix in enumerate(affixes, start=1):
                for realm_slug, realm_name, realm_prompt in selected_realms:
                    records.append(
                        YaoguaiAvatarPromptRecord(
                            species_slug=species_slug,
                            species_name=SPECIES_NAMES[species_slug],
                            gender=gender,
                            index=index,
                            realm_slug=realm_slug,
                            realm_name=realm_name,
                            appearance_prompt=affix,
                            realm_prompt=realm_prompt,
                            prompt=f"{prompt_base} {affix} {realm_prompt}",
                        )
                    )
    return records
