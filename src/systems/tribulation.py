"""
Heavenly tribulation system.
Manages the tribulation types, descriptions and selection logic used during breakthroughs.
"""
from __future__ import annotations
import random
from typing import TYPE_CHECKING, Optional
from dataclasses import dataclass

if TYPE_CHECKING:
    from src.classes.core.avatar import Avatar

from src.i18n import t
from src.classes.relation.relation import NumericRelation, Relation
from src.classes.relation.relations import get_live_related_avatars, iter_live_relation_items

TRIBULATION_DISPLAY_MSGIDS = {
    "inner_demon": "tribulation_inner_demon",
    "lightning": "tribulation_lightning_tribulation",
    "body": "tribulation_body_reforging",
    "vengeance": "tribulation_vengeance",
    "love": "tribulation_love_tribulation",
    "solar_force": "tribulation_solar_force",
    "thunderflame": "tribulation_thunderflame",
    "windstorm": "tribulation_wind_disaster",
    "nether_prison": "tribulation_nether_prison",
    "demonic": "tribulation_demonic_tribulation",
}


@dataclass
class TribulationType:
    """Tribulation type definition."""
    name: str  # Tribulation id
    description: str  # Tribulation description (used as a hint for story generation)
    requires_other_avatar: bool = False  # Whether another avatar must be involved
    relation_type: Optional[Relation] = None  # Required relation type


# Tribulation type definitions
TRIBULATION_TYPES = {
    "inner_demon": TribulationType(
        name="inner_demon",
        description=(
            "Thoughts surge and ebb; self-doubt wrestles with obsession, silent without yet clamorous within. "
            "Deep in the Dao heart, old doubts and future uncertainty intertwine, and a single errant thought "
            "can plunge one into the abyss of the inner demon."
        ),
        requires_other_avatar=False
    ),
    "lightning": TribulationType(
        name="lightning",
        description=(
            "Heaven's might surges like a tide; lightning congeals into patterns that crush bone, blood and "
            "divine sense. Purple thunder falls from the nine heavens, every bolt a test from heaven and earth, "
            "and the slightest misstep means destruction of body and spirit."
        ),
        requires_other_avatar=False
    ),
    "body": TribulationType(
        name="body",
        description=(
            "Sinew, bone, skin and membrane are remade; true qi grinds the meridians, and pain arrives together "
            "with rebirth. The body is a furnace, every inch of flesh tempered in raging fire; only by breaking "
            "can one stand anew, only through utmost pain can one be reborn."
        ),
        requires_other_avatar=False
    ),
    "vengeance": TribulationType(
        name="vengeance",
        description=(
            "Old grudges with an enemy refuse to fade; the gleam of blades echoes in the heart, and a single "
            "thought can rewrite karma. Karmic threads entangle and old hatreds linger; the moment of breakthrough "
            "is the moment of karmic reckoning."
        ),
        requires_other_avatar=True,
        relation_type=None
    ),
    "love": TribulationType(
        name="love",
        description=(
            "Tenderness is a blade; parting is unbearable, and the mind is drawn back to the warmth of the mortal "
            "world. Threads of affection bind tight, impossible to cut and only more tangled when pulled; a single "
            "attachment can lead to eternal ruin."
        ),
        requires_other_avatar=True,
        relation_type=Relation.IS_LOVER_OF
    ),
    "solar_force": TribulationType(
        name="solar_force",
        description=(
            "The sun blazes; heaven and earth turn red and white, and the solar gale cuts like white-gold flame. "
            "Righteous force scours impurity with fierce, direct strikes; too much yang and one shatters. It peaks "
            "at noon, its light searing the mind, and the danger of meridians bursting from dryness is ever present."
        ),
        requires_other_avatar=False
    ),
    "thunderflame": TribulationType(
        name="thunderflame",
        description=(
            "Seas of cloud pile layer upon layer with purple lightning lurking within; fire is born of thunder and "
            "thunder gestates in fire. External assault and internal refinement must move in step, testing soul and "
            "meridians at once. A sea of thunder looms overhead and karmic heavenly fire burns away cause and effect; "
            "in an instant lies the line between life and death."
        ),
        requires_other_avatar=False
    ),
    "windstorm": TribulationType(
        name="windstorm",
        description=(
            "In a windless place a faint hum rises first; then gale winds snap bone, the void tears, and "
            "spirit-devouring winds erode. The wind tunnels resonate like a saw, and the slightest slip in footing "
            "or posture tears the flesh open and strips away the protective dharma form."
        ),
        requires_other_avatar=False
    ),
    "nether_prison": TribulationType(
        name="nether_prison",
        description=(
            "The temperature plunges, black frost creeps upward, wronged souls press in, and a frozen hell shackles "
            "the body. Six paths of illusory punishment and yin fire that lights the bones, resting on four pillars: "
            "karma, dread, regret and attachment. Good and evil karma take the stage, and the judgment of the heart "
            "outweighs that of the body."
        ),
        requires_other_avatar=False
    ),
    "demonic": TribulationType(
        name="demonic",
        description=(
            "Heartbeat and spiritual sense fall out of rhythm; old desires and old hatreds awaken on their own, and "
            "the shadow of a demonic embryo forms in the sea of consciousness. Within the demon realm, desire, wrath, "
            "delusion, pride and doubt take turns probing; the integrity and coherence of the Dao heart are the core, "
            "and a single errant thought leads to qi deviation."
        ),
        requires_other_avatar=False
    ),
}


