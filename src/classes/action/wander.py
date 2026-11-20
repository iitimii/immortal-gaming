from __future__ import annotations

import random
from typing import TYPE_CHECKING

from src.i18n import t
from src.classes.action import TimedAction, Move
from src.classes.action.move_to_direction import Direction
from src.classes.event import Event
from src.classes.environment.region import NormalRegion, Region
from src.classes.environment.sect_region import SectRegion
from src.systems.cultivation import REALM_RANK

if TYPE_CHECKING:
    from src.classes.material import Material


class Wander(TimedAction):
    """
    Wander: roam the land for a short while to broaden one's horizons.

    Each month the avatar drifts toward the nearest region it does not know yet
    (within a modest search radius); when there is none, it drifts in a random
    in-bounds direction. Regions it walks into become known. On finish there is
    a small, luck-scaled chance of a serendipitous find.
    """

    # i18n IDs
    ACTION_NAME_ID = "wander_action_name"
    DESC_ID = "wander_description"
    REQUIREMENTS_ID = "wander_requirements"

    # Constants that need no translation
    EMOJI = "🍃"
    PARAMS = {}

    duration_months = 2

    # Manhattan radius within which unknown regions are sought out
    SEARCH_RADIUS = 15

    # Serendipitous find probability: BASE + luck * LUCK_FACTOR, clamped to [MIN, MAX]
    BASE_FIND_PROB = 0.15
    LUCK_FIND_FACTOR = 0.005
    MIN_FIND_PROB = 0.02
    MAX_FIND_PROB = 0.40
    # Share of finds that are a local material (when the region offers one)
    MATERIAL_FIND_SHARE = 0.5
    # Spirit stone finds by realm rank (a small fraction of a fortune event)
    SPIRIT_STONE_RANGES: tuple[tuple[int, int], ...] = ((5, 10), (25, 40), (50, 75), (100, 150))

    _DIRECTIONS = ("north", "south", "east", "west")

    def __init__(self, avatar, world):
        super().__init__(avatar, world)
        self.target_region_id: int | None = None
        self.target_loc: tuple[int, int] | None = None
        self.fallback_direction: str | None = None
        self.initial_known_regions: set[int] | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def can_possibly_start(self) -> bool:
        return not bool(getattr(self.avatar, "is_dead", False))

    def can_start(self) -> tuple[bool, str]:
        if getattr(self.avatar, "is_dead", False):
            return False, t("wander_cannot_start_dead")
        return True, ""

    def start(self) -> Event:
        self.initial_known_regions = set(self.avatar.known_regions)
        content = t(
            "wander_start_event",
            avatar=self.avatar.name,
            location=self.avatar.tile.location_name,
        )
        return Event(self.world.month_stamp, content, related_avatars=[self.avatar.id])

    def _execute(self) -> None:
        if self.initial_known_regions is None:
            self.initial_known_regions = set(self.avatar.known_regions)

        target_region = self._pick_target_region()
        if target_region is not None and self.target_loc is not None:
            dest = self.target_loc
        else:
            dest = self._fallback_destination()

        dx = dest[0] - self.avatar.pos_x
        dy = dest[1] - self.avatar.pos_y
        if dx or dy:
            Move(self.avatar, self.world).execute(dx, dy)

        region = self.avatar.tile.region if self.avatar.tile is not None else None
        if region is not None:
            self.avatar.known_regions.add(region.id)

    async def finish(self) -> list[Event]:
        events: list[Event] = []
        discovered = self._discovered_region_names()
        if discovered:
            content = t(
                "wander_finish_discovered_event",
                avatar=self.avatar.name,
                regions=", ".join(discovered),
            )
        else:
            content = t(
                "wander_finish_event",
                avatar=self.avatar.name,
                location=self.avatar.tile.location_name,
            )
        events.append(Event(self.world.month_stamp, content, related_avatars=[self.avatar.id]))

        find_content = self._try_serendipitous_find()
        if find_content:
            events.append(Event(self.world.month_stamp, find_content, related_avatars=[self.avatar.id]))
        return events

    # ------------------------------------------------------------------
    # Movement helpers
    # ------------------------------------------------------------------

    def _is_wander_target(self, region: Region) -> bool:
        if region.id in self.avatar.known_regions or not region.cors:
            return False
        # Mirror MoveToRegion: another sect's headquarters is not a destination
        if isinstance(region, SectRegion):
            sect = getattr(self.avatar, "sect", None)
            if sect is None or sect.id != region.sect_id:
                return False
        return True

    def _nearest_cor(self, region: Region) -> tuple[tuple[int, int], int]:
        x, y = self.avatar.pos_x, self.avatar.pos_y
        best = min(region.cors, key=lambda c: abs(c[0] - x) + abs(c[1] - y))
        return (int(best[0]), int(best[1])), abs(best[0] - x) + abs(best[1] - y)

    def _pick_target_region(self) -> Region | None:
        """Keep the current target while it is still unknown; otherwise pick the nearest unknown region."""
        regions = self.world.map.regions
        if self.target_region_id is not None:
            current = regions.get(self.target_region_id)
            if current is not None and self._is_wander_target(current):
                if self.target_loc is None:
                    self.target_loc = self._nearest_cor(current)[0]
                return current

        self.target_region_id = None
        self.target_loc = None
        best_dist: int | None = None
        best: list[tuple[Region, tuple[int, int]]] = []
        for region in regions.values():
            if not self._is_wander_target(region):
                continue
            loc, dist = self._nearest_cor(region)
            if dist > self.SEARCH_RADIUS:
                continue
            if best_dist is None or dist < best_dist:
                best_dist = dist
                best = [(region, loc)]
            elif dist == best_dist:
                best.append((region, loc))
        if not best:
            return None
        region, loc = random.choice(best)
        self.target_region_id = region.id
        self.target_loc = loc
        return region

    def _reach(self) -> int:
        step = int(getattr(self.avatar, "move_step_length", 1) or 1)
        step += int(self.avatar.effects.get("extra_move_step", 0) or 0)
        return max(1, step)

    def _clamped_dest(self, direction: str) -> tuple[int, int]:
        vx, vy = Direction.get_vector(direction)
        reach = self._reach()
        game_map = self.world.map
        nx = min(max(self.avatar.pos_x + vx * reach, 0), game_map.width - 1)
        ny = min(max(self.avatar.pos_y + vy * reach, 0), game_map.height - 1)
        return nx, ny

    def _fallback_destination(self) -> tuple[int, int]:
        """A random in-bounds direction, kept across months until it hits the map edge."""
        here = (self.avatar.pos_x, self.avatar.pos_y)
        if self.fallback_direction is not None and self._clamped_dest(self.fallback_direction) != here:
            return self._clamped_dest(self.fallback_direction)
        open_dirs = [d for d in self._DIRECTIONS if self._clamped_dest(d) != here]
        if not open_dirs:
            return here
        self.fallback_direction = random.choice(open_dirs)
        return self._clamped_dest(self.fallback_direction)

    def _discovered_region_names(self) -> list[str]:
        initial = self.initial_known_regions or set()
        names: list[str] = []
        for region_id in sorted(self.avatar.known_regions - initial):
            region = self.world.map.regions.get(region_id)
            if region is not None:
                names.append(region.name)
        return names

    # ------------------------------------------------------------------
    # Serendipitous find
    # ------------------------------------------------------------------

    def get_find_probability(self) -> float:
        luck = float(getattr(self.avatar, "luck", 0.0) or 0.0)
        prob = self.BASE_FIND_PROB + luck * self.LUCK_FIND_FACTOR
        return max(self.MIN_FIND_PROB, min(self.MAX_FIND_PROB, prob))

    def _local_materials(self) -> list[Material]:
        region = self.avatar.tile.region if self.avatar.tile is not None else None
        if not isinstance(region, NormalRegion):
            return []
        realm = self.avatar.cultivation_progress.realm
        materials: list[Material] = []
        for source in (*region.plants, *region.lodes, *region.animals):
            if realm >= source.realm:
                materials.extend(getattr(source, "materials", []) or [])
        return materials

    def _spirit_stone_amount(self) -> int:
        rank = REALM_RANK.get(self.avatar.cultivation_progress.realm, 0)
        low, high = self.SPIRIT_STONE_RANGES[min(max(rank, 0), len(self.SPIRIT_STONE_RANGES) - 1)]
        return random.randint(low, high)

    def _try_serendipitous_find(self) -> str:
        if random.random() >= self.get_find_probability():
            return ""
        materials = self._local_materials()
        if materials and random.random() < self.MATERIAL_FIND_SHARE:
            material = random.choice(materials)
            self.avatar.add_material(material, 1)
            return t("wander_find_material_event", avatar=self.avatar.name, material=material.name)
        amount = self._spirit_stone_amount()
        self.avatar.magic_stone = self.avatar.magic_stone + amount
        return t("wander_find_spirit_stones_event", avatar=self.avatar.name, amount=amount)

    # ------------------------------------------------------------------
    # Save / load (runtime state of an in-progress wander)
    # ------------------------------------------------------------------

    def get_save_data(self) -> dict:
        data = super().get_save_data()
        data.update(
            {
                "target_region_id": self.target_region_id,
                "target_loc": list(self.target_loc) if self.target_loc is not None else None,
                "fallback_direction": self.fallback_direction,
                "initial_known_regions": (
                    sorted(self.initial_known_regions) if self.initial_known_regions is not None else None
                ),
            }
        )
        return data

    def load_save_data(self, data: dict) -> None:
        super().load_save_data(data)
        self.target_region_id = data.get("target_region_id")
        loc = data.get("target_loc")
        self.target_loc = (int(loc[0]), int(loc[1])) if loc else None
        self.fallback_direction = data.get("fallback_direction")
        initial = data.get("initial_known_regions")
        self.initial_known_regions = set(int(r) for r in initial) if initial is not None else None
