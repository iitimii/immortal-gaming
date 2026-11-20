SECT_PROMPT_BASE = (
    "A pixelated xianxia sect scene image, extremely pixelated, strongly grainy, thick line outlines, "
    "minimalist, anime-style manga image. "
)

SECT_PROMPTS = [
    ("wondrous_transformation_sect", "Elegant gardens, string and wind instruments, a hundred flowers in full bloom, faint musical runes, full of spring."),
    ("returning_mystery_sect", "Mist-shrouded mountain peaks, countless layered formation light arrays, dim and obscure, deeply mysterious."),
    ("sleepless_city", "Dazzling aurora, city walls of ten-thousand-year ice, shimmering streams of light, dreamlike, a city that never sleeps."),
    ("heavenly_vigor_sect", "Majestic peaks, purple qi arriving from the east, a pillar of righteous light soaring into the sky, visions of resounding recitation."),
    ("demon_devouring_sect", "Treacherous mountain ranges, pervading blood mist, jagged rocks, piles of white bones, wild and gory."),
]


def sect_prompts() -> list[tuple[str, str]]:
    return [(name, SECT_PROMPT_BASE + affix) for name, affix in SECT_PROMPTS]
