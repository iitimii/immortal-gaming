from enum import Enum


class Alignment(Enum):
    """
    Alignment: righteous / neutral / evil.
    Values are English for code/save compatibility; __str__ returns the translated text.
    """
    RIGHTEOUS = "RIGHTEOUS"
    NEUTRAL = "NEUTRAL"
    EVIL = "EVIL"

    def __str__(self) -> str:
        from src.i18n import t
        return t(alignment_msg_ids.get(self, self.value))

    def get_info(self) -> str:
        # Short form: just the short text
        from src.i18n import t
        return t(alignment_msg_ids[self])

    def get_detailed_info(self) -> str:
        # Detailed form: short text + full description
        from src.i18n import t
        return t("{alignment}: {description}", 
                 alignment=t(alignment_msg_ids[self]), 
                 description=t(alignment_info_msg_ids[self]))

    def __hash__(self) -> int:
        return hash(self.value)

    def __eq__(self, other) -> bool:
        """
        Allows comparison with the same type or with strings:
        - Alignment: identity comparison
        - str: matches either the enum value or the translated display text (__str__)
        """
        if isinstance(other, Alignment):
            return self is other
        if isinstance(other, str):
            return other.upper() == self.value or other == str(self)
        return False

    @staticmethod
    def from_str(text: str) -> "Alignment":
        """
        Parse a string into an Alignment, accepting English aliases.
        Returns NEUTRAL when unrecognized.
        """
        t = str(text).strip().upper()
        mapping = {
            "RIGHTEOUS": "RIGHTEOUS", "RIGHT": "RIGHTEOUS",
            "NEUTRAL": "NEUTRAL", "MIDDLE": "NEUTRAL", "CENTER": "NEUTRAL",
            "EVIL": "EVIL"
        }
        align_id = mapping.get(t, "NEUTRAL")
        return Alignment(align_id)


alignment_msg_ids = {
    Alignment.RIGHTEOUS: "righteous",
    Alignment.NEUTRAL: "neutral",
    Alignment.EVIL: "evil",
}

alignment_info_msg_ids = {
    Alignment.RIGHTEOUS: "Righteous alignment follows the principles of helping the weak, maintaining order, and vanquishing evil.",
    Alignment.NEUTRAL: "Neutral alignment follows the principles of going with the flow, seeking benefit and avoiding harm, valuing self-cultivation and balance, and not easily taking sides.",
    Alignment.EVIL: "Evil alignment follows the principles of survival of the fittest, prioritizing self-interest above all, disdaining rules, and venerating power and fear. Acts ruthlessly, often resorting to murder and plunder.",
}
