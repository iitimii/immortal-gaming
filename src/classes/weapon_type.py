from enum import Enum


class WeaponType(Enum):
    """
    Weapon type enum
    """
    SWORD = "SWORD"
    SABER = "SABER"
    SPEAR = "SPEAR"
    STAFF = "STAFF"
    FAN = "FAN"
    WHIP = "WHIP"
    ZITHER = "ZITHER"
    FLUTE = "FLUTE"
    HIDDEN_WEAPON = "HIDDEN_WEAPON"
    
    def __str__(self) -> str:
        from src.i18n import t
        return t(weapon_type_msg_ids.get(self, self.value))

    @staticmethod
    def from_str(s: str) -> "WeaponType":
        s = str(s).strip().replace(" ", "_").upper()
        mapping = {
            "SWORD": "SWORD",
            "SABER": "SABER",
            "SPEAR": "SPEAR",
            "STAFF": "STAFF",
            "FAN": "FAN",
            "WHIP": "WHIP",
            "ZITHER": "ZITHER",
            "FLUTE": "FLUTE",
            "HIDDEN_WEAPON": "HIDDEN_WEAPON", "HIDDEN WEAPON": "HIDDEN_WEAPON"
        }
        type_id = mapping.get(s, "SWORD")
        return WeaponType(type_id)


weapon_type_msg_ids = {
    WeaponType.SWORD: "sword",
    WeaponType.SABER: "saber",
    WeaponType.SPEAR: "spear",
    WeaponType.STAFF: "staff",
    WeaponType.FAN: "fan",
    WeaponType.WHIP: "whip",
    WeaponType.ZITHER: "zither",
    WeaponType.FLUTE: "flute",
    WeaponType.HIDDEN_WEAPON: "hidden_weapon",
}

