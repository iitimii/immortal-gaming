from dataclasses import dataclass

from src.classes.environment.region import Region
from src.classes.essence import Essence, EssenceType
from src.i18n import t


@dataclass(eq=False)
class SectRegion(Region):
    """
    Sect headquarters region:
    - Used as a fallback cultivation region;
    - Only members respiring here enjoy an equivalent "all five elements at 5" qi environment.
    """
    sect_name: str = ""
    sect_id: int = -1
    image_path: str | None = None

    @property
    def essence(self) -> Essence:
        """
        Equivalent qi settings of sect headquarters:
        - Five-element qi (Metal, Wood, Water, Fire, Earth) density is 5 for each;
        - Only treated as a cultivation environment in action logic (e.g. Respire).
        """
        density = {essence_type: 5 for essence_type in EssenceType}
        return Essence(density)

    def get_region_type(self) -> str:
        return "sect"

    def _get_desc(self) -> str:
        return t("sect_headquarters_desc_format", sect_name=self.sect_name)

    def get_structured_info(self) -> dict:
        info = super().get_structured_info()
        info["type_name"] = t("Sect Headquarters")
        info["sect_name"] = self.sect_name
        info["sect_id"] = self.sect_id
        # The frontend can reuse the cultivation region display, showing the "fallback" qi environment:
        # type joins the five translated qi names with commas, e.g. "Metal,Wood,Water,Fire,Earth"
        type_label = ",".join(str(essence_type) for essence_type in EssenceType)
        info["essence"] = {
            "type": type_label,
            "density": 5,
        }
        return info
