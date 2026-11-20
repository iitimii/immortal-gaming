from typing import TYPE_CHECKING, Optional

from src.classes.environment.tile import Tile, TileType
from src.classes.environment.sect_region import SectRegion

if TYPE_CHECKING:
    from src.classes.environment.region import Region


class Map():
    """
    Records position -> tile via a dict.
    """
    def __init__(
        self,
        width: int,
        height: int,
        map_id: str = "classic",
        map_name: str = "",
        preset_version: int = 1,
    ):
        self.tiles = {}
        self.width = width
        self.height = height
        self.map_id = map_id
        self.map_name = map_name
        self.preset_version = preset_version
        self.wilderness_tile = "plain"
        self.landmarks: dict[int, dict[str, object]] = {}
        self.region_overrides: dict[int, dict[str, object]] = {}
        self.region_formations: dict[int, dict[str, object]] = {}
        # Coordinate sets of each region's "final ownership" (written by the allocation process)
        # key: region.id, value: list[(x, y)]
        self.region_cors: dict[int, list[tuple[int, int]]] = {}
        
        # Region dict, populated by the external loader (load_map.py)
        # Only regions[id] is maintained as the single source of truth; lookup by name iterates
        self.regions = {}
        self.sect_regions = {}
        
        # Category indexes are filled by the loader as needed; regions remains the only semantic source of truth.
        self.normal_regions = {}
        self.cultivate_regions = {}
        self.city_regions = {}

    def update_sect_regions(self) -> None:
        """Dynamically refresh the sect headquarters region dict from the current self.regions."""
        self.sect_regions = {rid: r for rid, r in self.regions.items() if isinstance(r, SectRegion)}

    def is_in_bounds(self, x: int, y: int) -> bool:
        """
        Determine whether a coordinate is within the map bounds.
        """
        return 0 <= x < self.width and 0 <= y < self.height

    def create_tile(self, x: int, y: int, tile_type: TileType):
        self.tiles[(x, y)] = Tile(tile_type, x, y, region=None)

    def get_tile(self, x: int, y: int) -> Tile:
        return self.tiles[(x, y)]

    def get_center_locs(self, locs: list[tuple[int, int]]) -> tuple[int, int]:
        """
        Get the center position of locs.
        If the geometric center is in the position list, return it;
        otherwise return the actual position nearest to the geometric center.
        """
        if not locs:
            return (0, 0)
        
        # Compute the average of the x and y coordinates separately
        avg_x = sum(loc[0] for loc in locs) // len(locs)
        avg_y = sum(loc[1] for loc in locs) // len(locs)
        center = (avg_x, avg_y)

        # If the geometric center is in the position list, return it directly
        if center in locs:
            return center
        
        # Otherwise find the actual position nearest to the geometric center
        def distance_squared(loc: tuple[int, int]) -> int:
            """Compute the squared distance to the center (avoids a square root)."""
            return (loc[0] - avg_x) ** 2 + (loc[1] - avg_y) ** 2
        
        return min(locs, key=distance_squared)

    def get_region(self, x: int, y: int) -> Optional['Region']:
        """
        Get a region.
        """
        return self.tiles[(x, y)].region

    def get_info(self, detailed: bool = False, avatar: object = None) -> dict:
        """
        Return map info (dict).
        avatar: if given, used to:
               1. filter to only regions in avatar.known_regions
               2. compute and append the distance from the avatar's current position to each region in the description
        """
        if TYPE_CHECKING:
             from src.classes.core.avatar import Avatar

        from src.classes.environment.region import NormalRegion, CultivateRegion, CityRegion
        
        known_region_ids = avatar.known_regions if avatar else None
        current_loc = (avatar.pos_x, avatar.pos_y) if avatar else None
        
        def filter_regions(cls):
            return {
                rid: r for rid, r in self.regions.items() 
                if isinstance(r, cls) and (known_region_ids is None or rid in known_region_ids)
            }

        from src.i18n import t

        def build_regions_info(regions_dict) -> list[str]:
            infos = []
            step_len = avatar.move_step_length if avatar else 1
            for r in regions_dict.values():
                base_info = r.get_detailed_info(current_loc, step_len) if detailed else r.get_info(current_loc, step_len)
                infos.append(base_info)
            return infos

        return {
            t("Cultivate Region (can respire to increase cultivation)"): build_regions_info(filter_regions(CultivateRegion)),
            t("Normal Region (can hunt, gather, mine)"): build_regions_info(filter_regions(NormalRegion)),
            t("City Region (can trade)"): build_regions_info(filter_regions(CityRegion)),
            t("Sect Headquarters (sect disciples heal faster here)"): build_regions_info(filter_regions(SectRegion)),
        }
