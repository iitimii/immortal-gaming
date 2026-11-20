from dataclasses import dataclass, field
from typing import Optional

from src.utils.df import game_configs, get_str, get_int, get_list_int
from src.utils.config import CONFIG
from src.classes.material import Material, materials_by_id
from src.systems.cultivation import Realm

@dataclass
class Plant:
    """
    Plant
    """
    id: int
    name: str
    desc: str
    realm: Realm
    material_ids: list[int] = field(default_factory=list)  # Item IDs for this plant
    
    # These fields are set in __post_init__
    materials: list[Material] = field(init=False, default_factory=list)  # Item instances for this plant
    
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
        Get the plant's detailed info, including name, description, realm and materials
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
            "type": "plant"
        }

def _load_plants() -> tuple[dict[int, Plant], dict[str, Plant]]:
    """Load plant data from the config table."""
    plants_by_id: dict[int, Plant] = {}
    plants_by_name: dict[str, Plant] = {}
    
    plant_df = game_configs["plant"]
    for row in plant_df:
        material_ids_list = get_list_int(row, "material_ids")
            
        plant = Plant(
            id=get_int(row, "id"),
            name=get_str(row, "name"),
            desc=get_str(row, "desc"),
            realm=Realm.from_id(get_int(row, "stage_id")),
            material_ids=material_ids_list
        )
        plants_by_id[plant.id] = plant
        plants_by_name[plant.name] = plant
    
    return plants_by_id, plants_by_name

plants_by_id: dict[int, Plant] = {}
plants_by_name: dict[str, Plant] = {}

def reload():
    """Reload data while preserving the global dict references."""
    new_id, new_name = _load_plants()
    
    plants_by_id.clear()
    plants_by_id.update(new_id)
    
    plants_by_name.clear()
    plants_by_name.update(new_name)

# Run once at module import
reload()