# Base prompt for story generation
STORY_PROMPT_BASE = (
    "In a classical, concise and unshowy style, depict the cultivator's state of mind and the choices they make "
    "while enduring the {calamity} tribulation, in 60-100 words."
)


class TribulationSelector:
    """Tribulation selector: picks a suitable tribulation based on the cultivator's state."""
    
    @staticmethod
    def choose_tribulation(avatar: Avatar) -> str:
        """
        Choose a tribulation type based on the cultivator's realm, relations, etc.
        
        Args:
            avatar: The cultivator undergoing the tribulation
            
        Returns:
            Tribulation id
        """
        # Base tribulation pool (no other avatar required)
        base_tribulations = [
            "inner_demon", "lightning", "body", "solar_force",
            "thunderflame", "windstorm", "nether_prison", "demonic",
        ]
        
        # Check for special relations that can trigger relation-based tribulations
        available_tribulations = base_tribulations.copy()
        
        rels = dict(iter_live_relation_items(avatar))
        has_enemy = any(state.last_numeric_relation == NumericRelation.ARCHENEMY for state in rels.values())
        has_lover = any(Relation.IS_LOVER_OF in state.identity_relations for state in rels.values())
        
        if has_enemy:
            available_tribulations.append("vengeance")
        if has_lover:
            available_tribulations.append("love")
        
        return random.choice(available_tribulations)
    
    @staticmethod
    def choose_related_avatar(avatar: Avatar, tribulation_name: str) -> Optional[Avatar]:
        """
        Choose a related avatar for the tribulation type (if one is needed).
        
        Args:
            avatar: The cultivator undergoing the tribulation
            tribulation_name: Tribulation id
            
        Returns:
            The related avatar, or None if not needed
        """
        tribulation = TRIBULATION_TYPES.get(tribulation_name)
        if not tribulation or not tribulation.requires_other_avatar:
            return None
        
        if tribulation_name == "vengeance":
            candidates = get_live_related_avatars(
                avatar,
                numeric_relation=NumericRelation.ARCHENEMY,
            )
        else:
            target_rel = tribulation.relation_type
            candidates = (
                get_live_related_avatars(avatar, identity_relation=target_rel)
                if target_rel is not None
                else []
            )
        
        if not candidates:
            return None
        
        return random.choice(candidates)
    
    @staticmethod
    def get_description(tribulation_name: str) -> str:
        """
        Get the description text of a tribulation.
        
        Args:
            tribulation_name: Tribulation id
            
        Returns:
            Tribulation description
        """
        tribulation = TRIBULATION_TYPES.get(tribulation_name)
        return tribulation.description if tribulation else ""

    @staticmethod
    def get_display_name(tribulation_name: str) -> str:
        """
        Get the localized tribulation name for UI/event display.

        Internally the stable ids remain the source of truth for rules and selection;
        the display layer translates them.
        """
        tribulation = TRIBULATION_TYPES.get(tribulation_name)
        raw_name = tribulation.name if tribulation else tribulation_name
        msgid = TRIBULATION_DISPLAY_MSGIDS.get(raw_name, raw_name)
        translated = t(msgid)
        return translated if translated != msgid else raw_name
    
    @staticmethod
    def get_story_prompt(tribulation_name: str) -> str:
        """
        Get the story generation prompt.
        
        Args:
            tribulation_name: Tribulation id
            
        Returns:
            The full story generation prompt
        """
        desc = TribulationSelector.get_description(tribulation_name)
        calamity = TribulationSelector.get_display_name(tribulation_name)
        prompt = STORY_PROMPT_BASE.format(calamity=calamity)
        return (prompt + (" " + desc if desc else "")).strip()
