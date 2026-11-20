from __future__ import annotations

from dataclasses import dataclass

AVATAR_COMMON_PROMPT_BASE = (
    "Anime manga style, slightly chibi, facing the camera head-on. "
    "Pure white background; the background must be clean, with no texture, shadow, gradient, mist, glow or border. "
    "The character is complete and centered; hair and hair ornaments must not touch the image edges; the subject has crisp edges. "
    "Pixel art style, not too much detail."
)

AVATAR_REALMS = [
    (
        "qi_refining",
        "Qi Refinement",
        "Qi Refinement stage look: overall plainer and more youthful, simplified ornaments, a plain collar, eyes with a touch of naivety. "
        "Only tone down existing visible light effects and patterns; do not add extra runes, halos or large-area effects.",
    ),
    (
        "foundation",
        "Foundation Establishment",
        "Foundation Establishment stage look: overall steadier and fresher, calmer eyes, existing hair ornaments and collar slightly more refined. "
        "Only make existing colors, patterns, accessories and close-fitting light effects clearer; do not change the main appearance elements.",
    ),
    (
        "golden_core",
        "Golden Core",
        "Golden Core stage look: overall more condensed and brighter, crisper facial features, more visible pupil highlights. "
        "Existing hair ornaments, forehead marks, eye makeup, collar or spiritual light gain finer texture; details are more refined but still restrained.",
    ),
    (
        "nascent_soul",
        "Nascent Soul",
        "Nascent Soul stage look: overall more translucent and ethereal, a quiet expression, hair strands and existing ornaments lighter and airier. "
        "Existing light effects become clear and soft, existing patterns more elegant; do not add exaggerated backgrounds or large-area effects.",
    ),
]


@dataclass(frozen=True)
class AvatarPromptRecord:
    gender: str
    index: int
    realm_slug: str
    realm_name: str
    appearance_prompt: str
    realm_prompt: str
    prompt: str

    @property
    def filename_stem(self) -> str:
        return f"{self.gender}_{self.index:03d}_{self.realm_slug}"

FEMALE_PROMPT_BASE = (
    "A xianxia female character avatar showing only the complete head, face and a little of the shoulders and neck. "
    f"{AVATAR_COMMON_PROMPT_BASE}"
)

FEMALE_AFFIXES = [
    "Ink-black long hair, clear eyes, a slight smile, white flower hairpin, pale green spiritual glow.",
    "Silver-gray curly hair, languid expression, beauty mark under the eye, crystal earrings, faint swirling mist.",
    "Wine-red short hair, heroic brows and eyes, sharp sword-like brows sweeping to the temples, golden forehead ornament, flame-pattern eyeshadow.",
    "Light purple twin tails, smiling crescent eyes, bell hair ribbon, slightly flushed cheeks, lively spiritual glow.",
    "Cyan long straight hair, cool aloof face, indifferent expression, hair pinned up with a jade hairpin, icy blue eyes.",
    "Golden-brown wavy hair, gentle smile, pearl dangling hairpin, amber eyes, warm soft light.",
    "Deep blue updo, dignified and composed, phoenix hair crown, long narrow eyes, golden rim light.",
    "Pure white long hair, heterochromatic eyes, silver chain forehead ornament, starry spiritual sparkles, calm expression.",
    "Pink bun hairstyle, innocent smile, peach blossom hair clip, rosy cheeks, faint petal glow.",
    "Flaxen choppy hair, determined eyes, tightly pressed lips, simple hair band, light-colored shoulder collar.",
    "Orange-red long hair, radiant smile, flame-pattern forehead ornament, amber eyes, faintly glowing hair tips.",
    "Dark green braid, serene expression, wooden hairpin, light green eyes, grass-leaf hair ornament.",
    "Gray-white short hair, piercing gaze, faint gold tattoo on the left cheek, metal earrings, cool-toned shadows.",
    "Chestnut long curly hair, alluring eyes, rose hair ornament, red lips, red makeup at the eye corners.",
    "Navy blue tied-up hair, brisk and capable, black headscarf, blazing gaze, dark blue spiritual glow.",
    "Light yellow loose hair, pale complexion, plain hair band, soft faint brows and eyes, pale green glow like medicinal mist.",
    "Iridescent flowing hair, eyes shimmering with light, wreathed in clouds and mist, soft contours, glowing hair strands.",
    "Jet-black hime cut, well-behaved and quiet, silk bow, lowered eyes with a slight smile, light pink eyeshadow.",
    "Light brown updo, cute playful smile, red string hair ornament, bright round eyes, small earrings.",
    "Silver-white long braid, eyes closed in prayer, soft halo, moon-white mark between the brows, quiet expression.",
    "Deep purple straight hair, cold and proud beauty, amethyst crown, chin slightly raised, purple eye glow.",
    "Emerald double-loop buns, lively smile, jade tassels, upturned eye corners, wind-like spiritual glow.",
    "Platinum long hair, distant expression, icicle earrings, pale blue lips, frost on the hair tips.",
    "Fluffy red hair, wild eyes, bone-fang earrings, beast-pattern cheek markings, bold brows and eyes.",
    "Indigo hanging hair loops, gentle eyes, scroll-pattern hairpin, thin brows, pale gold eyes.",
    "Crimson long hair, tsundere expression, cat-ear headband, upturned eye corners, small fang.",
    "Dark blue wolf-cut short hair, sharp eyes, sword-shaped earrings, high brow bones, cool white highlights.",
    "Beige loose hair, sleepy eyes, cloud-pattern hair band, half-closed eyes, soft hair strands.",
    "Dark blue-green updo, mature and steady, auspicious cloud hairpin, kind brows and eyes, pale gold earrings.",
    "Jade-green long hair, pale complexion, deep blue will-o'-wisp eyeshadow, gloomy gaze, cold-toned spirit flames.",
    "Rose-gold long hair, sweet smile, lace hair band, pinkish-white eye glow, fine sparkles.",
    "Pitch-black long straight hair covering one eye, skull hair clip, shadowed eyes, dark purple mist.",
    "Black-to-white gradient short hair, calm expression, Go-stone earrings, taiji mark on the forehead, black-and-white spiritual glow.",
    "Lake-blue curly hair, water-drop forehead ornament, transparent earrings, gentle smile, rippling water highlights.",
    "Deep black high ponytail, red mark between the brows, small scar on the cheek, resolute gaze, dark collar.",
    "Pale gold hair with straight bangs, light-colored irises, lotus headpiece, ethereal expression, white-gold glow.",
    "Peacock-blue long hair, feather-shaped dangling hairpin, proud smile, colorful makeup at the eye corners, multicolored hair tips.",
    "Smoke-gray low ponytail, translucent veil, cold eyes, dark green misty glow.",
    "Dark red updo, black-gold hair crown, majestic phoenix eyes, deep red eyeshadow, dark gold earrings.",
    "Platinum short hair, mechanical monocle lens ornament, shrewd smile, silver hair clip.",
    "Pale green short curly hair, round-rimmed glazed-glass spectacles, focused expression, light green eyes.",
    "Purple-black double buns, talisman-paper hair ornaments, mischievous grin, purple eyeshadow.",
    "Azure long braid, snowflake hair ornament, frost on the eyelashes, calm expression, ice-crystal earrings.",
    "Copper-brown short hair, wheat-toned skin, hearty smile, animal-hide hair tie, golden-brown eyes.",
    "Long black hair with gold streaks, golden slit pupils, scale earrings, tiny gold markings at the corners of the forehead.",
    "Light pink shoulder-length hair, misty teary eyes, seashell earrings, aqua-blue eyes, pearl hair clip.",
    "Silver-blue hime cut, moon-disc mark on the forehead, calm expression, moon-white eye glow, silver hair ring.",
    "Dark purple fluffy short hair, small fang, dark-patterned hair band, impish grin, purple-black spiritual mist.",
]

