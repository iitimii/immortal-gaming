from __future__ import annotations

from typing import Any

from .models import EntityRewrite, RewriteJob, WorldLoreRewriteDraft
from .validation import ValidatedJobResult, draft_from_validated_job, validate_job_result


def build_fallback_style_guide(lore_text: str) -> dict[str, Any]:
    tone = _tone_prefix(lore_text)
    return {
        "world_tone": tone or "this run's world lore",
        "naming_rules": [
            "Names should translate the world lore's mood instead of pasting keywords onto old names",
            "Avoid reusing the same root word",
        ],
        "forbidden_patterns": ["Do not write numeric bonuses", "Do not write system mechanics", "Do not add mechanical prefixes"],
        "description_style": "Concise, concrete, and visual",
    }


def fallback_job(job: RewriteJob) -> WorldLoreRewriteDraft:
    result: dict[str, Any] = {
        job.result_field: [_fallback_entity(entity, job.entity_label, job.lore_text) for entity in job.entities],
    }
    if job.paired_entities:
        result[job.paired_result_field] = [
            _fallback_entity(entity, job.paired_entity_label, job.lore_text)
            for entity in job.paired_entities
        ]
    validated = validate_job_result(job, result, source="fallback")
    return draft_from_validated_job(job, validated)


def _fallback_entity(entity: dict[str, Any], label: str, lore_text: str) -> dict[str, Any]:
    entity_id = int(entity["id"])
    old_name = str(entity.get("name") or f"{label} {entity_id}").strip()
    motif = _fallback_motif(lore_text, entity_id)
    name = _blend_name(old_name, motif)
    if len(name) > 60:
        name = name[:60].rstrip()

    desc = (
        f"{name} still keeps its old form and purpose, yet the order of a new age has quietly rewritten it. "
        f"Local rumor ties it to the {motif}, lending its familiar history a heavier, more tangible air."
    )
    return {
        "id": entity_id,
        "name": name,
        "desc": desc,
    }


# ASCII and full-width (\uff0c \u3002 \uff1b \u3001 \uff01 \uff1f) separators
_TONE_SEPARATORS = ",.;:!?\uff0c\u3002\uff1b\u3001\uff01\uff1f\n\r\t "


def _tone_prefix(lore_text: str) -> str:
    text = str(lore_text or "").strip()
    for char in _TONE_SEPARATORS:
        text = text.replace(char, " ")
    for part in text.split(" "):
        part = part.strip()
        if part.isalpha() and 3 <= len(part) <= 12:
            return part.capitalize()
    return "New Era"


def _fallback_motif(lore_text: str, entity_id: int) -> str:
    text = str(lore_text or "")
    lowered = text.lower()
    if any(keyword in lowered for keyword in ("overtime", "office", "shift", "workplace")):
        motifs = ["Water Clock", "Lamp Ledger", "Night Roster", "Urgent Summons", "Weary Bell", "Paperwork"]
        return motifs[entity_id % len(motifs)]
    if any(keyword in lowered for keyword in ("dharma ending", "dharma-ending", "ending age", "end of dharma")):
        motifs = ["Remnant Spirit", "Ashen Vein", "Broken Glow", "Withered Tide", "Derelict Furnace", "Cold Star"]
        return motifs[entity_id % len(motifs)]
    if any(keyword in lowered for keyword in ("demon", "yao", "monster", "beast")):
        motifs = ["Strange Sigil", "Beast Moon", "Spirit Molt", "Wild Blood", "Hundred Bones", "Hidden Scale"]
        return motifs[entity_id % len(motifs)]
    return _tone_prefix(text)


def _blend_name(old_name: str, motif: str) -> str:
    if not motif:
        return old_name
    words = old_name.split()
    if len(words) <= 1:
        return f"{motif} {old_name}"
    midpoint = max(1, len(words) // 2)
    return " ".join([*words[:midpoint], motif, *words[midpoint:]])
