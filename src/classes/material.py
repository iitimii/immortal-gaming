from dataclasses import dataclass

from src.classes.items.item import Item
from src.utils.df import game_configs, get_str, get_int
from src.systems.cultivation import Realm

@dataclass
class Material(Item):
    """
    Material
    """
    id: int
    name: str
    desc: str
    realm: Realm

    def instantiate(self) -> "Material":
        return self

    def __hash__(self) -> int:
        return hash(self.id)

    def __str__(self) -> str:
        return self.name

    def get_info(self) -> str:
        from src.i18n import t
        return f"[{self.id}] " + t("{name} ({realm})", name=self.name, realm=str(self.realm))

    def get_detailed_info(self) -> str:
        from src.i18n import t
        return f"[{self.id}] " + t("{name}: {desc} ({realm})", name=self.name, desc=self.desc, realm=str(self.realm))

    def get_structured_info(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.name,
            "desc": self.desc,
            "grade": str(self.realm),
            "effect_desc": "" # Materials have no effects field for now
        }

def _load_materials() -> tuple[dict[int, Material], dict[str, Material]]:
    """Load material data from the config table."""
    materials_by_id: dict[int, Material] = {}
    materials_by_name: dict[str, Material] = {}
    
    if "material" in game_configs:
        material_df = game_configs["material"]
        for row in material_df:
            material = Material(
                id=get_int(row, "id"),
                name=get_str(row, "name"),
                desc=get_str(row, "desc"),
                realm=Realm.from_id(get_int(row, "stage_id"))
            )
            materials_by_id[material.id] = material
            materials_by_name[material.name] = material
    
    return materials_by_id, materials_by_name

# Load material data from the config table
materials_by_id, materials_by_name = _load_materials()

def reload():
    """Reload data."""
    new_id, new_name = _load_materials()
    materials_by_id.clear()
    materials_by_id.update(new_id)
    materials_by_name.clear()
    materials_by_name.update(new_name)