MALE_PROMPT_BASE = (
    "A xianxia male character avatar showing only the complete head, face and a little of the shoulders and neck. "
    f"{AVATAR_COMMON_PROMPT_BASE}"
)

MALE_AFFIXES = [
    "Ink-black long hair, sharp sword-like brows sweeping to the temples, lightning-sharp eyes, golden crown holding the hair up, cool white highlights.",
    "Silver-white loose hair, short beard and a smile, wooden Daoist hairpin, relaxed brows and eyes, soft misty glow.",
    "Wine-red short hair, unrestrained wild eyes, a slight smirk, black jade ear stud, fiery red eye glow.",
    "Deep blue ponytail, stern cold expression, silver forehead guard, sharp gaze, icy blue highlights.",
    "Brown buzz cut, honest simple smile, coarse cloth collar, thick brows and round eyes, warm skin tone.",
    "Golden curly hair, peach-blossom eyes, folding-fan-pattern hairpin, flirtatious smile, golden earrings.",
    "Gray-white long hair, gaunt haggard face, sinister gaze, bone hair ornament, surrounded by gray mist.",
    "Pure black choppy hair, youthful face, red headband, clear eyes, slightly flushed cheeks.",
    "Purple shoulder-length hair, bewitchingly handsome, snake-shaped earrings, wicked charming smile, purple eyeshadow.",
    "Black hair half tied up, refined and courteous, jade crown, scholarly brows and eyes, pale gold eyes.",
    "Red hair spiking upward, glaring wide eyes, flame-pattern brow markings, broad brows, red rim light.",
    "Flaxen long hair, melancholy expression, plain hair band, downcast eyes, light gray shadows.",
    "Dark green short hair, glazed-glass monocle, brisk capable look, expressionless face, green reflections.",
    "Chestnut slightly wavy hair, gentle eyes, loose Daoist robe collar, faint smile, soft light.",
    "Navy blue long braid, bronze skin, totem face markings, dark pupils, blue-black hair cord.",
    "Light gray center-parted hair, gold-rimmed glasses, cold sneer, long narrow eyes, silver ear stud.",
    "Deep black long hair cascading like a waterfall, guqin-shaped hair crown, eyes closed with a faint smile, pale purple sound-wave light patterns.",
    "Jet-black slicked-back hair, scrutinizing gaze, dragon-pattern forehead ornament, broad-shouldered collar, golden eye glow.",
    "Caramel fluffy short hair, toothy grin, brocade headband, bright round eyes.",
    "Silver hair covering the eyes, half-face mask, a slight smirk, gray-blue eyes, cool-toned shadows.",
    "Deep purple long straight hair, purple-gold crown, haughty expression, chin slightly raised, amethyst earrings.",
    "Emerald short hair, grass-leaf earrings, lively eyes, sly smile, wind-like spiritual glow.",
    "Platinum long hair, jade amulet, upright gaze, white hair band, light blue eyes.",
    "Messy reddish-brown hair, stubble, wine-gourd earrings, weary smile, warm-toned shadows.",
    "Indigo tied-up hair, black cloth mask covering the face and showing only sharp eyes, dark blue highlights.",
    "Crimson short hair, scar on the cheek, hot-blooded expression, eyes as determined as a clenched fist.",
    "Dark blue wolf-cut hair, beast-fang necklace, fierce eyes, thick brows, dark collar.",
    "Off-white long curly hair, silk hair band, half-closed eyes, lazy smile, soft sheen.",
    "Dark blue-green Daoist topknot, horsetail-whisk-pattern hairpin, serious expression, long brows, blue-gray collar.",
    "Messy fluffy hair, lens-goggle forehead ornament, ingenious eyes, small metal hair clips.",
    "Rose-gold side-parted hair, peach-blossom eyes, rose ear stud, frivolous smile, pink-gold highlights.",
    "Pitch-black long hair, blood-red eyes, demonic forehead mark, dark purple mist, shadowed cheeks.",
    "Black-to-white gradient short hair, taiji mark on the forehead, calm expression, black-and-white spiritual glow.",
    "Lake-blue curly hair, water-drop earrings, gentle smile, rippling water highlights, blue eyes.",
    "Deep black high ponytail, small scar on the brow bone, resolute gaze, dark shoulder collar, red hair cord.",
    "Pale gold shoulder-length hair, lotus mark between the brows, compassionate expression, white-gold glow.",
    "Peacock-blue long hair, feather crown, proud smile, colorful makeup at the eye corners, colorful earrings.",
    "Smoke-gray low ponytail, translucent face mask, cold eyes, dark green misty glow.",
    "Dark red updo, black-gold hair crown, majestic phoenix eyes, deep red eyeshadow, dark gold earrings.",
    "Platinum short hair, mechanical monocle, shrewd smile, silver hair clip.",
    "Pale green short curly hair, round-rimmed glazed-glass spectacles, focused expression, light green eyes.",
    "Purple-black tied-up hair, talisman-paper hair band, mischievous grin, purple eyeshadow.",
    "Azure long braid, snowflake forehead ornament, frost on the eyelashes, calm expression, ice-crystal earrings.",
    "Copper-brown short hair, wheat-toned skin, hearty smile, animal-hide hair tie, golden-brown eyes.",
    "Long black hair with gold streaks, golden slit pupils, scale earrings, tiny gold markings at the corners of the forehead.",
    "Light pink shoulder-length hair, seashell earrings, gentle eyes, aqua-blue eyes, pearl hair clip.",
    "Silver-blue hime cut, moon-disc mark on the forehead, calm expression, moon-white eye glow, silver hair ring.",
    "Dark purple fluffy short hair, small fang, dark-patterned hair band, impish grin, purple-black spiritual mist.",
]

