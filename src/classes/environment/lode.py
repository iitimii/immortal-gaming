from dataclasses import dataclass, field
from typing import Optional

from src.utils.df import game_configs, get_str, get_int, get_list_int
from src.classes.material import Material, materials_by_id
from src.systems.cultivation import Realm

@dataclass
class Lode:
    """
    Ore vein
    """
    id: int
    name: str
    desc: str
    realm: Realm
    material_ids: list[int] = field(default_factory=list)  # Item IDs for this ore vein
    
    # These fields are set in __post_init__
    materials: list[Material] = field(init=False, default_factory=list)  # Item instances for this ore vein
    
    def __post_init__(self):
        """Initialize item instances."""
        for material_id in self.material_ids:
            if material_id in materials_by_id:
                self.materials.append(materials_by_id[material_id])

    def __hash__(self) -> int:
        return hash(self.id)

    def __str__(self) -> str:
        return self.name
    
    def get_info(self) -> str:
        """
        Get the ore vein's detailed info
        """
        from src.i18n import t
        # Use a format-string msgid
        base_info = t("[{name}] ({realm})", name=self.name, realm=str(self.realm))
        info_parts = [base_info, self.desc]
        
        if self.materials:
            material_names = [material.name for material in self.materials]
            materials_str = t("comma_separator").join(material_names)
            info_parts.append(t("Drops: {materials}", materials=materials_str))
        
        return " - ".join(info_parts)

    def get_structured_info(self) -> dict:
        materials_info = [material.get_structured_info() for material in self.materials]
        return {
            "id": str(self.id),
            "name": self.name,
            "desc": self.desc,
            "grade": str(self.realm),
            "drops": materials_info,
            "type": "lode"
        }

def _load_lodes() -> tuple[dict[int, Lode], dict[str, Lode]]:
    """Load lode data from the config table."""
    lodes_by_id: dict[int, Lode] = {}
    lodes_by_name: dict[str, Lode] = {}
    
    # Check that the config exists to avoid initialization errors
    if "lode" not in game_configs:
        return {}, {}
    
    lode_df = game_configs["lode"]
    for row in lode_df:
        material_ids_list = get_list_int(row, "material_ids")
            
        lode = Lode(
            id=get_int(row, "id"),
            name=get_str(row, "name"),
            desc=get_str(row, "desc"),
            realm=Realm.from_id(get_int(row, "stage_id")),
            material_ids=material_ids_list
        )
        lodes_by_id[lode.id] = lode
        lodes_by_name[lode.name] = lode
    
    return lodes_by_id, lodes_by_name

lodes_by_id: dict[int, Lode] = {}
lodes_by_name: dict[str, Lode] = {}

def reload():
    """Reload data while preserving the global dict references."""
    new_id, new_name = _load_lodes()
    
    lodes_by_id.clear()
    lodes_by_id.update(new_id)
    
    lodes_by_name.clear()
    lodes_by_name.update(new_name)
    
    # Update ORE_MATERIAL_IDS
    global ORE_MATERIAL_IDS
    ORE_MATERIAL_IDS = {material_id for lode in lodes_by_id.values() for material_id in lode.material_ids}

# Run once at module import
reload()