assert len(FEMALE_AFFIXES) == len(MALE_AFFIXES)


def avatar_prompts(gender: str) -> list[str]:
    if gender == "female":
        return [f"{FEMALE_PROMPT_BASE} {affix}" for affix in FEMALE_AFFIXES]
    if gender == "male":
        return [f"{MALE_PROMPT_BASE} {affix}" for affix in MALE_AFFIXES]
    raise ValueError("gender must be 'female' or 'male'")


def avatar_realm_prompt_records(
    gender: str,
    *,
    realm_slugs: list[str] | None = None,
) -> list[AvatarPromptRecord]:
    if gender == "female":
        prompt_base = FEMALE_PROMPT_BASE
        affixes = FEMALE_AFFIXES
    elif gender == "male":
        prompt_base = MALE_PROMPT_BASE
        affixes = MALE_AFFIXES
    else:
        raise ValueError("gender must be 'female' or 'male'")

    realms = AVATAR_REALMS
    if realm_slugs:
        requested = set(realm_slugs)
        realms = [realm for realm in AVATAR_REALMS if realm[0] in requested]
        missing = requested - {realm[0] for realm in realms}
        if missing:
            raise ValueError(f"unknown realm slug: {', '.join(sorted(missing))}")

    return [
        AvatarPromptRecord(
            gender=gender,
            index=index,
            realm_slug=realm_slug,
            realm_name=realm_name,
            appearance_prompt=affix,
            realm_prompt=realm_prompt,
            prompt=f"{prompt_base} {affix} {realm_prompt}",
        )
        for index, affix in enumerate(affixes, start=1)
        for realm_slug, realm_name, realm_prompt in realms
    ]
